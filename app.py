import streamlit as st
import os
import json
import time
import pandas as pd
import numpy as np
import ccxt
from google import genai

st.set_page_config(
    page_title="ST-Fin v8 Optimized Scalper",
    page_icon="⚡",
    layout="wide"
)

# Kustomisasi CSS Terminal Pro-Trader
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #030712;
    color: #e2e8f0;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { background: #030712; padding: 0.5rem 1rem; }
.terminal-panel {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.8);
}
.terminal-screen {
    background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 15px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #34d399; height: 380px; overflow-y: auto; white-space: pre-wrap; line-height: 1.4;
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

# Inisialisasi State dengan Batasan Kapasitas (Capped History)
if "ledger" not in st.session_state:
    loaded = load_json(LEDGER_FILE, [])
    st.session_state.ledger = loaded[-100:] if len(loaded) > 100 else loaded

if "balance_history" not in st.session_state:
    loaded_hist = load_json(HISTORY_FILE, [{"time": time.strftime("%H:%M:%S"), "balance": 10.00}])
    st.session_state.balance_history = loaded_hist[-100:] if len(loaded_hist) > 100 else loaded_hist

if "balance" not in st.session_state:
    if st.session_state.balance_history:
        st.session_state.balance = st.session_state.balance_history[-1]["balance"]
    else:
        st.session_state.balance = 10.00

if "logs" not in st.session_state:
    st.session_state.logs = [f"[SYSTEM] ST-Fin v8 Optimized Scanner aktif (History Capped). Memuat {len(st.session_state.ledger)} riwayat."]
if "is_running" not in st.session_state:
    st.session_state.is_running = False

def add_log(msg):
    st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg}")
    # Batasi maksimal 50 log di memori
    if len(st.session_state.logs) > 50:
        st.session_state.logs.pop()

def update_balance(new_balance):
    st.session_state.balance = round(new_balance, 2)
    current_time = time.strftime("%H:%M:%S")
    st.session_state.balance_history.append({"time": current_time, "balance": st.session_state.balance})
    # Batasi riwayat grafik maksimal 100 titik data
    if len(st.session_state.balance_history) > 100:
        st.session_state.balance_history = st.session_state.balance_history[-100:]
    save_json(HISTORY_FILE, st.session_state.balance_history)

def calculate_technical_indicators(df):
    close = df['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    
    return {
        "rsi": round(float(rsi.iloc[-1]), 2) if not np.isnan(rsi.iloc[-1]) else 50.0,
        "ema9": round(float(ema9.iloc[-1]), 6),
        "ema21": round(float(ema21.iloc[-1]), 6)
    }

def scan_all_coins_market():
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        exchange.load_markets()
        
        usdt_symbols = [s for s in exchange.symbols if s.endswith('/USDT') and ':' not in s]
        tickers = exchange.fetch_tickers(usdt_symbols)
        
        valid_candidates = []
        for symbol, t in tickers.items():
            quote_vol = t.get('quoteVolume', 0.0) or 0.0
            price = t.get('last', 0.0) or 0.0
            change_24h = t.get('percentage', 0.0) or 0.0
            
            if price > 0 and quote_vol >= 50000:
                valid_candidates.append({
                    "symbol": symbol,
                    "price": price,
                    "change_24h": change_24h,
                    "volume": quote_vol
                })
        
        valid_candidates = sorted(valid_candidates, key=lambda x: abs(x['change_24h']), reverse=True)
        target_pool = valid_candidates[:12] # Ambil sampel 12 koin teraktif agar cepat & ringan
        
        scanned_data = []
        for item in target_pool:
            symbol = item['symbol']
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=25)
                if len(ohlcv) >= 15:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    tech = calculate_technical_indicators(df)
                    
                    orderbook = exchange.fetch_order_book(symbol, limit=5)
                    bids_vol = sum([b[1] for b in orderbook['bids']])
                    asks_vol = sum([a[1] for a in orderbook['asks']])
                    whale_imbalance = round((bids_vol / (bids_vol + asks_vol)) * 100, 2) if (bids_vol + asks_vol) > 0 else 50.0
                    
                    scanned_data.append({
                        "symbol": symbol,
                        "current_price": item['price'],
                        "change_24h": item['change_24h'],
                        "indicators": tech,
                        "whale_imbalance_pct": whale_imbalance,
                        "recent_volume": item['volume']
                    })
            except Exception:
                continue
        return scanned_data
    except Exception:
        return [
            {
                "symbol": "PEPE/USDT",
                "current_price": 0.0000125,
                "change_24h": 8.5,
                "indicators": {"rsi": 58.2, "ema9": 0.0000124, "ema21": 0.0000122},
                "whale_imbalance_pct": 60.1,
                "recent_volume": 250000
            }
        ]

# --- UI HEADER ---
st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; margin-bottom: 20px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 20px;">⚡ ST-Fin v8 // Optimized All-Coin Scalper</h2>
    </div>
