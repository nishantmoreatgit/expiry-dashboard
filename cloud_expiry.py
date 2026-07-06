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
def generate_live_dashboard():
    # Dynamic date window generation
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
            
            # 1. Generate active top live row block
            live_row = df.iloc[0]
            change_color = "green" if live_row['Change_Pct'] >= 0 else "red"
            sign = "+" if live_row['Change_Pct'] >= 0 else ""
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_row['Close']:,} (Today)</td><td style='color: {change_color};'>{sign}{live_row['Change_Pct']:.2f}%</td></tr>\n"
            
            # 2. Extract historical Tuesday expirations
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # Complete independent framework page layout template
            full_master_page = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="60">
    <title>CLOUD LIVE INTRA-DAY MASTER DASHBOARD</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f9f9f9; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 800px; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
        th {{ background-color: #f2f2f2; }}
        h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h2>📊 CLOUD LIVE INTRA-DAY MASTER DASHBOARD</h2>
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
</html>"""
            return full_master_page
        else:
            print(f"❌ Fyers Error tracking channel: {res}")
            return None
    except Exception as e:
        print(f"❌ Critical runtime core exception: {e}")
        return None

# =====================================================================
# 💾 Execute Absolute File Overwrite Array Sync
# =====================================================================
updated_dashboard_html = generate_live_dashboard()

if updated_dashboard_html:
    target_file = "index.html"
    try:
        # Force writing fresh clean templates to guarantee changes are detected by Git
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(updated_dashboard_html)
        print(f"💾 Success: Fresh dataset hard-written over {target_file} layout space!")
    except Exception as e:
        print(f"❌ Write permission dropped: {e}")
