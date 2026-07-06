import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 Fetch secure runtime token environments from GitHub Actions
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
def force_rebuild_dashboard():
    symbol = "NSE:NIFTY50-INDEX"
    current_date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 1. Fetch real-time live value using the 1-Minute historical candle endpoint
    live_close = 0.0
    live_change = 0.0
    
    try:
        live_payload = {
            "symbol": symbol,
            "resolution": "1",
            "date_format": "1",
            "range_from": current_date_str,
            "range_to": current_date_str,
            "cont_flag": "1"
        }
        live_res = fyers.history(data=live_payload)
        if live_res and live_res.get('code') == 200:
            live_candles = live_res.get('candles', [])
            if live_candles:
                # ✅ FIX: Safely parse the last element as a structured index list rather than an object
                latest_candle = live_candles[-1]
                if isinstance(latest_candle, list) and len(latest_candle) >= 5:
                    live_close = float(latest_candle[4]) # Index 4 contains the sub-minute close price
                else:
                    live_close = float(latest_candle)
                print(f"🎯 1-Minute override extracted live market value: {live_close}")
    except Exception as e_live:
        print(f"⚠️ 1-Minute tick extraction skipped: {e_live}")

    # 2. Extract standard historical Tuesday records using Daily indicators
    start_date = datetime.date.today() - datetime.timedelta(days=120)
    history_payload = {
        "symbol": symbol, 
        "resolution": "D", 
        "date_format": "1", 
        "range_from": start_date.strftime("%Y-%m-%d"), 
        "range_to": current_date_str, 
        "cont_flag": "1"
    }
    
    try:
        res = fyers.history(data=history_payload)
        if res and res.get('code') == 200:
            candles = res.get('candles', [])
            if not candles: 
                print("⚠️ Daily index tracking framework returned empty lists.")
                return None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # Form accurate change ratios across historical nodes
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            
            # Fall back to standard end-of-day daily indicators if live tick fails
            if live_close == 0.0:
                live_close = float(df['Close'].values[-1])
                live_change = float(df['Change_Pct'].values[-1])
            else:
                # Generate accurate change percentage ratios compared to yesterday's closing price
                prev_day_close = float(df['Close'].values[-2]) if len(df) > 1 else float(df['Close'].values[-1])
                live_change = ((live_close - prev_day_close) / prev_day_close) * 100
            
            # Sort the data frame so that the newest records appear at the top
            df = df.sort_values(by='Date', ascending=False)
            
            html_rows = ""
            change_color = "green" if live_change >= 0 else "red"
            sign = "+" if live_change >= 0 else ""
            
            # Inject live tracking row into the data table structure
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_close:,.2f} ({current_date_str})</td><td style='color: {change_color};'>{sign}{live_change:.2f}%</td></tr>\n"
            
            # Filter and append specific Tuesday expiration metrics (Tuesday Expiry)
            for _, row in df.iterrows():
                if row['Date'] == datetime.date.today():
                    continue
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,.2f}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # Generate the final independent HTML page structure
            full_master_dashboard = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
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
            return full_master_dashboard
        else:
            print(f"❌ Fyers History Query Rejected: {res}")
            return None
    except Exception as e:
        print(f"❌ Core processing error occurred: {e}")
        return None

# =====================================================================
# 💾 Execute absolute overwrite file operation
# =====================================================================
fresh_dashboard_html = force_rebuild_dashboard()

if fresh_dashboard_html:
    target_file = "index.html"
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(fresh_dashboard_html)
        print(f"💾 Success: {target_file} updated cleanly with true live tick metrics!")
    except Exception as e:
        print(f"❌ File saving operation dropped: {e}")
