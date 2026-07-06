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

print("✅ क्रेडेंشियल्स मिळाले! फायर्स क्लायंट सुरू करत आहे...")
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
# 📊 डेटा फेचिंग आणि HTML रो जनरेशन फंक्शन
# =====================================================================
def get_index_weekly_html(symbol, title):
    # मागील ९० दिवसांचा ऐतिहासिक डेटा मिळवणे (Reports अचूक दिसण्यासाठी)
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
                print(f"⚠️ {title}: डेटा रिकामा मिळाला.")
                return None, None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # बदल % (Change %) कॅल्क्युलेट करणे
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # डेटा रिव्हर्स करणे (नवीन तारीख वर दाखवण्यासाठी)
            df = df.iloc[::-1]
            
            # डॅशबोर्डचे टेबल रो जनरेशन
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
                
                # फक्त मंगळवारचा डेटा डॅशबोर्डमध्ये जोडण्यासाठी फिल्टर (Tuesday Expiry)
                if day_name == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # संपूर्ण स्वतंत्र HTML डॅशबोर्ड कोड (जर पूर्ण फाईल ओव्हरराईट करायची असेल तर)
            full_html = f"""
            <!DOCTYPE html>
            <html lang="mr">
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="refresh" content="60">
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f9f9f9; }}
                    table {{ border-collapse: collapse; width: 100%; max-width: 800px; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                    th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
                    th {{ background-color: #f2f2f2; }}
                    h2 {{ color: #333; }}
                </style>
            </head>
            <body>
                <h2>📊 {title}</h2>
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
            </html>
            """
            return html_rows, full_html
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return None, None
    except Exception as e:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e}")
        return None, None

# =====================================================================
# 💾 मुख्य एक्झिक्युशन आणि स्मार्ट फाईल सेव्हिंग सिस्टीम
# =====================================================================
html_table_rows, complete_html_page = get_index_weekly_html("NSE:NIFTY50-INDEX", "CLOUD LIVE INTRA-DAY MASTER DASHBOARD")

if html_table_rows and complete_html_page:
    dashboard_filename = "index.html"
    
    try:
        # मूळ फाईल वाचण्याचा प्रयत्न करणे
        if os.path.exists(dashboard_filename):
            with open(dashboard_filename, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # जर <tbody> टॅग सापडला तर फक्त डेटा इन्जेक्ट करा (तुमचे डिझाईन सुरक्षित राहील)
            if "<tbody>" in html_content and "</tbody>" in html_content:
                start_idx = html_content.find("<tbody>") + len("<tbody>")
                end_idx = html_content.find("</tbody>")
                updated_html = html_content[:start_idx] + "\n" + html_table_rows + html_content[end_idx:]
                
                with open(dashboard_filename, "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print(f"💾 यशस्वी: नवीन लाइव्ह डेटा {dashboard_filename} च्या <tbody> मध्ये इन्जेक्ट केला!")
            else:
                # टॅग नसेल तर संपूर्ण नवीन सुंदर HTML पेज तयार करणे
                with open(dashboard_filename, "w", encoding="utf-8") as f:
                    f.write(complete_html_page)
                print(f"💾 यशस्वी: <tbody> न सापडल्यामुळे संपूर्ण {dashboard_filename} फाईल नवीन डेटासह ओव्हरराईट केली!")
        else:
            # फाईल अस्तित्वात नसेल तर नवीन तयार करणे
            with open(dashboard_filename, "w", encoding="utf-8") as f:
                f.write(complete_html_page)
            print(f"💾 यशस्वी: {dashboard_filename} फाईल नवीन तयार करून डेटा लिहिला गेला आहे!")
                
    except Exception as e:
        print(f"❌ फाईल सेव्ह करताना त्रुटी: {e}")
else:
    print("🚨 डेटा मिळाला नाही, त्यामुळे डॅशबोर्ड अपडेट केला नाही.")
