import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब सिक्रेट्समधून थेट व्हॅलिड ऍक्सेस टोकन आणि ॲप आयडी वाचणे
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         # तुमचा Fyers App ID
access_token = os.environ.get('FY_LIVE_TOKEN')   # तुमचा आजचा लाइव्ह ऍक्सेस टोकन

if not client_id or not access_token:
    print("❌ एरर: गिटहब सिक्रेट्समधून FY_APP_ID किंवा FY_LIVE_TOKEN मिळाला नाही!")
    print(f"🔍 सद्यस्थिती -> App ID मिळाला का?: {'होय' if client_id else 'नाही'}, Token मिळाला का?: {'होय' if access_token else 'नाही'}")
    sys.exit(1)

print("✅ क्रेडेंशियल्स मिळाले! फायर्स क्लायंट सुरू करत आहे...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📈 डेटा फेचिंग फंक्शन्स (Data Fetch)
# =====================================================================
def get_index_weekly_html(symbol, title):
    # २०२६ मधील चालू महिन्याचा डेटा घेण्यासाठी तारीख डायनॅमिक केली आहे
    start_date = datetime.date.today() - datetime.timedelta(days=30)
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
                return f"<div>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            print(f"📊 {title} लाइव्ह डेटा यशस्वी! शेवटची क्लोजिंग किंमत: {df['Close'].iloc[-1]}")
            return df.to_html()
        else:
            print(f"❌ फियर्स हिस्ट्री एरर रिस्पॉन्स: {res}")
            return f"<div>⚠️ एरर: {res.get('message', 'माहिती मिळू शकली नाही')}</div>"
    except Exception as e_hist:
        print(f"❌ हिस्ट्री API कॉल अयशस्वी: {e_hist}")
        return f"<div>⚠️ एक्सेप्शन एरर: {str(e_hist)}</div>"

# टेस्ट रन
html_table = get_index_weekly_html("NSE:NIFTY50-INDEX", "Nifty 50 Weekly")
