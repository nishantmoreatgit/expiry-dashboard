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

print("✅ क्रेडेंशियल्स मिळाले! फायर्स रिअल-टाइम इंजिन सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 रिअल-टाइम डेटा फेचिंग आणि HTML रो जनरेशन सिस्टीम
# =====================================================================
def generate_live_dashboard():
    symbol = "NSE:NIFTY50-INDEX"
    
    # 🎯 १. रिअल-टाइम लाईव्ह टिक प्राईस मिळवणे (Quotes API)
    live_close = 0.0
    live_change = 0.0
    try:
        quote_payload = {"symbols": symbol}
        quote_res = fyers.quotes(data=quote_payload)
        if quote_res and quote_res.get('code') == 200:
            data_out = quote_res.get('d', [])[0].get('v', {})
            live_close = data_out.get('lp', 0.0)      # Live Last Price (LTP)
            live_change = data_out.get('chp', 0.0)    # Live Change Percentage
            print(f"🎯 Quotes API वरून मिळालेला थेट लाईव्ह भाव: {live_close}")
    except Exception as e_quote:
        print(f"⚠️ Quotes API फेल झाले, जुनी पद्धत वापरत आहे: {e_quote}")

    # २. ऐतिहासिक मंगळवार गोळा करणे (History API)
    start_date = datetime.date.today() - datetime.timedelta(days=90)
    history_payload = {
        "symbol": symbol, 
        "resolution": "D", 
        "date_format": "1", 
        "range_from": start_date.strftime("%Y-%m-%d"), 
        "range_to": datetime.date.today().strftime("%Y-%m-%d"), 
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
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            df = df.iloc[::-1]
            
            # जर Quotes API कडून लाईव्ह डेटा मिळाला नसेल, तर बॅकअप म्हणून हिस्टरीचा लेटेस्ट डेटा वापरणे
            if live_close == 0.0:
                live_close = df['Close'].iloc[0]
                live_change = df['Change_Pct'].iloc[0]
            
            html_rows = ""
            current_date = datetime.date.today().strftime("%Y-%m-%d")
            
            # 🎯 डॅशबोर्डवर १००% अचूक चालू रिअल-टाइम टिक ओळ जोडणे
            change_color = "green" if live_change >= 0 else "red"
            sign = "+" if live_change >= 0 else ""
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_close:,.2f} ({current_date})</td><td style='color: {change_color};'>{sign}{live_change:.2f}%</td></tr>\n"
            
            # ऐतिहासिक मंगळवारचे रेकॉर्ड्स जोडणे
            for _, row in df.iterrows():
                dt = pd.to_datetime(row['Date'])
                # आजची तारीख ऐतिहासिक टेबलमध्ये डबल दिसू नये म्हणून वगळणे
                if row['Date'] == datetime.date.today():
                    continue
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,.2f}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # संपूर्ण स्वतंत्र डॅशबोर्ड टेम्पलेट
            full_master_dashboard = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30"> <!-- दर ३0 सेकंदांनी पेज ऑटो-लोडेबल होईल -->
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
fresh_dashboard_html = generate_live_dashboard()

if fresh_dashboard_html:
    target_file = "index.html"
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(fresh_dashboard_html)
        print(f"💾 यशस्वी: {target_file} फाईल नवीन रिअल-टाइम डेटासह अद्ययावत केली आहे!")
    except Exception as e:
        print(f"❌ फाईल सेव्ह करताना त्रुटी आली: {e}")
