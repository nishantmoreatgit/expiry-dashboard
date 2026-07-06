import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब सिक्रेट्समधून थेट तुमचा सेव्ह केलेला टोकन वाचणे
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
access_token = os.environ.get('FY_LIVE_TOKEN')   

if not client_id or not access_token:
    print("❌ एरर: गिटहब सिक्रेट्समधून App ID किंवा Access Token मिळाला नाही!")
    print(f"🔍 सद्यस्थिती -> App ID मिळाला का?: {'होय' if client_id else 'नाही'}, Token मिळाला का?: {'होय' if access_token else 'नाही'}")
    sys.exit(1)

print("✅ क्रेडेंशियल्स मिळाले! फायर्स क्लायंट सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📈 मॅथेमॅटिकल फंक्शन्स (Black-Scholes Options Metrics)
# =====================================================================
def cdf_normal(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_options(S, K, T, r, sigma):
    if T <= 0: return max(0.0, S - K), max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * cdf_normal(d1) - K * math.exp(-r * T) * cdf_normal(d2), K * math.exp(-r * T) * cdf_normal(-d2) - S * cdf_normal(-d1)

# =====================================================================
# 📊 डेटा फेचिंग आणि HTML जनरेशन फंक्शन
# =====================================================================
def get_index_weekly_html(symbol, title):
    # मागील ६० दिवसांचा डेटा मिळवणे जेणेकरून रिपोर्ट्समध्ये खंड पडणार नाही
    start_date = datetime.date.today() - datetime.timedelta(days=60)
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
                print(f"⚠️ {title}: डेटा रिकामा मिळाला.")
                return f"<div style='color:orange;'>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            # कॅंडल्स डेटा फ्रेम तयार करणे
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल % (Change %) कॅल्क्युलेट करणे
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            print(f"📊 {title} लाइव्ह डेटा यशस्वी! शेवटची क्लोजिंग किंमत: {df['Close'].iloc[-1]}")
            
            # डेटा रिव्हर्स करणे (नवीन तारीख वर दाखवण्यासाठी)
            df = df.iloc[::-1]
            
            # डॅशबोर्डसाठी सुंदर HTML टेबल तयार करणे
            html_content = f"<h3>📊 {title} Dashboard</h3>"
            html_content += "<table border='1' style='border-collapse: collapse; width: 100%; text-align: left; font-family: Arial;'>"
            html_content += "<tr style='background-color: #f2f2f2;'><th>तारीख ▲▼</th><th>क्लोज प्राईस ▲▼</th><th>बदल % ▲▼</th></tr>"
            
            # पहिली ओळ LIVE डेटा म्हणून हायलाइट करणे
            live_row = df.iloc[0]
            change_color = "green" if live_row['Change_Pct'] >= 0 else "red"
            html_content += f"<tr style='background-color: #ffe6e6; font-weight: bold;'>"
            html_content += f"<td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_row['Close']:,} (Today)</td><td style='color: {change_color};'>{live_row['Change_Pct']:.2f}%</td></tr>"
            
            # इतर ऐतिहासिक तारखा जोडणे (फक्त मंगळवार/विशिष्ट दिवसांचा फिल्टर हवा असल्यास तो इथे लावू शकता)
            for _, row in df.iloc[1:10].iterrows():
                day_name = pd.to_datetime(row['Date']).strftime('%a')
                row_color = "green" if row['Change_Pct'] >= 0 else "red"
                html_content += f"<tr><td>{row['Date']} ({day_name})</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{row['Change_Pct']:.2f}%</td></tr>"
                
            html_content += "</table>"
            return html_content
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return f"<div style='color:red;'>⚠️ एरर: {res.get('message', 'माहिती मिळू शकली नाही')}</div>"
    except Exception as e_hist:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e_hist}")
        return f"<div style='color:red;'>⚠️ एक्सेप्शन एरर: {str(e_hist)}</div>"

# =====================================================================
# 💾 मुख्य एक्झिक्युशन आणि फाईल सेव्हिंग सिस्टीम
# =====================================================================
# डेटा फेच करा
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "⚡ CLOUD LIVE INTRA-DAY MASTER DASHBOARD")

# डॅशबोर्ड फाईलचे नाव (तुमच्या फाईलचे नाव index.html नसेल तर ते बदला)
dashboard_filename = "index.html" 

try:
    with open(dashboard_filename, "w", encoding="utf-8") as f:
        f.write(html_table)
    print(f"💾 यशस्वी: नवीन डेटा {dashboard_filename} फाईलमध्ये लिहिला गेला आहे!")
except Exception as e_file:
    print(f"❌ फाईल सेव्ह करताना एरर आली: {e_file}")
