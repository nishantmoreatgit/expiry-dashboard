import datetime
import math
import pandas as pd
import os
import pyotp
import requests
from urllib.parse import urlparse, parse_qs
from fyers_apiv3 import fyersModel

# १. गिटहब लॉकरमधून (Secrets) पासवर्ड्स सुरक्षितपणे वाचणे
client_id = "RAE54K69M5-100" 
secret_key = os.environ.get('FY_SECRET_KEY')
fy_username = os.environ.get('FY_USER_ID')
fy_pin = os.environ.get('FY_PIN')
totp_key = os.environ.get('FY_TOTP_KEY')

def get_fyers_fully_automatic_token():
    print("● पायरी १: फुल्ल ऑटो-लॉगिन प्रक्रिया सुरू होत आहे...")
    try:
        # १. गुगल ऑथेंटिकेटरचा ६ आकडी लाईव्ह OTP जनरेट करणे
        totp = pyotp.TOTP(totp_key.replace(" ", ""))
        token_otp = totp.now()
        print(f"● पायरी २: लाईव्ह TOTP OTP ({token_otp}) यशस्वीरीत्या जनरेट झाला.")
        
        # FYERS v3 सेशन मॉडेल तयार करणे
        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri="https://fyers.in",
            response_type="code",
            grant_type="authorization_code"
        )
        
        # २. बॅकग्राउंडला फियर्स लॉगिन सर्व्हरशी संपर्क करणे (Requests Session)
        req_session = requests.Session()
        
        # फियर्स लॉगिन यूआरएल जनरेट करणे
        auth_url = session.generate_authcode()
        
        # पायरी ३: ओटीपी (TOTP) सबमिट करणे
        print("● पायरी ३: बॅकग्राउंडला TOTP आणि PIN सबमिट केला जात आहे...")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        # फियर्स बॅकएंड ऑथेंटिकेशन हिट
        login_payload = {
            "fy_username": fy_username, 
            "totp": token_otp, 
            "pin": fy_pin, 
            "appId": client_id.split("-")[0]
        }
        
        res = req_session.post("https://fyers.in", json=login_payload, headers=headers)
        
        if res.status_code == 200:
            auth_res = res.json()
            if auth_res.get('s') == 'ok':
                auth_code = auth_res.get('code')
                print("● पायरी ४: FYERS कडून ऑथेंटिकेशन कोड आपोआप मिळाला!")
                
                # ३. मिळालेला कोड वापरून फायनल Access Token जनरेट करणे
                session.set_token(auth_code)
                token_response = session.generate_token()
                
                final_token = token_response.get('access_token')
                if final_token:
                    print("🚀 यश: आजचे नवीन Access Token यशस्वीरीत्या जनरेट झाले!")
                    return final_token
            else:
                print(f"❌ FYERS एरर: {auth_res.get('message')}")
        else:
            print(f"❌ सर्व्हर एरर स्टेटस कोड: {res.status_code}")
            
        return None
    except Exception as e:
        print(f"❌ ऑटो-टोकन जनरेशन अपवाद (Exception): {e}")
        return None

# --- ऑटो-टोकन जनरेशन ट्रिगर करणे ---
access_token = get_fyers_fully_automatic_token()

# जर ऑटो-लॉगिन फेल झाले, तरच जुने टोकन बॅकअप म्हणून वापरले जाईल
if not access_token:
    print("⚠️ ऑटो-लॉगिन फेल, मॅन्युअल बॅकअप टोकन सेट करत आहे...")
    access_token = "EXPIRED_TOKEN_FOR_TESTING"

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