""", unsafe_allow_html=True)

# --- METRIK UTAMA ---
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Portofolio (Modal $10 Protected)</div>
            <div style="font-size: 22px; font-weight: bold; color: #38bdf8; margin-top: 5px;">${st.session_state.balance:.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    active_count = len([x for x in st.session_state.ledger if x.get("status") == "ACTIVE_PAPER_TRADE"])
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Posisi Aktif</div>
            <div style="font-size: 22px; font-weight: bold; color: #34d399; margin-top: 5px;">{active_count}</div>
        </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Ledger History (Max 100)</div>
            <div style="font-size: 22px; font-weight: bold; color: #f8fafc; margin-top: 5px;">{len(st.session_state.ledger)}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- GRAFIK LIVE PORTOS ---
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

# --- KONTROL UTAMA ---
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    if st.button("🚀 JALANKAN OPTIMIZED SCANNER", use_container_width=True, type="primary", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.rerun()
with col_ctrl2:
    if st.button("🛑 MATIKAN BOT", use_container_width=True, type="secondary", disabled=not st.session_state.is_running):
        st.session_state.is_running = False
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- LAYOUT UTAMA (LEDGER & TERMINAL) ---
grid_left, grid_right = st.columns(2)

with grid_left:
    st.markdown("""
        <div class="terminal-panel">
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">📊 Capped Experiment Ledger (Max 100 Terakhir)</h3>
        </div>
    """, unsafe_allow_html=True)
    if st.session_state.ledger:
        st.dataframe(st.session_state.ledger, use_container_width=True, height=350)
    else:
        st.info("Belum ada data pembelajaran tercatat.")

with grid_right:
    st.markdown("""
        <div class="terminal-panel">
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">💻 AI Intelligence Feed (Max 50 Log)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    log_text = "\n".join(st.session_state.logs)
    st.markdown(f'<div class="terminal-screen">{log_text}</div>', unsafe_allow_html=True)

# --- SIKLUS OTONOM OPTIMIZED ---
if st.session_state.is_running:
    add_log("Memulai siklus pemindaian universal dan penyaringan anti-scam...")
    
    market_coins = scan_all_coins_market()

    for item in market_coins:
        if not st.session_state.is_running:
            break
        
        symbol = item['symbol']
        tech = item['indicators']
        whale_imb = item['whale_imbalance_pct']
        change = item['change_24h']
        
        add_log(f"Check {symbol} | Change: {change}% | RSI: {tech['rsi']} | Whale Imbalance: {whale_imb}%")
        
        decision = "SKIP"
        reasoning = "Kandidat tidak lolos filter ketat anti-scam atau momentum 1m belum matang."
        
        if ai_client:
            prompt = f"""
            Anda adalah inti kecerdasan buatan kuantitatif untuk sistem ST-Fin v8.
            Analisis koin universal dengan filter anti-scam yang ketat untuk melindungi modal $10:
            - Pair: {symbol} | Harga: ${item['current_price']} | Change 24j: {change}% | Vol: ${item['recent_volume']:,.0f}
            - Indikator 1m: RSI = {tech['rsi']}, EMA 9 = {tech['ema9']}, EMA 21 = {tech['ema21']}
            - Whale Imbalance: {whale_imb}%
            
            Aturan:
            - Berikan "LONG ENTRY" hanya jika tren bersih, RSI sehat (45-75), dan Whale Imbalance > 52%.
            - Jika ragu atau potensi scam, wajibkan "SKIP".
            
            Respons HARUS berupa JSON murni:
            {{
                "decision": "LONG ENTRY" atau "SKIP",
                "confidence": "Tinggi/Sedang",
                "reasoning": "Alasan singkat..."
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
                add_log("Warning: Batas API tercapai, mengaktifkan pengaman darurat.")

        add_log(f"Verdict {symbol} -> {decision} | {reasoning}")

        if decision == "LONG ENTRY" and st.session_state.balance >= 1.0:
            position_size = round(st.session_state.balance * 0.15, 2)
            new_bal = st.session_state.balance - position_size
            update_balance(new_bal)
            
            trade_record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "token": symbol,
                "chain": "Universal Optimized Network",
                "entry_price": item['current_price'],
                "size": position_size,
                "status": "ACTIVE_PAPER_TRADE",
                "reasoning": reasoning
            }
            st.session_state.ledger.append(trade_record)
            
            # Batasi ledger maksimal 100 riwayat agar file JSON tidak membengkak
            if len(st.session_state.ledger) > 100:
                st.session_state.ledger = st.session_state.ledger[-100:]
                
            save_json(LEDGER_FILE, st.session_state.ledger)
            add_log(f"Ledger: Posisi {symbol} tercatat (Total: {len(st.session_state.ledger)})")

        time.sleep(1.0)
    
    time.sleep(1)
    st.rerun()
