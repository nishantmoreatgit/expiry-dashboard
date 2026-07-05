import datetime
import math
import pandas as pd
import os
from fyers_apiv3 import fyersModel

# =====================================================================
# 🔐 गिटहब लॉकर (Secrets) मधून मॅन्युअल ऍक्सेस टोकन आपोआप वाचणे
# =====================================================================
client_id = "RAE54K69M5-100" 
access_token = os.environ.get('FY_ACCESS_TOKEN')
# =====================================================================

if not access_token:
    print("⚠️ वॉर्निंग: 'FY_ACCESS_TOKEN' सापडला नाही. बॅकअप टोकन वापरत आहे...")
    access_token = "EXPIRED_TOKEN_FOR_TESTING"

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

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
            if not candles: return f"<div style='color:orange; padding:10px;'>⚠️ {title}: डेटा रिकामा मिळाला.</div>"
            
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
                    <td>🔴 CLOUD LIVE (Last Fetch)</td>
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
            
            return f"<h3>{title}</h3><table><thead><tr><th>तारीख</th><th>क्लोज प्राईस</th><th>बदल %</th></tr></thead><tbody>{live_row_html}{rows}</tbody></table>"
    except: pass
    return ""

def get_options_backtest_html():
    start_date = datetime.date(2025, 9, 1)
    payload = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            df = pd.DataFrame(res.get('candles', []), columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
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
                rows += f"<tr><td>{p_row['Date']} ते {c_row['Date']}</td><td data-val='{atm}'>{atm}</td><td>{p_row['Close']:.2f}➔{c_row['Close']:.2f}</td><td style='{ce_style}'>{ce_p:+.2f}%</td><td style='{pe_style}'>{pe_p:+.2f}%</td></tr>"
            return f"<h3>Nifty 50 Options Backtest (ATM CE / PE)</h3><table><thead><tr><th>कालावधी ▲▼</th><th>ATM स्ट्राईक ▲▼</th><th>स्पॉट प्रवास</th><th>Call % बदल ▲▼</th><th>Put % बदल ▲▼</th></tr></thead><tbody>{rows}</tbody></table>"
    except: pass
    return ""

nifty_html = get_index_weekly_html("NSE:NIFTY50-INDEX", 1, "Nifty 50 Spot Weekly Report (Tuesday Expiry)")
sensex_html = get_index_weekly_html("BSE:SENSEX-INDEX", 3, "BSE Sensex Spot Weekly Report (Thursday Expiry)")
options_html = get_options_backtest_html()

# HTML डिझाइनमध्ये उजव्या कोपऱ्यात Live Clock चे स्टायलिंग आणि JavaScript जोडले आहे
full_template = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="300"><title>Cloud Live Dashboard</title>
<style>
body {{ font-family: sans-serif; background-color: #f4f6f9; padding: 20px; }} 
.container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; position: relative; }} 
h2, h3 {{ text-align: center; color: #0056b3; }} 
table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }} 
th, td {{ padding: 12px; border: 1px solid #dee2e6; text-align: center; }} 
th {{ background-color: #007bff; color: white; }} 
tr:nth-child(even) {{ background-color: #f8f9fa; }}
/* 🕒 लाईव्ह घड्याळाचे सुंदर स्टायलिंग (Right Corner) */
.live-clock-box {{ position: absolute; top: 25px; right: 25px; background: #212529; color: #00ff66; padding: 8px 15px; border-radius: 6px; font-family: monospace; font-size: 16px; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
</style></head>
<body>
<div class="container">
    <!-- घड्याळाचा बॉक्स -->
    <div class="live-clock-box">⏰ MARKET TIME: <span id="clockDisplay">00:00:00</span></div>
    <h2>📊 CLOUD LIVE INTRA-DAY MASTER DASHBOARD</h2>
    {nifty_html}{sensex_html}{options_html}
</div>
<script>
// ⏱️ दर सेकंदाला मिनिटे आणि सेकंद बदलणारे JavaScript घड्याळ
function updateClock() {{
    let now = new Date();
    let hours = String(now.getHours()).padStart(2, '0');
    let minutes = String(now.getMinutes()).padStart(2, '0');
    let seconds = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('clockDisplay').textContent = hours + ":" + minutes + ":" + seconds;
}}
setInterval(updateClock, 1000); // दर १,००० मिलीसेकंद (१ सेकंड) ला रन होईल
updateClock(); // पेज लोड झाल्यावर लगेच सुरू होईल
</script>
</body></html>"""

os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f: 
    f.write(full_template)
print("Cloud Live Dashboard with Tick Clock Generated!")
