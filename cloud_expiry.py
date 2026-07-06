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

print("✅ क्रेडेंशियल्स मिळाले! फायर्स क्लायंट सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 डेटा फेचिंग आणि HTML रो जनरेशन फंक्शन
# =====================================================================
def get_index_weekly_html(symbol):
    # मागील ९० दिवसांचा ऐतिहासिक डेटा मिळवणे
    start_date = datetime.date.today() - datetime.timedelta(days=90)
    payload = {
        "symbol": symbol, 
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
                print(f"⚠️ {symbol}: डेटा रिकामा मिळाला.")
                return None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल % (Change %) कॅल्क्युलेट करणे
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # डेटा रिव्हर्स करणे (नवीन तारीख वर दाखवण्यासाठी)
            df = df.iloc[::-1]
            
            html_rows = ""
            
            # १. पहिली ओळ LIVE डेटा (Latest Row)
            live_row = df.iloc[0]
            change_color = "green" if live_row['Change_Pct'] >= 0 else "red"
            sign = "+" if live_row['Change_Pct'] >= 0 else ""
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_row['Close']:,} (Today)</td><td style='color: {change_color};'>{sign}{live_row['Change_Pct']:.2f}%</td></tr>\n"
            
            # २. इतर ऐतिहासिक मंगळवार फिल्टर करून जोडणे
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                day_name = dt.strftime('%a')
                
                # फक्त मंगळवारचा डेटा (Tuesday Expiry)
                if day_name == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            return html_rows
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return None
    except Exception as e:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e}")
        return None

# =====================================================================
# 💾 मुख्य एक्झिक्युशन आणि अचूक प्लेसहोल्डर रिप्लेसमेंट सिस्टीम
# =====================================================================
nifty_table_rows = get_index_weekly_html("NSE:NIFTY50-INDEX")

if nifty_table_rows:
    dashboard_filename = "index.html"
    
    try:
        if os.path.exists(dashboard_filename):
            # १. मूळ index.html फाईल पूर्ण वाचणे
            with open(dashboard_filename, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # २. जर {{NIFTY_DATA}} हा प्लेसहोल्डर मिळाला तर तिथे डेटा रिप्लेस करणे
            if "{{NIFTY_DATA}}" in html_content:
                updated_html = html_content.replace("{{NIFTY_DATA}}", nifty_table_rows)
                
                with open(dashboard_filename, "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print("💾 यशस्वी: लाइव्ह डेटा {{NIFTY_DATA}} च्या जागी अचूक अपडेट केला गेला आहे!")
            else:
                print("⚠️ एरर: index.html मध्ये {{NIFTY_DATA}} हा शब्द सापडला नाही. कृपया index.html मध्ये हा प्लेसहोल्डर टॅग जोडा.")
        else:
            print(f"❌ चूक: {dashboard_filename} फाईल सापडली नाही.")
                
    except Exception as e:
        print(f"❌ फाईल सेव्ह करताना त्रुटी: {e}")
else:
    print("🚨 फियर्स कडून डेटा मिळाला नाही, त्यामुळे डॅशबोर्ड अपडेट केला नाही.")
