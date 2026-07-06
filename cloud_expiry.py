import datetime
import math
import os
import sys
import pyotp
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 Secure Credentials from GitHub Secrets
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
secret_key = os.environ.get('FY_SECRET_KEY')     
totp_key = os.environ.get('FY_TOTP_KEY')         
pin = os.environ.get('FY_PIN')                   
fyers_id = os.environ.get('FYERS_ID')             
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    """Generates the mandatory daily token using official Fyers SDK integration endpoints."""
    try:
        if not all([client_id, secret_key, totp_key, pin, fyers_id]):
            print("❌ Error: Missing credentials in GitHub Secrets mapping environment variables.")
            return None

        # Step 1: Generate dynamic TOTP
        clean_totp_key = totp_key.replace(" ", "")
        totp = pyotp.TOTP(clean_totp_key)
        current_otp = totp.now()

        # Step 2: Initialize Session Model directly using the official SDK wrapper
        # This completely replaces the broken manual requests.post code.
        session_instance = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )

        # Step 3: Use the official SDK internal helper to validate and fetch auth_code
        print("🔗 Authenticating with Fyers servers via official SDK instance...")
        
        # Simulating the parameters to complete authorization cleanly
        # Fyers requires a direct manual URL redirect or an authorization token generated token code
        # Since manual requests are cloud-blocked, we use the token parsing pipeline.
        
        # Check if we can exchange via direct authentication URL mapping
        auth_url = session_instance.generate_authcode()
        print(f"✅ Authorization pipeline initialized. Attempting token generation...")

        # If you have an active access token generated manually today, you can also fall back to it
        # For full background automation, we run the token structure:
        response = session_instance.generate_token()
        
        if "access_token" in response:
            return response.get("access_token")
        else:
            print(f"❌ Token Generation Error: SDK Response -> {response}")
            # Printing additional details to help debug if it fails here
            if "message" in response:
                print(f"💡 Fyers Message: {response.get('message')}")
            return None
        
    except Exception as e:
        print(f"❌ System Automation Blocked: {e}")
        return None

# Execute runtime authorization
access_token = get_automated_access_token()

if not access_token:
    print("🚨 Access token acquisition failed. Terminating engine.")
    sys.exit(1)

print("✅ Access token verified! Fetching live data matrices...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📈 Mathematical Calculations and Data Fetch
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
                print(f"⚠️ {title}: Empty candle data package returned.")
                return f"<div>⚠️ {title}: No Data Found.</div>"
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"📊 {title} Fetch Successful! Latest Close Price: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ Fyers History Error Response: {res}")
            return f"<div>⚠️ Error: {res.get('message', 'Failed to retrieve data')}</div>"
    except Exception as e_hist:
        print(f"❌ History Call Exception: {e_hist}")
        return f"<div>⚠️ Exception: {str(e_hist)}</div>"

# Run data pipeline verification
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "Thursday", "Nifty 50 Weekly")
