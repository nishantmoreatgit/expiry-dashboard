import os
import sys
import pyotp
import requests
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersConnect import session

# Fetch credentials from GitHub Secrets
client_id = os.environ.get('FY_APP_ID')         
secret_key = os.environ.get('FY_SECRET_KEY')     
totp_key = os.environ.get('FY_TOTP_KEY')         
pin = os.environ.get('FY_PIN')                   
fyers_id = os.environ.get('FYERS_ID')             
redirect_uri = "https://fyers.in"

def get_automated_access_token():
    try:
        # Step 1: Generate dynamic TOTP
        totp = pyotp.TOTP(totp_key.replace(" ", ""))  # strip spaces if any
        current_otp = totp.now()

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        
        # Step 2: Validate TOTP
        payload_totp = {"client_id": client_id, "fyers_id": fyers_id, "totp": current_otp}
        res_totp = requests.post("https://fyers.in", json=payload_totp, headers=headers).json()
        if res_totp.get('s') != 'ok':
            print(f"❌ TOTP Error: {res_totp}")
            return None
            
        request_key = res_totp.get('request_key')

        # Step 3: Validate PIN
        payload_pin = {"client_id": client_id, "request_key": request_key, "pin": pin}
        res_pin = requests.post("https://fyers.in", json=payload_pin, headers=headers).json()
        if res_pin.get('s') != 'ok':
            print(f"❌ PIN Error: {res_pin}")
            return None
            
        access_token_temp = res_pin.get('data', {}).get('access_token')

        # Step 4: Authorize OAuth 
        oauth_headers = {'Authorization': f"Bearer {access_token_temp}", 'Content-Type': 'application/json'}
        oauth_payload = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": "sample_state"
        }
        res_oauth = requests.post("https://fyers.in", json=oauth_payload, headers=oauth_headers).json()
        
        # Safe URL extraction fix
        target_url = res_oauth.get('data', {}).get('redirect_url', '')
        if not target_url or 'auth_code=' not in target_url:
            print(f"❌ OAuth Redirect Failed. API Response: {res_oauth}")
            return None

        # Extract auth code cleanly
        auth_code = target_url.split('auth_code=')[1].split('&')[0]

        # Step 5: Generate Final Access Token via SDK
        fyers_session = session.FyersSession(
            client_id=client_id, secret_key=secret_key,
            redirect_uri=redirect_uri, response_type="code"
        )
        fyers_session.set_token(auth_code)
        response = fyers_session.generate_token()
        return response.get("access_token")
        
    except Exception as e:
        print(f"❌ Automation Exception occurred: {e}")
        return None

access_token = get_automated_access_token()

if not access_token:
    print("🚨 Token authentication failed completely.")
    sys.exit(1) # Forces GitHub Actions to stop and show logs

print("✅ Token Generated Successfully! Fetching live data now...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# Rest of your math and get_index_weekly_html code follows...
