import datetime
import math
import os
import sys
import pyotp
import requests
import pandas as pd
# ✅ FIX: Import directly from the correct Fyers v3 module namespaces
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब सिक्रेट्स (Secrets) मधून क्रेडेंशियल्स वाचणे
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
secret_key = os.environ.get('FY_SECRET_KEY')     
totp_key = os.environ.get('FY_TOTP_KEY')         
pin = os.environ.get('FY_PIN')                   
fyers_id = os.environ.get('FYERS_ID')             
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    """स्वयंचलितपणे रोजचा नवीन टोकन तयार करणारी सिस्टीम"""
    try:
        if not all([client_id, secret_key, totp_key, pin, fyers_id]):
            print("❌ चूक: गिटहब सिक्रेट्समध्ये (FY_APP_ID, FY_SECRET_KEY, etc.) माहिती सेट करायची राहिली आहे!")
            return None

        # पायरी १: गुगल ऑथेंटिकेटरचा लाइव्ह ६ अंकी कोड तयार करणे
        clean_totp_key = totp_key.replace(" ", "")
        totp = pyotp.TOTP(clean_totp_key)
        current_otp = totp.now()

        headers = {
            'Accept': 'application/json', 
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # पायरी २: TOTP व्हॅलिडेट करणे
        payload_totp = {"client_id": client_id, "fyers_id": fyers_id, "totp": current_otp}
        res_totp = requests.post("https://fyers.in", json=payload_totp, headers=headers).json()
        if res_totp.get('s') != 'ok':
            print(f"❌ पायरी २ (TOTP Error): फियर्स रिस्पॉन्स -> {res_totp}")
            return None
            
        request_key = res_totp.get('request_key')

        # पायरी ३: लॉगिन पिन व्हॅलिडेट करणे
        payload_pin = {"client_id": client_id, "request_key": request_key, "pin": pin}
        res_pin = requests.post("https://fyers.in", json=payload_pin, headers=headers).json()
        if res_pin.get('s') != 'ok':
            print(f"❌ पायरी ३ (PIN Error): फियर्स रिस्पॉन्स -> {res_pin}")
            return None
            
        access_token_temp = res_pin.get('data', {}).get('access_token')

        # पायरी ४: ओ-ऑथ (OAuth) ऑथोरायझेशन链 लिंक मिळवणे
        oauth_headers = {'Authorization': f"Bearer {access_token_temp}", 'Content-Type': 'application/json', 'User-Agent': headers['User-Agent']}
        oauth_payload = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": "sample_state"}
        res_oauth = requests.post("https://fyers.in", json=oauth_payload, headers=oauth_headers).json()
        
        target_url = res_oauth.get('data', {}).get('redirect_url', '')
        if not target_url or 'auth_code=' not in target_url:
            print(f"❌ पायरी ४ (OAuth Error): ऑथ कोड मिळाला नाही. फियर्स रिस्पॉन्स -> {res_oauth}")
            return None

        # पायरी ४.५: स्ट्रिंग स्प्लिट करून ऑथ कोड काढणे
        try:
            url_parts = target_url.split('auth_code=')
            auth_code = url_parts[1].split('&')[0]
            print(f"🔍 ऑथ कोड (Auth Code) मिळाला.")
        except Exception as e_split:
            print(f"❌ ऑथ कोड स्प्लिट करताना एरर आली: {e_split} | URL: {target_url}")
            return None

        # ✅ FIX: Use fyersModel.SessionModel to create the daily authorization session handler
        fyers_session = fyersModel.SessionModel(
            client_id=client_id, secret_key=secret_key,
            redirect_uri=redirect_uri, response_type="code"
        )
        fyers_session.set_token(auth_code)
        response = fyers_session.generate_token()
        
        if "access_token" in response:
            return response.get("access_token")
        else:
            print(f"❌ पायरी ५ (Token Generation Error): SDK रिस्पॉन्स -> {response}")
            return None
        
    except Exception as e:
        print(f"❌ सिस्टीम ऑटोमेशन मध्ये अडथळा: {e}")
        return None

# टोकन जनरेशन सुरू करा
access_token = get_automated_access_token()

if not access_token:
    print("🚨 ॲक्सेस टोकन मिळाला नाही. कोड सुरक्षितपणे थांबवला जात आहे.")
    sys.exit(1)

print("✅ टोकन यशस्वीरित्या मिळाला! लाइव्ह डेटा फेच करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📈 गणिते आणि डेटा फेचिंग फंक्शन्स (Calculations & Data Fetch)
# =====================================================================
def cdf_normal(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_options(S, K, T, r, sigma):
    if T <= 0: return max(0.0, S - K), max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * cdf_normal(d1) - K * math.exp(-r * T) * cdf_normal(d2), K * math.exp(-r * T) * cdf_normal(-d2) - S * cdf_normal(-d1)

def get_index_weekly_html(symbol, expiry_day, title):
    start_date = datetime.date(2025, 9, 1)
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
                print(f"⚠️ {title}: कॅंडल्सचा डेटा रिकामा मिळाला.")
                return f"<div>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"📊 {title} डेटा यशस्वीरित्या मिळाला! शेवटची क्लोजिंग किंमत: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return f"<div>⚠️ एरर: {res.get('message', 'माहिती मिळू शकली नाही')}</div>"
    except Exception as e_hist:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e_hist}")
        return f"<div>⚠️ एक्सेप्शन एरर: {str(e_hist)}</div>"

# टेस्ट रन
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "Thursday", "Nifty 50 Weekly")