def cdf_normal(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_options(S, K, T, r, sigma):
    if T <= 0: return max(0.0, S - K), max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * cdf_normal(d1) - K * math.exp(-r * T) * cdf_normal(d2), K * math.exp(-r * T) * cdf_normal(-d2) - S * cdf_normal(-d1)

def get_index_weekly_html(symbol, expiry_day, title):
    start_date = datetime.date(2025, 9, 1)
    payload = {"symbol": symbol, "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            candles = res.get('candles', [])
            if not candles: return f"<div style='color:orange; padding:10px;'>⚠️ {title}: डेटा रिकामा मिळाला. (आज सुट्टी असू शकते)</div>"
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            df['Day of Week'] = pd.to_datetime(df['Date']).dt.weekday
            weekly_df = df[df['Day of Week'] == expiry_day].sort_values(by='Date').copy()
            weekly_df['Weekly Change Raw'] = weekly_df['Close'].pct_change() * 100
            weekly_df = weekly_df.dropna(subset=['Weekly Change Raw'])
            
            rows = ""
            for idx, row in weekly_df.iterrows():
                exp_dt = row['Date'].strftime("%Y-%m-%d")
                day_lbl = "Tue" if expiry_day == 1 else "Thu"
                c_style = "color: #28a745; font-weight: bold;" if row['Weekly Change Raw'] > 0 else "color: #dc3545; font-weight: bold;"
                rows += f"<tr><td>{exp_dt} ({day_lbl})</td><td data-val='{row['Close']}'>{row['Close']:,.2f}</td><td style='{c_style}'>{row['Weekly Change Raw']:+.2f}%</td></tr>"
            return f"<h3>{title}</h3><table><thead><tr><th>तारीख</th><th>क्लोज प्राईस</th><th>बदल %</th></tr></thead><tbody>{rows}</tbody></table>"
        else:
            return f"<div style='color:orange; padding:10px;'>⚠️ {title}: लाइव्ह मार्केट बंद आहे. उद्या सोमवारपासून डेटा चालू होईल.</div>"
    except Exception as e: 
        return f"<div style='color:red; padding:10px;'>❌ {title} Exception: {str(e)}</div>"

def get_options_backtest_html():
    start_date = datetime.date(2025, 9, 1)
    payload = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            df = pd.DataFrame(res.get('candles', []), columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            weekly_df = df[pd.to_datetime(df['Date']).dt.weekday == 1].sort_values(by='Date').copy()
            rows = ""
            for i in range(1, len(weekly_df)):
                p_row, c_row = weekly_df.iloc[i-1], weekly_df.iloc[i]
                atm = int(round(p_row['Close'] / 50) * 50)
                ce_en, pe_en = black_scholes_options(p_row['Close'], atm, 5/365, 0.07, 0.12)
                ce_ex, pe_ex = max(0.0, c_row['Close'] - atm), max(0.0, atm - c_row['Close'])
                ce_p = ((ce_ex - ce_en) / ce_en) * 100 if ce_en > 0 else 0.0
                pe_p = ((pe_ex - pe_en) / pe_en) * 100 if pe_en > 0 else 0.0
                rows += f"<tr><td>{p_row['Date']} ते {c_row['Date']}</td><td>{atm}</td><td>{p_row['Close']:.2f}➔{c_row['Close']:.2f}</td><td style='color: {'#28a745' if ce_p>0 else '#dc3545'}; font-weight: bold;'>{ce_p:+.2f}%</td><td style='color: {'#28a745' if pe_p>0 else '#dc3545'}; font-weight: bold;'>{pe_p:+.2f}%</td></tr>"
            return f"<h3>Nifty 50 Options Backtest (ATM CE / PE)</h3><table><thead><tr><th>कालावधी</th><th>ATM स्ट्राईक</th><th>स्पॉट प्रवास</th><th>Call % बदल</th><th>Put % बदल</th></tr></thead><tbody>{rows}</tbody></table>"
    except: pass
    return ""

nifty_html = get_index_weekly_html("NSE:NIFTY50-INDEX", 1, "Nifty 50 Spot Weekly Report (Tuesday Expiry)")
sensex_html = get_index_weekly_html("BSE:SENSEX-INDEX", 3, "BSE Sensex Spot Weekly Report (Thursday Expiry)")
options_html = get_options_backtest_html()

full_template = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Live Dashboard</title>
<style>body {{ font-family: sans-serif; background-color: #f4f6f9; padding: 20px; }} .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; }} h2, h3 {{ text-align: center; color: #0056b3; }} table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }} th, td {{ padding: 12px; border: 1px solid #dee2e6; text-align: center; }} th {{ background-color: #007bff; color: white; }} tr:nth-child(even) {{ background-color: #f8f9fa; }}</style></head><body><div class="container"><h2>📊 LIVE OPTIONS & EXPIRES MASTER DASHBOARD</h2>{nifty_html}{sensex_html}{options_html}</div></body></html>"""

os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f: 
    f.write(full_template)
print("Dashboard status generated successfully!")
