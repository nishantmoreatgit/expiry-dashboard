import datetime
import math
import pandas as pd
import os
from fyers_apiv3 import fyersModel

# १. तुमचे FYERS API क्रेडेंशियल्स आणि चालू अॅक्सेस टोकन टाका
client_id = "RAE54K69M5-100" 
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCcVNoekZUcDNjYm5NRGRuRUVhNU9XNEhHQXVPWHdKQjFzeENGMTNPcnZKaTNrY3NORW5VZEJPQS1pbHY0R0FUbUhTdld1YjRjMWlZbWcteUZzQThkblF3b0pfVUFiZUxzU2QwQ3BFT2hxM095T0RvVT0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIxM2NkNjIxY2ZkZGNlYWI4ZmFjYjRmM2YzMWE3OTczYTZiNmM4OWZlYTY3ZWQ2NmViM2U0OThhNSIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiRk4xMDY1IiwiYXBwVHlwZSI6MTAwLCJleHAiOjE3ODMyOTc4MDAsImlhdCI6MTc4MzI0MTkyNSwiaXNzIjoiYXBpLmZ5ZXJzLmluIiwibmJmIjoxNzgzMjQxOTI1LCJzdWIiOiJhY2Nlc3NfdG9rZW4ifQ.9M2UX7wCgOEcTYAHpF46fKR3O39LgwQN1wRXfnKnkCA"

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# मॅन्युअल नॉर्मल डिस्ट्रिब्युशन फंक्शन
def cdf_normal(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

# Black-Scholes Formula - CALL आणि PUT दोन्हीसाठी
def black_scholes_options(S, K, T, r, sigma):
    if T <= 0:
        return max(0.0, S - K), max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    call_price = S * cdf_normal(d1) - K * math.exp(-r * T) * cdf_normal(d2)
    put_price = K * math.exp(-r * T) * cdf_normal(-d2) - S * cdf_normal(-d1)
    
    return call_price, put_price

def generate_historical_option_dashboard_from_sep_2025():
    print("१. निफ्टी स्पॉटचा १ सप्टेंबर २०२५ पासूनचा संपूर्ण डेटा फेच करत आहे...")
    
    # थेट १ सप्टेंबर २०२५ पासूनची निश्चित स्टार्ट डेट सेट केली [NSE]
    start_date = datetime.date(2025, 9, 1) [NSE]
    end_date = datetime.date.today()
    
    spot_payload = {
        "symbol": "NSE:NIFTY50-INDEX",
        "resolution": "D",
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }
    
    try:
        response = fyers.history(data=spot_payload)
        if response and response.get('code') == 200:
            candles = response.get('candles', [])
            if not candles:
                print("[ALERT] कोणताही डेटा सापडला नाही.")
                return
                
            df = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='s').dt.date
            df['Day of Week'] = pd.to_datetime(df['Date']).dt.weekday
            
            # केवळ मंगळवारचा एक्सपायरी डेटा फिल्टर करा
            weekly_df = df[df['Day of Week'] == 1].sort_values(by='Date').copy()
            
            table_rows_html = ""
            print("२. १ सप्टेंबर २०२५ पासूनचा सर्व ऑप्शन्स डेटा जनरेट होत आहे...")
            
            for i in range(1, len(weekly_df)):
                prev_row = weekly_df.iloc[i-1]
                curr_row = weekly_df.iloc[i]
                
                prev_date = prev_row['Date'].strftime("%Y-%m-%d")
                curr_date = curr_row['Date'].strftime("%Y-%m-%d")
                
                # ATM स्ट्राईक निश्चित करणे
                atm_strike = int(round(prev_row['Close'] / 50) * 50)
                
                r, sigma = 0.07, 0.12 # ७% व्याजदर, १२% Volatility
                
                # सुरवातीचे प्रीमियम्स (Entry Premiums)
                ce_entry, pe_entry = black_scholes_options(prev_row['Close'], atm_strike, 5/365, r, sigma)
                
                # अंतिम प्रीमियम्स एक्सपायरीला (Expiry Values)
                ce_expiry = max(0.0, curr_row['Close'] - atm_strike)
                pe_expiry = max(0.0, atm_strike - curr_row['Close'])
                
                # टक्केवारी बदल काढणे
                ce_pct = ((ce_expiry - ce_entry) / ce_entry) * 100 if ce_entry > 0 else 0.0
                pe_pct = ((pe_expiry - pe_entry) / pe_entry) * 100 if pe_entry > 0 else 0.0
                
                # रंगांचे स्टायलिंग सेट करणे
                ce_color = "color: #28a745; font-weight:bold;" if ce_pct > 0 else "color: #dc3545;"
                pe_color = "color: #28a745; font-weight:bold;" if pe_pct > 0 else "color: #dc3545;"
                
                table_rows_html += f"""
                <tr>
                    <td data-val="{curr_date}">{prev_date} ते {curr_date}</td>
                    <td data-val="{atm_strike}">{atm_strike}</td>
                    <td>{prev_row['Close']:.2f} ➔ {curr_row['Close']:.2f}</td>
                    <td>{ce_entry:.2f} ➔ {ce_expiry:.2f}</td>
                    <td data-val="{ce_pct}" style="{ce_color}">{ce_pct:+.2f}%</td>
                    <td>{pe_entry:.2f} ➔ {pe_expiry:.2f}</td>
                    <td data-val="{pe_pct}" style="{pe_color}">{pe_pct:+.2f}%</td>
                </tr>
                """
                
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="UTF-8">
            <title>Nifty Option Historical Dashboard</title>
            <style>
            body { font-family: -apple-system, sans-serif; background-color: #f4f6f9; padding: 30px; }
            .container { max-width: 1100px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            h2 { text-align: center; color: #0056b3; margin-bottom: 5px; }
            p.sub-title { text-align: center; color: #6c757d; margin-top: 0; margin-bottom: 25px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 12px 15px; border: 1px solid #dee2e6; text-align: center; }
            th { background-color: #007bff; color: white; cursor: pointer; user-select: none; }
            th:hover { background-color: #0056b3; }
            tr:nth-child(even) { background-color: #f8f9fa; }
            tr:hover { background-color: #f1f3f5; }
            </style>
            </head>
            <body>
            <div class="container">
            <h2>📊 NIFTY 50 ATM OPTIONS HISTORICAL REPORT (सप्टेंबर २०२५ पासून)</h2>
            <p class="sub-title">खालील कोणत्याही हेडिंगवर क्लिक करून डेटा चढत्या उतरत्या (▲▼) क्रमाने सॉर्ट करा</p>
            <table>
            <thead>
            <tr>
            <th onclick="sortTable(0)">कालावधी (Weekly Period) ▲▼</th>
            <th onclick="sortTable(1)">ATM स्ट्राईक प्राईस ▲▼</th>
            <th>निफ्टी SPOT मुव्हमेंट</th>
            <th>Call (CE) प्रीमियम प्रवास</th>
            <th onclick="sortTable(4)">Call % बदल ▲▼</th>
            <th>Put (PE) प्रीमियम प्रवास</th>
            <th onclick="sortTable(6)">Put % बदल ▲▼</th>
            </tr>
            </thead>
            <tbody id="tableBody">
            <!--ROWS_HERE-->
            </tbody>
            </table>
            </div>
            <script>
            let sortDirections = [true, true, true, true, true, true, true];
            function sortTable(colIndex) {
                const tableBody = document.getElementById("tableBody");
                const rows = Array.from(tableBody.querySelectorAll("tr"));
                const isAscending = sortDirections[colIndex];
                
                rows.sort((rowA, rowB) => {
                    const cellA = rowA.querySelectorAll("td")[colIndex];
                    const cellB = rowB.querySelectorAll("td")[colIndex];
                    let valA = cellA.getAttribute("data-val");
                    let valB = cellB.getAttribute("data-val");
                    
                    if (colIndex > 0) {
                        valA = parseFloat(valA) || 0;
                        valB = parseFloat(valB) || 0;
                    }
                    if (valA < valB) return isAscending ? -1 : 1;
                    if (valA > valB) return isAscending ? 1 : -1;
                    return 0;
                });
                rows.forEach(row => tableBody.appendChild(row));
                sortDirections[colIndex] = !isAscending;
            }
            </script>
            </body>
            </html>
            """.replace("<!--ROWS_HERE-->", table_rows_html)
            
            # फाईलचे नाव बदलले जेणेकरून ओळखणे सोपे होईल
            output_file = 'index.html'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            print(f"३. ऐतिहासिक रिपोर्ट यशस्वीरीत्या '{output_file}' मध्ये सेव्ह झाला आहे!")
            
        else:
            print("[ERROR] निफ्टी डेटा मिळाला नाही. कोड:", response.get('code'))
    except Exception as e:
        print(f"त्रुटी: {e}")

# --- कोड रन करा ---
generate_historical_option_dashboard_from_sep_2025()
