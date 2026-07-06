import datetime
import math
import os
import pandas as pd
import pyotp
import requests
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersConnect import session

# =====================================================================
# 🔐 SECURE CREDENTIALS FROM GITHUB SECRETS
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         # Your App ID (e.g. RAE54K69M5-100)
secret_key = os.environ.get('FY_SECRET_KEY')     # Your Fyers Secret Key
totp_key = os.environ.get('FY_TOTP_KEY')         # String key from Fyers External TOTP setup
pin = os.environ.get('FY_PIN')                   # Your 4-digit Fyers login PIN
fyers_id = os.environ.get('FYERS_ID')             # Your Fyers Client ID login name (e.g. XY12345)
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    """Simulates Fyers interactive login to pull the true daily access token."""
    try:
        # Step 1: Generate dynamic 6-digit TOTP
        totp = pyotp.TOTP(totp_key)
        current_otp = totp.now()

        # Step 2: Request Send OTP via API backend
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        payload_totp = {"client_id": client_id, "fyers_id": fyers_id, "totp": current_otp}
        res_totp = requests.post("https://fyers.in", json=payload_totp, headers=headers).json()
        
        if res_totp.get('s') != 'ok':
            raise Exception(f"TOTP Validation Failed: {res_totp.get('message')}")
            
        request_key = res_totp.get('request_key')

        # Step 3: Validate PIN
        payload_pin = {"client_id": client_id, "request_key": request_key, "pin": pin}
        res_pin = requests.post("https://fyers.in", json=payload_pin, headers=headers).json()
        
        if res_pin.get('s') != 'ok':
            raise Exception(f"PIN Validation Failed: {res_pin.get('message')}")
            
        access_token_temp = res_pin.get('data', {}).get('access_token')

        # Step 4: Generate Auth Code via OAuth Redirect Simulation
        oauth_headers = {'Authorization': f"Bearer {access_token_temp}"}
        oauth_payload = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": "sample_state"
        }
        res_oauth = requests.post("https://fyers.in", json=oauth_payload, headers=oauth_headers).json()
        
        # Extract auth code from redirect target URL
        target_url = res_oauth.get('data', {}).get('redirect_url', '')
        auth_code = target_url.split('auth_code=')[1].split('&')[0]

        # Step 5: Final Token Generation via Fyers SDK
        fyers_session = session.FyersSession(
            client_id=client_id, secret_key=secret_key,
            redirect_uri=redirect_uri, response_type="code"
        )
        fyers_session.set_token(auth_code)
        response = fyers_session.generate_token()
        return response.get("access_token")
        
    except Exception as e:
        print(f"❌ Automation Error: {e}")
        return None

# Generate token on GitHub environment
access_token = get_automated_access_token()

if not access_token:
    print("🚨 Token generation failed. Exiting script.")
    exit(1)

# Initialize Fyers client with the fresh active daily token
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
                print(f"⚠️ {title}: No candles found in data.")
                return f"<div style='color:orange; padding:10px;'>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            # Repaired completion of your truncated script code
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"✅ Successfully fetched data for {title}. Latest Close: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ Fyers Error Response: {res}")
            return f"<div style='color:red;'>⚠️ Error: {res.get('message', 'Unknown Error')}</div>"
    except Exception as e_hist:
        print(f"❌ History call failed: {e_hist}")
        return f"<div style='color:red;'>⚠️ Exception: {str(e_hist)}</div>"

# Execution test run command inside the runner
html_output = get_index_weekly_html("NSE:NIFTY50-INDEX", "Thursday", "Nifty 50 Weekly")
