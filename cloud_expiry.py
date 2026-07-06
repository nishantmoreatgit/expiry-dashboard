import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 Secure Credentials from GitHub Secrets
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
secret_key = os.environ.get('FY_SECRET_KEY')     
refresh_token = os.environ.get('FY_REFRESH_TOKEN') # 👈 Your stable local token map
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    """Uses a secure Refresh Token to automatically build active daily access keys."""
    try:
        if not all([client_id, secret_key, refresh_token]):
            print("❌ Error: Missing mandatory FY_APP_ID, FY_SECRET_KEY, or FY_REFRESH_TOKEN in GitHub configuration.")
            return None

        # Initialize the official session handler
        session_instance = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="refresh_token" # 👈 Telling Fyers to use a refresh workflow
        )

        # Securely pass your existing background token string
        session_instance.set_token(refresh_token)
        
        # Request a fresh dynamic 24-hour Access Token seamlessly
        print("🔗 Querying Fyers API token gateway using cloud-safe refresh mapping...")
        response = session_instance.generate_token()
        
        if "access_token" in response:
            return response.get("access_token")
        else:
            print(f"❌ Token Generation Failed: {response}")
            return None
        
    except Exception as e:
        print(f"❌ Core Refresh Exception: {e}")
        return None

# Generate token on GitHub environment
access_token = get_automated_access_token()

if not access_token:
    print("🚨 Access token acquisition failed completely. Exiting framework processing.")
    sys.exit(1)

print("✅ Live Token generated successfully using refresh tokens! Fetching live market metrics...")
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
    # Adjusted start date dynamically to prevent payload bounds overflow
    start_date = datetime.date(2026, 1, 1)
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
                print(f"⚠️ {title}: No candle records found in current date window.")
                return f"<div>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"📊 {title} Live Data Success! Latest Close Vector: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ Fyers History Error Response: {res}")
            return f"<div>⚠️ Error processing history payload: {res.get('message')}</div>"
    except Exception as e_hist:
        print(f"❌ Active history data pull exception: {e_hist}")
        return f"<div>⚠️ Execution Error: {str(e_hist)}</div>"

# Execute testing runtime run verification
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "Thursday", "Nifty 50 Weekly")
