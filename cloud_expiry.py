import datetime
import math
import pandas as pd
import os
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब लॉकर (Secrets) मधून मॅन्युअल ऍक्सेस टोकन आपोआप वाचणे
# =====================================================================
access_token = os.environ.get('FY_ACCESS_TOKEN')
client_id = "RAE54K69M5-100" 
# =====================================================================

if not access_token or access_token == "EXPIRED_TOKEN_FOR_TESTING":
    print("⚠️ वॉर्निंग: 'FY_ACCESS_TOKEN' अजून सेट केलेला नाही.")
    access_token = "DUMMY_TOKEN"

# एरर हँडलर चौकटीसह फायर्स मॉडेल सुरू करणे
try:
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")
except Exception as e_init:
    print(f"Fyers Init Info: {e_init}")

def cdf_normal(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_options(S, K, T, r, sigma):
    if T <= 0: return max(0.0, S - K), max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * cdf_normal(d1) - K * math.exp(-r * T) * cdf_normal(d2), K * math.exp(-r * T) * cdf_normal(-d2) - S * cdf_normal(-d1)

def get_index_weekly_html(symbol, expiry_day, title):
    start_date = datetime.date(2025, 9, 1)
    payload = {"symbol": symbol, "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            candles = res.get('candles', [])
            if not candles: return f"<div style='color:orange; padding:10px;'>⚠️ {title}: डेटा मिळाला नाही.</div>"
            
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            df['Day of Week'] = pd.to_datetime(df['Date']).dt.weekday
            
            weekly_df = df[df['Day of Week'] == expiry_day].sort_values(by='Date').copy()
            weekly_df['Weekly Change Raw'] = weekly_df['Close'].pct_change() * 100
            weekly_df = weekly_df.dropna(subset=['Weekly Change Raw'])
            
            today = datetime.date.today()
            offset = (today.weekday() - expiry_day) % 7
            if offset == 0: offset = 7
            last_expiry_date = today - datetime.timedelta(days=offset)
            
            live_close = df.iloc[-1]['Close']
            try:
                quotes_res = fyers.quotes(data={"symbols": symbol})
                if quotes_res and quotes_res.get('s') == 'ok':
                    live_close = quotes_res.get('d', [{}]).get('v', {}).get('lp', live_close)
            except: pass
            
            live_row_html = ""
            try:
                last_expiry_data = df[df['Date'] <= last_expiry_date].iloc[-1]
                expiry_close = last_expiry_data['Close']
                live_pct_change = ((live_close - expiry_close) / expiry_close) * 100
                live_color = "color: #28a745; font-weight: bold; background-color: #e8f5e9;" if live_pct_change > 0 else "color: #dc3545; font-weight: bold; background-color: #ffebee;"
                
                live_row_html = f"""
                <tr style="background-color: #fff9db; border: 2px solid #ff922b; font-weight: bold;">
                    <td>🔴 CLOUD LIVE (Intraday LTP)</td>
                    <td data-val="{live_close}">{live_close:,.2f}</td>
                    <td data-val="{live_pct_change}" style="{live_color}">{live_pct_change:+.2f}%</td>
                </tr>
                """
            except: pass
            
            rows = ""
            for idx, row in weekly_df.iterrows():
                exp_dt = row['Date'].strftime("%Y-%m-%d")
                day_lbl = "Tue" if expiry_day == 1 else "Thu"
                c_style = "color: #28a745; font-weight: bold;" if row['Weekly Change Raw'] > 0 else "color: #dc3545; font-weight: bold;"
                rows += f"<tr><td>{exp_dt} ({day_lbl})</td><td data-val='{row['Close']}'>{row['Close']:,.2f}</td><td style='{c_style}' data-val='{row['Weekly Change Raw']}'>{row['Weekly Change Raw']:+.2f}%</td></tr>"
            
            return f"<h3>{title}</h3><div class='table-responsive'><table><thead><tr><th onclick='sortTable(this,0)'>तारीख ▲▼</th><th onclick='sortTable(this,1)'>क्लोज प्राईस ▲▼</th><th onclick='sortTable(this,2)'>बदल % ▲▼</th></tr></thead><tbody>{live_row_html}{rows}</tbody></table></div>"
        else:
            return f"<div style='color:red; padding:20px; font-weight:bold;'>⚠️ FYERS API: {title} साठी वैध टोकन आवश्यक आहे. (उद्या सकाळी नवीन टोकन टाका)</div>"
    except Exception as e: 
        return f"<div style='color:red; padding:10px;'>❌ {title} Exception: {str(e)}</div>"

def get_options_backtest_html():
    start_date = datetime.date(2025, 9, 1)
    payload = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            df = pd.DataFrame(res.get('candles', []), columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            # येथे 'dt.weekday' दुरुस्त केले आहे
            weekly_df = df[pd.to_datetime(df['Date']).dt.weekday == 1].sort_values(by='Date').copy()
            rows = ""
            for i in range(1, len(weekly_df)):
                p_row, c_row = weekly_df.iloc[i-1], weekly_df.iloc[i]
                atm = int(round(p_row['Close'] / 50) * 50)
                ce_en, pe_en = black_scholes_options(p_row['Close'], atm, 5/365, 0.07, 0.12)
                ce_ex, pe_ex = max(0.0, c_row['Close'] - atm), max(0.0, atm - c_row['Close'])
                ce_p = ((ce_ex - ce_en) / ce_en) * 100 if ce_en > 0 else 0.0
                pe_p = ((pe_ex - pe_en) / pe_en) * 100 if pe_en > 0 else 0.0
                ce_style = "color: #28a745; font-weight: bold;" if ce_p > 0 else "color: #dc3545;"
                pe_style = "color: #28a745; font-weight: bold;" if pe_p > 0 else "color: #dc3545;"
                rows += f"<tr><td>{p_row['Date']} ते {c_row['Date']}</td><td data-val='{atm}'>{atm}</td><td>{p_row['Close']:.2f}➔{c_row['Close']:.2f}</td><td style='{ce_style}' data-val='{ce_p}'>{ce_p:+.2f}%</td><td style='{pe_style}' data-val='{pe_p}'>{pe_p:+.2f}%</td></tr>"
            return f"<h3>Nifty 50 Options Backtest (ATM CE / PE)</h3><div class='table-responsive'><table><thead><tr><th onclick='sortTable(this,0)'>कालावधी ▲▼</th><th onclick='sortTable(this,1)'>ATM स्ट्राईक ▲▼</th><th>स्पॉट प्रवास</th><th onclick='sortTable(this,3)'>Call % बदल ▲▼</th><th onclick='sortTable(this,4)'>Put % बदल ▲▼</th></tr></thead><tbody>{rows}</tbody></table></div>"
        else:
            return f"<div style='color:orange; padding:20px; text-align:center; font-weight:bold;'>📉 ऑप्शन्स बॅकटेस्ट: नवीन टोकन प्रलंबित आहे.</div>"
    except: pass
    return ""

nifty_html = get_index_weekly_html("NSE:NIFTY50-INDEX", 1, "Nifty 50 Spot Weekly Report (Tuesday Expiry)")
sensex_html = get_index_weekly_html("BSE:SENSEX-INDEX", 3, "BSE Sensex Spot Weekly Report (Thursday Expiry)")
options_html = get_options_backtest_html()

# HTML टेम्पलेट अचूक क्लोजिंग ट्रिपल कोट्ससह (""") दुरुस्त केले आहे
full_template = f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>Mobile Friendly Live Dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; padding: 15px; margin: 0; }} 
.container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }} 
h2 {{ text-align: center; color: #0056b3; font-size: 22px; margin-top: 5px; line-height: 1.3; }}
h3 {{ text-align: center; color: #212529; font-size: 18px; margin-top: 30px; border-bottom: 2px solid #dee2e6; padding-bottom: 6px; }} 
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; min-width: 500px; }} 
th, td {{ padding: 10px 12px; border: 1px solid #dee2e6; text-align: center; }} 
th {{ background-color: #007bff; color: white; cursor: pointer; user-select: none; }} 
tr:nth-child(even) {{ background-color: #f8f9fa; }}
.table-responsive {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 15px; border-radius: 6px; }}

.mega-live-clock {{ 
    text-align: center; 
    margin: 15px auto; 
    background: #1a1d20; 
    color: #00ff66; 
    padding: 10px 25px; 
    border-radius: 8px; 
    font-family: 'Courier New', Courier, monospace; 
    font-size: 28px; 
    font-weight: bold; 
    width: fit-content; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.2); 
    letter-spacing: 1px;
}}

@media (min-width: 768px) {{
    body {{ padding: 25px; }}
    .container {{ padding: 30px; }}
    h2 {{ font-size: 28px; }}
    h3 {{ font-size: 22px; }}
    table {{ font-size: 16px; }}
    th, td {{ padding: 14px 18px; }}
    .mega-live-clock {{ font-size: 35px; padding: 15px 35px; }}
}}
</style></head>
<body>
<div class="container">
    <h2>📊 CLOUD LIVE INTRA-DAY MASTER DASHBOARD</h2>
    <div class="mega-live-clock">⏰ <span id="clockDisplay">00:00:00</span></div>
    {nifty_html}{sensex_html}{options_html}
</div>
<script>
function updateClock() {{
    let now = new Date();
    let hours = String(now.getHours()).padStart(2, '0');
    let minutes = String(now.getMinutes()).padStart(2, '0');
    let seconds = String(now.getSeconds()).padStart(2, '0');
