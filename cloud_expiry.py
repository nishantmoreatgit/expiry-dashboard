import datetime
import math
import os
import sys
import pyotp
import requests
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersConnect import session

# =====================================================================
# 🔐 SECURE CREDENTIALS FROM GITHUB SECRETS
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
secret_key = os.environ.get('FY_SECRET_KEY')     
totp_key = os.environ.get('FY_TOTP_KEY')         
pin = os.environ.get('FY_PIN')                   
fyers_id = os.environ.get('FYERS_ID')             
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    """Simulates a browser login to safely pull the daily access token on GitHub."""
    try:
        # Step 1: Clean and generate TOTP
        clean_totp_key = totp_key.replace(" ", "") if totp_key else ""
        totp = pyotp.TOTP(clean_totp_key)
        current_otp = totp.now()

        # Critical: Browser simulation headers to bypass cloud platform blocks
        headers = {
            'Accept': 'application/json', 
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Step 2: Validate TOTP
        payload_totp = {"client_id": client_id, "fyers_id": fyers_id, "totp": current_otp}
        res_totp = requests.post("https://fyers.in", json=payload_totp, headers=headers).json()
        if res_totp.get('s') != 'ok':
            print(f"❌ TOTP Step Failed: {res_totp}")
            return None
            
        request_key = res_totp.get('request_key')

        # Step 3: Validate PIN
        payload_pin = {"client_id": client_id, "request_key": request_key, "pin": pin}
        res_pin = requests.post("https://fyers.in", json=payload_pin, headers=headers).json()
        if res_pin.get('s') != 'ok':
            print(f"❌ PIN Step Failed: {res_pin}")
            return None
            
        access_token_temp = res_pin.get('data', {}).get('access_token')

        # Step 4: Request OAuth Authorization Link
        oauth_headers = {
            'Authorization': f"Bearer {access_token_temp}", 
            'Content-Type': 'application/json',
            'User-Agent': headers['User-Agent']
        }
        oauth_payload = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": "sample_state"
        }
        res_oauth = requests.post("https://fyers.in", json=oauth_payload, headers=oauth_headers).json()
        
        target_url = res_oauth.get('data', {}).get('redirect_url', '')
        if not target_url or 'auth_code=' not in target_url:
            print(f"❌ OAuth Extraction Failed. Response received: {res_oauth}")
            return None

        # Safe parsing fallback to avoid indexing crash (Exit Code 2)
        try:
            auth_code = target_url.split('auth_code=')[1].split('&')[0]
        except IndexError:
            print(f"❌ Structural crash parsing auth code from URL string: {target_url}")
            return None

        # Step 5: Trade Authentication Token Exchange via SDK
        fyers_session = session.FyersSession(
            client_id=client_id, secret_key=secret_key,
            redirect_uri=redirect_uri, response_type="code"
        )
        fyers_session.set_token(auth_code)
        response = fyers_session.generate_token()
        return response.get("access_token")
        
    except Exception as e:
        print(f"❌ Critical Core Exception: {e}")
        return None

# Execution Flow Gateway
access_token = get_automated_access_token()

if not access_token:
    print("🚨 Token acquisition completely failed. Exiting framework processing.")
    sys.exit(1)

print("✅ Live Token Acquired! Querying market database...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📈 MATHEMATICAL CALCULATIONS AND DATA FETCH
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
                print(f"⚠️ {title}: No candles returned inside history payload.")
                return f"<div>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            # Form complete pandas table cleanly
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"📊 {title} Data Success! Last Close Point: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ Market Request Rejected: {res}")
            return f"<div>⚠️ Error processing metrics: {res.get('message', 'Unknown API Error')}</div>"
    except Exception as e_hist:
        print(f"❌ Active call exception tracking: {e_hist}")
        return f"<div>⚠️ Exception tracking failure: {str(e_hist)}</div>"

# Run sample execution pipeline tracking validation
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "Thursday", "Nifty 50 Weekly")
