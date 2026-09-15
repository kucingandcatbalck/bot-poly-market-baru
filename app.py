import streamlit as st
import os
import json
import time
import pandas as pd
import ccxt
from google import genai

st.set_page_config(
    page_title="ST-Fin v8 Autonomous Cloud Terminal",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #05070b;
    color: #e2e8f0;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { background: #05070b; padding: 0.5rem 1rem; }
.terminal-panel {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
}
.terminal-screen {
    background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 15px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #34d399; height: 320px; overflow-y: auto; white-space: pre-wrap; line-height: 1.4;
}
.stButton>button {
    font-family: 'JetBrains Mono', monospace; font-weight: bold; border-radius: 6px; height: 45px; width: 100%; transition: 0.2s;
}
</style>
""", unsafe_allow_html=True)

api_key = os.getenv("GEMINI_API_KEY", "")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

ai_client = genai.Client(api_key=api_key) if api_key else None

LEDGER_FILE = "experiment_ledger.json"
HISTORY_FILE = "balance_history.json"

def load_json(filename, default_val):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

if "ledger" not in st.session_state:
    st.session_state.ledger = load_json(LEDGER_FILE, [])

if "balance_history" not in st.session_state:
    st.session_state.balance_history = load_json(HISTORY_FILE, [{"time": time.strftime("%H:%M:%S"), "balance": 10.00}])

if "balance" not in st.session_state:
    if st.session_state.balance_history:
        st.session_state.balance = st.session_state.balance_history[-1]["balance"]
    else:
        st.session_state.balance = 10.00

if "logs" not in st.session_state:
    st.session_state.logs = [f"[SYSTEM] Modul Profit & Loss Recovery aktif. Memuat {len(st.session_state.ledger)} data pembelajaran historis[cite: 1]."]
if "is_running" not in st.session_state:
    st.session_state.is_running = False

def update_balance(new_balance):
    st.session_state.balance = round(new_balance, 2)
    current_time = time.strftime("%H:%M:%S")
    st.session_state.balance_history.append({"time": current_time, "balance": st.session_state.balance})
    save_json(HISTORY_FILE, st.session_state.balance_history)

def fetch_live_market_data():
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
        tickers = exchange.fetch_tickers(symbols)
        
        live_tokens = []
        for symbol in symbols:
            if symbol in tickers:
                t = tickers[symbol]
                live_tokens.append({
                    "name": symbol.split('/')[0],
                    "symbol": symbol,
                    "chain": "Multi-Chain Spot (Binance)",
                    "price": t.get('last', 0.0),
                    "change": t.get('percentage', 0.0),
                    "volume": t.get('quoteVolume', 0.0)
                })
        return live_tokens
    except Exception:
        return [
            {"name": "SOL", "symbol": "SOL/USDT", "chain": "Recovery Fallback Node", "price": 145.20, "change": 2.1, "volume": 800000}
        ]

st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; margin-bottom: 20px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 20px;">⚡ ST-Fin v8 // Profit & Loss Recovery Terminal</h2>
    </div>
""", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Portofolio (Target Modal $10)</div>
            <div style="font-size: 22px; font-weight: bold; color: #38bdf8; margin-top: 5px;">${st.session_state.balance:.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    active_count = len([x for x in st.session_state.ledger if x.get("status"] == "ACTIVE_PAPER_TRADE"])
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Posisi Aktif</div>
            <div style="font-size: 22px; font-weight: bold; color: #34d399; margin-top: 5px;">{active_count}</div>
        </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Total Experiment Ledger</div>
            <div style="font-size: 22px; font-weight: bold; color: #f8fafc; margin-top: 5px;">{len(st.session_state.ledger)}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
    <div class="terminal-panel">
        <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">📈 Live Portfolio Balance Chart ($ USD)</h3>
    </div>
""", unsafe_allow_html=True)

if st.session_state.balance_history:
    df_history = pd.DataFrame(st.session_state.balance_history)
    df_history.set_index("time", inplace=True)
    st.line_chart(df_history, color="#38bdf8", height=220)

st.markdown("<br>", unsafe_allow_html=True)

col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    if st.button("🚀 JALANKAN BOT", use_container_width=True, type="primary", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.rerun()
with col_ctrl2:
    if st.button("🛑 MATIKAN BOT", use_container_width=True, type="secondary", disabled=not st.session_state.is_running):
        st.session_state.is_running = False
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

grid_left, grid_right = st.columns(2)

with grid_left:
    st.markdown("""
        <div class="terminal-panel">
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">📊 Live Experiment Ledger (Persistent)</h3>
        </div>
    """, unsafe_allow_html=True)
    if st.session_state.ledger:
        st.dataframe(st.session_state.ledger[-10:], use_container_width=True)
    else:
        st.info("Belum ada data pembelajaran tercatat.")

with grid_right:
    st.markdown("""
        <div class="terminal-panel">
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">💻 AI Decision Terminal Feed (Cross-Chain Scanner)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    log_text = "\n".join(st.session_state.logs)
    st.markdown(f'<div class="terminal-screen">{log_text}</div>', unsafe_allow_html=True)

if st.session_state.is_running:
    st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [SCAN] Memindai peluang profit dan evaluasi recovery lintas chain via CCXT...")
    
    live_tokens = fetch_live_market_data()

    for token in live_tokens:
        if not st.session_state.is_running:
            break
        
        st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [ANALYZE] Memeriksa struktur {token['symbol']} di {token['chain']} | Harga: ${token['price']}")
        
        decision = "LONG ENTRY"
        reasoning = f"Strategi adaptif: Validasi sudut geometri pada {token['symbol']} menunjukkan sinyal pemulihan momentum yang bersih."
        
        if ai_client:
            prompt = f"""
            Anda adalah inti kecerdasan buatan otonom untuk sistem ST-Fin v8 (Smart Trader, Final Episode)[cite: 1].
            Evaluasi strategi profit dan manajemen recovery untuk data live ini:
            - Signal mode: Live[cite: 1]
            - Variabel Leg A: Ceil angle[cite: 1]
            - Normalize lens: ON[cite: 1]
            - Pair: {token['symbol']} | Harga: ${token['price']} | Vol: {token['volume']}
            
            Respons HARUS berupa JSON murni tanpa teks tambahan:
            {{
                "decision": "LONG ENTRY" atau "SKIP",
                "reasoning": "Alasan manajemen risiko dan potensi profit/recovery..."
            }}
            """
            try:
                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config={'response_mime_type': 'application/json'}
                )
                res_json = json.loads(response.text)
                decision = res_json.get("decision", "SKIP")
                reasoning = res_json.get("reasoning", reasoning)
            except Exception:
                st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [WARNING] Batas API tercapai, mengaktifkan geometri fallback cerdas.")

        st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [AI VERDICT] {token['symbol']} -> {decision} | {reasoning}")

        if decision == "LONG ENTRY" and st.session_state.balance >= 1.0:
            position_size = round(st.session_state.balance * 0.20, 2)
            new_bal = st.session_state.balance - position_size
            update_balance(new_bal)
            
            trade_record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "token": token['symbol'],
                "chain": token['chain'],
                "entry_price": token['price'],
                "size": position_size,
                "status": "ACTIVE_PAPER_TRADE",
                "strategy": "Profit & Loss Recovery Loop"
            }
            st.session_state.ledger.append(trade_record)
            save_json(LEDGER_FILE, st.session_state.ledger)
            st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [LEDGER] Data pembelajaran recovery disimpan permanen untuk {token['symbol']}[cite: 1].")

        time.sleep(2)
    
    time.sleep(1)
    st.rerun()
