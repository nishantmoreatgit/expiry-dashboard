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

print("✅ क्रेडेंशियल्स मिळाले! १-मिनिट रिअल-टाइम डेटा इंजिन सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 डेटा फेचिंग आणि नवीन कोरी HTML डॅशबोर्ड जनरेशन सिस्टीम
# =====================================================================
def force_rebuild_dashboard():
    symbol = "NSE:NIFTY50-INDEX"
    current_date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 🎯 १. खरोखरचा चालू लाईव्ह भाव मिळवणे (1-Minute Resolution History)
    live_close = 0.0
    live_change = 0.0
    
    try:
        # आजच्या दिवसाची चालू १-मिनिटाची कॅंडल मागवणे
        live_payload = {
            "symbol": symbol,
            "resolution": "1",
            "date_format": "1",
            "range_from": current_date_str,
            "range_to": current_date_str,
            "cont_flag": "1"
        }
        live_res = fyers.history(data=live_payload)
        if live_res and live_res.get('code') == 200:
            live_candles = live_res.get('candles', [])
            if live_candles:
                # सर्वात शेवटच्या १-मिनिटाच्या कॅंडलचा क्लोजिंग भाव म्हणजेच चालू टिक भाव (LTP)
                live_close = live_candles[-1][4]
                print(f"🎯 १-मिनिट कॅंडलवरून मिळालेला थेट बाजारभाव: {live_close}")
    except Exception as e_live:
        print(f"⚠️ १-मिनिट डेटा खेचताना एरर आली: {e_live}")

    # २. ऐतिहासिक मंगळवार डेटा मिळवणे (Daily Resolution History)
    start_date = datetime.date.today() - datetime.timedelta(days=90)
    history_payload = {
        "symbol": symbol, 
        "resolution": "D", 
        "date_format": "1", 
        "range_from": start_date.strftime("%Y-%m-%d"), 
        "range_to": current_date_str, 
        "cont_flag": "1"
    }
    
    try:
        res = fyers.history(data=history_payload)
        if res and res.get('code') == 200:
            candles = res.get('candles', [])
            if not candles: 
                print("⚠️ हिस्टरी डेटा रिकामा मिळाला.")
                return None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल टक्केवारी काढणे (Daily Change %)
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # जर १-मिनिट डेटा अपयशी ठरला, तरच डेली क्लोज वापरणे
            if live_close == 0.0:
                live_close = df['Close'].iloc[-1]
                live_change = df['Change_Pct'].iloc[-1]
            else:
                # जर १-मिनिट लाइव्ह भाव मिळाला, तर कालच्या बंद भावावरून आजचा खरा लाइव्ह बदल काढणे
                prev_day_close = df['Close'].iloc[-2] if len(df) > 1 else df['Close'].iloc[-1]
                live_change = ((live_close - prev_day_close) / prev_day_close) * 100
            
            # डेटा रिव्हर्स करणे (जेणेकरून ऐतिहासिक तारखा खाली क्रमाने दिसतील)
            df = df.iloc[::-1]
            
            html_rows = ""
            change_color = "green" if live_change >= 0 else "red"
            sign = "+" if live_change >= 0 else ""
            
            # 🎯 डॅशबोर्डवर १००% अचूक चालू रिअल-टाइम ओळ जोडणे
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_close:,.2f} ({current_date_str})</td><td style='color: {change_color};'>{sign}{live_change:.2f}%</td></tr>\n"
            
            # ऐतिहासिक मंगळवारचे रेकॉर्ड्स फिल्टर करून जोडणे
            for _, row in df.iterrows():
                if row['Date'] == datetime.date.today():
                    continue
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,.2f}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # संपूर्ण स्वतंत्र डॅशबोर्ड टेम्पलेट
            full_master_dashboard = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
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
    <h2>📊 CLOUD LIVE INTRA-DAY MASTER DASHBOARD</h2>
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
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(fresh_dashboard_html)
        print(f"💾 यशस्वी: {target_file} फाईल नवीन १-मिनिट लाइव्ह डेटासह अद्ययावत केली आहे!")
    except Exception as e:
        print(f"❌ फाईल सेव्ह करताना त्रुटी आली: {e}")
