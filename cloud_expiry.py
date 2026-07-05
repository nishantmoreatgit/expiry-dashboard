import datetime
import math
import pandas as pd
import os
from fyers_apiv3 import fyersModel

# १. तुमचे FYERS API क्रेडेंशियल्स आणि चालू अॅक्सेस टोकन टाका
client_id = "RAE54K69M5-100" 
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowliwieDoxIiwieDoyI10sImF0X2hhc2gi0iJnQUFBQUFCcVNVUjJHV1BFRTdhU2RuOV9ESXpQV1dSaXljSmE5ZnVsV3dud1luZzVCYkZMZmRCNmFOeGM0cG1oX0tNbVk0dlZtYzdWNVVfYmNXS0d1WTZMeGc0Q0UwaUw2LWVJdzduQlpURS1iSnZfcmEwWklaRT0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIxNTU0YzUxMDE4YTIzOTFjNjFiNTU0NTM3MGM5MDNkMWJjYmQ3MzBkODQ1YzBiYWJmYmY4MGQ3NyIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiRk4xMDY1IiwiYXBwVHlwZSI6MTAwLCJleHAiOjE3ODMyMTE0MDASImF0IjoxNzgzMTg2NTUwLCJzdWIiOiJhY2Nlc3NfdG9rZW4ifQ.pp7d8h61Y1TYC-48518ptstpZ7n4AwPzhZZz9dNsg8c"

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
    end_date = datetime.date.today()
    payload = {"symbol": symbol, "resolution": "D", "date_format": "1", "range_from": start_date.strftime("%Y-%m-%d"), "range_to": end_date.strftime("%Y-%m-%d"), "cont_flag": "1"}
    try:
        res = fyers.history(data=payload)
        if res and res.get('code') == 200:
            df = pd.DataFrame(res.get('candles', []), columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            df['Day of Week'] = pd.to_datetime(df['Date']).dt.weekday
            
            weekly_df = df[df['Day of Week'] == expiry_day].sort_values(by='Date').copy()
            weekly_df['Weekly Change Raw'] = weekly_df['Close'].pct_change() * 100
            weekly_df = weekly_df.dropna(subset=['Weekly Change Raw'])
            
            today = datetime.date.today()
            offset = (today.weekday() - expiry_day) % 7
            if offset == 0: offset = 7
            last_exp = today - datetime.timedelta(days=offset)
            live_html = ""
            try:
                l_exp_data = df[df['Date'] <= last_exp].iloc[-1]
                t_data = df.iloc[-1]
                if l_exp_data['Date'] != t_data['Date']:
                    l_change = ((t_data['Close'] - l_exp_data['Close']) / l_exp_data['Close']) * 100
                    l_bg = "background-color: #e8f5e9; color: #28a745;" if l_change > 0 else "background-color: #ffebee; color: #dc3545;"
                    live_html = f"<tr style='{l_bg} font-weight: bold;'><td>LIVE (Since {l_exp_data['Date'].strftime('%d-%b')})</td><td data-val='{t_data['Close']}'>{t_data['Close']:,.2f} (Today)</td><td data-val='{l_change}'>{l_change:+.2f}%</td></tr>"
            except: pass
            
            rows = ""
            for idx, row in weekly_df.iterrows():
                exp_dt = row['Date'].strftime("%Y-%m-%d")
                day_lbl = "Tue" if expiry_day == 1 else "Thu"
                c_style = "color: #28a745; font-weight: bold;" if row['Weekly Change Raw'] > 0 else "color: #dc3545; font-weight: bold;"
                rows += f"<tr><td data-val='{exp_dt}'>{exp_dt} ({day_lbl})</td><td data-val='{row['Close']}'>{row['Close']:,.2f}</td><td data-val='{row['Weekly Change Raw']}' style='{c_style}'>{row['Weekly Change Raw']:+.2f}%</td></tr>"
            
            return f"<h3>{title}</h3><table><thead><tr><th onclick='sortTable(this,0)'>तारीख ▲▼</th><th onclick='sortTable(this,1)'>क्लोज प्राईस ▲▼</th><th onclick='sortTable(this,2)'>बदल % ▲▼</th></tr></thead><tbody>{rows}{live_html}</tbody></table>"
    except: return ""

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
                
                rows += f"<tr><td>{p_row['Date']} ते {c_row['Date']}</td><td data-val='{atm}'>{atm}</td><td>{p_row['Close']:.2f}➔{c_row['Close']:.2f}</td><td style='color: {'#28a745' if ce_p>0 else '#dc3545'}; font-weight: bold;' data-val='{ce_p}'>{ce_p:+.2f}%</td><td style='color: {'#28a745' if pe_p>0 else '#dc3545'}; font-weight: bold;' data-val='{pe_p}'>{pe_p:+.2f}%</td></tr>"
            
            return f"<h3>Nifty 50 Options Backtest (ATM CE / PE)</h3><table><thead><tr><th onclick='sortTable(this,0)'>कालावधी ▲▼</th><th onclick='sortTable(this,1)'>ATM स्ट्राईक ▲▼</th><th>स्पॉट प्रवास</th><th onclick='sortTable(this,3)'>Call % बदल ▲▼</th><th onclick='sortTable(this,4)'>Put % बदल ▲▼</th></tr></thead><tbody>{rows}</tbody></table>"
    except: return ""

nifty_html = get_index_weekly_html("NSE:NIFTY50-INDEX", 1, "Nifty 50 Spot Weekly Report (Tuesday Expiry)")
sensex_html = get_index_weekly_html("BSE:SENSEX-INDEX", 3, "BSE Sensex Spot Weekly Report (Thursday Expiry)")
options_html = get_options_backtest_html()

full_template = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Live Options & Expiry Dashboard</title>
<style>
body {{ font-family: -apple-system, sans-serif; background-color: #f4f6f9; padding: 20px; }}
.container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
h2, h3 {{ text-align: center; color: #0056b3; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 30px; }}
th, td {{ padding: 12px 15px; border: 1px solid #dee2e6; text-align: center; }}
th {{ background-color: #007bff; color: white; cursor: pointer; }}
tr:nth-child(even) {{ background-color: #f8f9fa; }}
</style></head><body><div class="container"><h2>📊 LIVE OPTIONS & EXPIRES ALL-IN-ONE DASHBOARD</h2>{nifty_html}{sensex_html}{options_html}</div>
<script>
function sortTable(thEl, colIndex) {{
    const table = thEl.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    thEl.asc = !thEl.asc;
    rows.sort((rA, rB) => {{
        let vA = rA.querySelectorAll('td')[colIndex].getAttribute('data-val') || rA.querySelectorAll('td')[colIndex].innerText;
        let vB = rB.querySelectorAll('td')[colIndex].getAttribute('data-val') || rB.querySelectorAll('td')[colIndex].innerText;
        return (isNaN(vA) || isNaN(vB)) ? vA.localeCompare(vB) : parseFloat(vA) - parseFloat(vB);
    }});
    if (!thEl.asc) rows.reverse();
    rows.forEach(r => tbody.appendChild(r));
}}
</script></body></html>"""

# गिटहब पेजेससाठी 'docs' फोल्डर बनवून त्यात index.html सेव्ह करणे
os.makedirs("docs", exist_on_drop=True)
with open("docs/index.html", "w", encoding="utf-8") as f: 
    f.write(full_template)
print("index.html successfully created inside docs folder!")
