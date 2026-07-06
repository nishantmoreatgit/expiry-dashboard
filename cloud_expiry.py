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
# 📊 डेटा फेचिंग आणि HTML टेबल जनरेशन फंक्शन
# =====================================================================
def get_index_weekly_html(symbol, title):
    # मागील ६० दिवसांचा डेटा मिळवणे
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
                return None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल % (Change %) कॅल्क्युलेट करणे
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # डेटा रिव्हर्स करणे (नवीन तारीख वर दाखवण्यासाठी)
            df = df.iloc[::-1]
            
            # डॅशबोर्डचे टेबल रोजचे रो जनरेट करणे
            html_rows = ""
            
            # १. पहिली ओळ LIVE डेटा (Latest Row)
            live_row = df.iloc[0]
            change_color = "green" if live_row['Change_Pct'] >= 0 else "red"
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'>"
            html_rows += f"<td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_row['Close']:,} (Today)</td><td style='color: {change_color};'>+{live_row['Change_Pct']:.2f}%</td></tr>\n"
            
            # २. इतर ऐतिहासिक मंगळवार फिल्टर करून जोडणे
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                day_name = dt.strftime('%a')
                
                # फक्त मंगळवारचा डेटा डॅशबोर्डमध्ये जोडण्यासाठी फिल्टर (Tuesday Expiry)
                if day_name == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            return html_rows
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return None
    except Exception as e:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e}")
        return None

# =====================================================================
# 💾 मुख्य एक्झिक्युशन आणि फाईल इंजेक्शन सिस्टीम
# =====================================================================
html_table_rows = get_index_weekly_html("NSE:NIFTY50-INDEX", "Nifty 50 Weekly")

if html_table_rows:
    dashboard_filename = "index.html"
    
    try:
        # १. मूळ index.html फाईल वाचणे
        with open(dashboard_filename, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # २. जुना टेबल डेटा शोधून नवीन डेटाने बदलणे
        # तुमच्या index.html मध्ये <tbody> आणि </tbody> चे टॅग्ज असणे आवश्यक आहे
        if "<tbody>" in html_content and "</tbody>" in html_content:
            start_idx = html_content.find("<tbody>") + len("<tbody>")
            end_idx = html_content.find("</tbody>")
            
            # नवीन डेटा टेबलच्या मध्ये इन्जेक्ट करणे
            updated_html = html_content[:start_idx] + "\n" + html_table_rows + html_content[end_idx:]
            
            # ३. बदललेली फाईल पुन्हा सेव्ह करणे
            with open(dashboard_filename, "w", encoding="utf-8") as f:
                f.write(updated_html)
            print(f"💾 यशस्वी: नवीन लाइव्ह डेटा {dashboard_filename} मध्ये इन्जेक्ट केला आहे!")
        else:
            print("⚠️ एरर: index.html मध्ये <tbody> टॅग सापडला नाही. संपूर्ण फाईल अपडेट केली जात आहे.")
            # टॅग नसेल तर बॅकअप म्हणून संपूर्ण फाईल ओव्हरराईट करणे
            with open(dashboard_filename, "w", encoding="utf-8") as f:
                f.write(html_table_rows)
                
    except Exception as e:
        print(f"❌ फाईल अपडेट करताना त्रुटी: {e}")
else:
    print("🚨 डेटा मिळाला नाही, त्यामुळे डॅशबोर्ड अपडेट केला नाही.")
