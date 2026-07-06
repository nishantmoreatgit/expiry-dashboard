import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 Fetch secure runtime token environments
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
access_token = os.environ.get('FY_LIVE_TOKEN')   

if not client_id or not access_token:
    print("❌ Error: Missing configuration parameters in environment maps.")
    sys.exit(1)

print("✅ Credentials verified! Initializing Fyers client channel...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 Process historical candle records and structure metrics
# =====================================================================
def get_live_data_rows():
    start_date = datetime.date.today() - datetime.timedelta(days=90)
    payload = {
        "symbol": "NSE:NIFTY50-INDEX", 
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
                print("⚠️ No data chunks found inside history matrix.")
                return None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            df = df.iloc[::-1]
            
            html_rows = ""
            
            # Extract current trading data nodes safely
            live_close = df['Close'].values[0]
            live_change = df['Change_Pct'].values[0]
            live_date = df['Date'].values[0]
            
            if pd.isna(live_change):
                live_change = 0.0
                
            change_color = "green" if live_change >= 0 else "red"
            sign = "+" if live_change >= 0 else ""
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_close:,.2f} ({live_date})</td><td style='color: {change_color};'>{sign}{live_change:.2f}%</td></tr>\n"
            
            # Isolate historical Tuesday expirations
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,.2f}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            return html_rows
        else:
            print(f"❌ Fyers Error tracking channel: {res}")
            return None
    except Exception as e:
        print(f"❌ Critical runtime core exception: {e}")
        return None

# =====================================================================
# 💾 Execute Template Macro Replacement Array Sync
# =====================================================================
live_matrix_rows = get_live_data_rows()
target_file = "index.html"

if live_matrix_rows:
    try:
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                template_content = f.read()
            
            # Inject live data rows into the template placeholder macro
            if "{{LIVE_NIFTY_MATRIX}}" in template_content:
                final_html = template_content.replace("{{LIVE_NIFTY_MATRIX}}", live_matrix_rows)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(final_html)
                print("💾 Success: Live row variables stitched into layout frame container!")
            else:
                print("⚠️ Warning: Macro string token placeholder missing inside template file.")
        else:
            print("❌ Error: index.html layout file template not discovered.")
    except Exception as e:
        print(f"❌ Write permission dropped: {e}")
