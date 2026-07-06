import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब सिक्रेट्समधून थेट चालू लाइव्ह टोकन वाचणे
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
access_token = os.environ.get('FY_LIVE_TOKEN')   

if not client_id or not access_token:
    print("❌ एरर: गिटहब सिक्रेट्समधून App ID किंवा Access Token मिळाला नाही!")
    sys.exit(1)

print("✅ क्रेडेंशियल्स मिळाले! फियर्स इंजिन सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 डेटा फेचिंग आणि नवीन कोरी HTML डॅशबोर्ड जनरेशन सिस्टीम
# =====================================================================
def force_rebuild_dashboard():
    # मागील ९० दिवसांचा संपूर्ण डेटा सिंक करणे
    start_date = datetime.date.today() - datetime.timedelta(days=90)
    payload = {
        "symbol": "NSE:NIFTY50-INDEX", 
        "resolution": "D", 
        "date_format": "1", 
        "range_from": start_date.strftime("%Y-%m-%d"), 
        "range_to": datetime.date.today().strftime("%Y-%m-%d"), 
        "cont_flag": "1"
    }
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            candles = res.get('candles', [])
            if not candles: 
                print("⚠️ फियर्स कडून डेटा ब्लँक मिळाला.")
                return None
            
            # डेटा फ्रेम सिस्टीम
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल टक्केवारी काढणे
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # डेटा रिव्हर्स करणे (जेणेकरून आजची तारीख वर दिसेल)
            df = df.iloc[::-1]
            
            html_rows = ""
            
            # 🎯 १. लाइव्ह ओळ काढणे (पायथन इंडेक्सिंग त्रुटी दुरुस्त केली)
            live_close = df['Close'].iloc[0]
            live_change = df['Change_Pct'].iloc[0]
            
            # जर आज सुट्टी असेल किंवा डेटा अपडेट नसेल, तरीही क्रॅश रोखणे
            if pd.isna(live_change):
                live_change = 0.0
                
            change_color = "green" if live_change >= 0 else "red"
            sign = "+" if live_change >= 0 else ""
            
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_close:,.2f} (Today)</td><td style='color: {change_color};'>{sign}{live_change:.2f}%</td></tr>\n"
            
            # 🎯 २. ऐतिहासिक मंगळवार फिल्टर (Tuesday Expiry डाटा मॅपिंग)
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,.2f}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # 🎯 संपूर्ण नवीन स्वतंत्र टेम्पलेट जनरेशन (जुन्या फाईलवर अवलंबून राहणे बंद)
            full_master_dashboard = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="60">
    <title>CLOUD LIVE INTRA-DAY MASTER DASHBOARD</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f9f9f9; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 800px; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
        th {{ background-color: #f2f2f2; }}
        h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h2>=== 📊 CLOUD LIVE INTRA-DAY MASTER DASHBOARD ===</h2>
    <p>Nifty 50 Spot Weekly Report (Tuesday Expiry)</p>
    <table>
        <thead>
            <tr><th>तारीख ▲▼</th><th>क्लोज प्राईस ▲▼</th><th>बदल % ▲▼</th></tr>
        </thead>
        <tbody>
            {html_rows}
        </tbody>
    </table>
</body>
</html>"""
            return full_master_dashboard
        else:
            print(f"❌ फियर्स API कडून एरर आली: {res}")
            return None
    except Exception as e:
        print(f"❌ डेटा कॅल्क्युलेशन क्रॅश झाले: {e}")
        return None

# =====================================================================
# 💾 थेट फाईल ओव्हरराईट करणे (Force Override Engine)
# =====================================================================
fresh_dashboard_html = force_rebuild_dashboard()

if fresh_dashboard_html:
    target_file = "index.html"
    try:
        # कोणतीही जुनी व्हॅल्यू न तपासता थेट फाईल नवीन डेटाने बदलणे
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(fresh_dashboard_html)
        print(f"💾 यशस्वी: {target_file} फाईल नवीन लाईव्ह डेटासह पूर्ण बदलली आहे!")
    except Exception as e:
        print(f"❌ फाईल सेव्ह करताना त्रुटी आली: {e}")
