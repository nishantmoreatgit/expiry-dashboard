import datetime
import math
import os
import sys
import pandas as pd
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 Fetch secure live credentials from GitHub Actions Environment Maps
# =====================================================================
client_id = os.environ.get('FY_APP_ID')         
access_token = os.environ.get('FY_LIVE_TOKEN')   

if not client_id or not access_token:
    print("❌ Error: Missing credentials inside the runner environment!")
    sys.exit(1)

print("✅ Credentials verified! Connecting to Fyers API ecosystem...")
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# =====================================================================
# 📊 Fetch market candle matrices and generate responsive HTML layouts
# =====================================================================
def get_index_weekly_html(symbol, title):
    # Fetch previous historical vectors to fill database requirements 
    start_date = datetime.date.today() - datetime.timedelta(days=90)
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
                print(f"⚠️ {symbol}: Empty candle matrix returned.")
                return None, None
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            
            # Extract change metric arrays 
            df['Prev_Close'] = df['Close'].shift(1)
            df['Change_Pct'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
            df = df.iloc[::-1]
            
            html_rows = ""
            
            # 1. Inject Live data header tracking vector
            live_row = df.iloc[0]
            change_color = "green" if live_row['Change_Pct'] >= 0 else "red"
            sign = "+" if live_row['Change_Pct'] >= 0 else ""
            html_rows += f"<tr style='background-color: #ffe6e6; font-weight: bold;'><td>🔴 CLOUD LIVE (Last Fetch)</td><td>{live_row['Close']:,} (Today)</td><td style='color: {change_color};'>{sign}{live_row['Change_Pct']:.2f}%</td></tr>\n"
            
            # 2. Extract specific Tuesday expiration nodes (Tuesday Expiry filter)
            for _, row in df.iloc[1:].iterrows():
                dt = pd.to_datetime(row['Date'])
                if dt.strftime('%a') == "Tue":
                    row_color = "green" if row['Change_Pct'] >= 0 else "red"
                    row_sign = "+" if row['Change_Pct'] >= 0 else ""
                    html_rows += f"<tr><td>{row['Date']} (Tue)</td><td>{row['Close']:,}</td><td style='color: {row_color};'>{row_sign}{row['Change_Pct']:.2f}%</td></tr>\n"
            
            # Comprehensive master fallback HTML backup template layout
            full_html = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="60">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f9f9f9; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 800px; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
        th {{ background-color: #f2f2f2; }}
        h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h2>📊 {title}</h2>
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
            return html_rows, full_html
        else:
            print(f"❌ API Query Failed: {res}")
            return None, None
    except Exception as e:
        print(f"❌ Calculation Pipeline Interrupted: {e}")
        return None, None

# =====================================================================
# 💾 Secure Execution File Writing Engine 
# =====================================================================
html_table_rows, complete_html_page = get_index_weekly_html("NSE:NIFTY50-INDEX", "CLOUD LIVE INTRA-DAY MASTER DASHBOARD")

if html_table_rows and complete_html_page:
    dashboard_filename = "index.html"
    
    try:
        # Check and load existing layout models safely
        if os.path.exists(dashboard_filename):
            with open(dashboard_filename, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # If our explicit macro placeholder tag is active, replace it
            if "{{NIFTY_DATA}}" in html_content:
                updated_html = html_content.replace("{{NIFTY_DATA}}", html_table_rows)
                with open(dashboard_filename, "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print("💾 Success: Live row variables injected inside macro mapping placeholders!")
            else:
                # 🎯 AUTO-RECOVERY FIX: If placeholder isn't found, write the whole page layout cleanly!
                with open(dashboard_filename, "w", encoding="utf-8") as f:
                    f.write(complete_html_page)
                print("💾 Success: Re-compiled master HTML index layout container structure directly!")
        else:
            # Create a brand new workspace tracking container if missing entirely
            with open(dashboard_filename, "w", encoding="utf-8") as f:
                f.write(complete_html_page)
            print("💾 Success: Initialized pristine ecosystem dashboard index layout frame!")
                
    except Exception as e:
        print(f"❌ Write operation dropped: {e}")
else:
    print("🚨 Dataset extraction failed empty. Halting write sync arrays.")
