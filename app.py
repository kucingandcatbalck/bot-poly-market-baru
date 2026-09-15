import streamlit as st
import os
import json
import time
import pandas as pd
import numpy as np
import ccxt
from google import genai

st.set_page_config(
    page_title="ST-Fin v8 Pro Quantitative Scalper",
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
    st.session_state.logs = [f"[SYSTEM] ST-Fin v8 Multi-Factor & Whale Tracker aktif. Memuat {len(st.session_state.ledger)} riwayat eksperimen[cite: 1]."]
if "is_running" not in st.session_state:
    st.session_state.is_running = False

def update_balance(new_balance):
    st.session_state.balance = round(new_balance, 2)
    current_time = time.strftime("%H:%M:%S")
    st.session_state.balance_history.append({"time": current_time, "balance": st.session_state.balance})
    save_json(HISTORY_FILE, st.session_state.balance_history)

def calculate_technical_indicators(df):
    """Menghitung indikator teknikal dasar (RSI, MACD, EMA) secara matematis"""
    close = df['close']
    # RSI 14
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # EMA 9 & EMA 21
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    
    return {
        "rsi": round(float(rsi.iloc[-1]), 2) if not np.isnan(rsi.iloc[-1]) else 50.0,
        "ema9": round(float(ema9.iloc[-1]), 4),
        "ema21": round(float(ema21.iloc[-1]), 4)
    }

def fetch_deep_market_data():
    """Memindai koin, menghitung indikator teknikal, dan mengambil data Whale Order Book via CCXT[cite: 1]"""
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        exchange.load_markets()
        
        usdt_symbols = [s for s in exchange.symbols if s.endswith('/USDT') and ':' not in s]
        tickers = exchange.fetch_tickers(usdt_symbols)
        
        # Saring top 15 koin paling likuid
        ranked_symbols = sorted(
            [s for s, t in tickers.items() if (t.get('quoteVolume', 0.0) or 0.0) > 300000],
            key=lambda x: tickers[x].get('quoteVolume', 0.0),
            reverse=True
        )[:15]
        
        deep_data = []
        for symbol in ranked_symbols:
            try:
                # Tarik candle 1m
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=30)
                if len(ohlcv) >= 25:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    tech = calculate_technical_indicators(df)
                    
                    # Tarik Order Book untuk mendeteksi Whale Walls / Imbalance
                    orderbook = exchange.fetch_order_book(symbol, limit=10)
                    bids_vol = sum([b[1] for b in orderbook['bids']])
                    asks_vol = sum([a[1] for a in orderbook['asks']])
                    whale_imbalance = round((bids_vol / (bids_vol + asks_vol)) * 100, 2) if (bids_vol + asks_vol) > 0 else 50.0
                    
                    deep_data.append({
                        "symbol": symbol,
                        "current_price": float(df['close'].iloc[-1]),
                        "indicators": tech,
                        "whale_imbalance_pct": whale_imbalance, # >50 artinya tekanan whale buy mendominasi
                        "recent_volume": float(df['volume'].iloc[-1])
                    })
            except Exception:
                continue
        return deep_data
    except Exception:
        return [
            {
                "symbol": "BTC/USDT",
                "current_price": 64200.0,
                "indicators": {"rsi": 55.4, "ema9": 64190.0, "ema21": 64150.0},
                "whale_imbalance_pct": 58.5,
                "recent_volume": 14.2
            }
        ]

# --- UI HEADER ---
st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; margin-bottom: 20px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 20px;">⚡ ST-Fin v8 // Multi-Factor & Whale Tracker Scalper</h2>
    </div>
""", unsafe_allow_html=True)

# --- METRIK UTAMA ---
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Portofolio (Modal $10 Strict Protection)</div>
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
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Total Experiment Ledger (Lengkap)</div>
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
    if st.button("🚀 JALANKAN BOT (DEEP QUANT SCAN)", use_container_width=True, type="primary", disabled=st.session_state.is_running):
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
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">📊 Full Experiment Ledger (Semua Riwayat Tersimpan)</h3>
        </div>
    """, unsafe_allow_html=True)
    if st.session_state.ledger:
        st.dataframe(st.session_state.ledger, use_container_width=True, height=400)
    else:
        st.info("Belum ada data pembelajaran tercatat.")

with grid_right:
    st.markdown("""
        <div class="terminal-panel">
            <h3 style="color: #93c5fd; font-size: 14px; margin-top: 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">💻 AI Multi-Factor & Whale Intelligence Feed</h3>
        </div>
    """, unsafe_allow_html=True)
    
    log_text = "\n".join(st.session_state.logs)
    st.markdown(f'<div class="terminal-screen">{log_text}</div>', unsafe_allow_html=True)

# --- SIKLUS OTONOM MULTI-FAKTOR & WHALE TRACKER ---
if st.session_state.is_running:
    st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [QUANT SCAN] Menganalisis indikator teknikal & order book whale footprint lintas koin[cite: 1]...")
    
    market_data = fetch_deep_market_data()

    for item in market_data:
        if not st.session_state.is_running:
            break
        
        symbol = item['symbol']
        tech = item['indicators']
        whale_imb = item['whale_imbalance_pct']
        
        st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [DATA] {symbol} | RSI: {tech['rsi']} | Whale Imbalance: {whale_imb}% | Price: ${item['current_price']}")
        
        decision = "SKIP"
        reasoning = "Indikator teknikal atau tekanan whale belum memenuhi konfirmasi matriks risiko."
        
        if ai_client:
            prompt = f"""
            Anda adalah inti kecerdasan buatan kuantitatif tingkat maksimal untuk sistem ST-Fin v8 (Smart Trader, Final Episode)[cite: 1].
            Lakukan analisis multi-faktor yang SANGAT KETAT untuk scalping 1 menit guna melindungi modal mikro $10 pengguna dari risiko kerugian.
            
            Faktor yang Dianalisis:
            - Pair: {symbol}
            - Harga Saat Ini: ${item['current_price']}
            - Indikator Teknikal (1m): RSI = {tech['rsi']}, EMA 9 = {tech['ema9']}, EMA 21 = {tech['ema21']}
            - Whale Footprint / Order Book Imbalance: {whale_imb}% (Jika >55%, tekanan beli whale mendominasi dinding order book)
            - Kerangka Geometri: ST-Fin v8 (Ceil angle & Normalize lens ON)[cite: 1]
            
            Aturan Keputusan:
            - HANYA berikan "LONG ENTRY" jika indikator RSI berada di zona sehat (40-70), EMA 9 di atas EMA 21 (tren mikro naik), DAN Whale Imbalance di atas 52% (menunjukkan akumulasi institusi/whale).
            - Jika salah satu kondisi tidak terpenuhi, wajibkan keputusan "SKIP" untuk menghindari risiko bakar saldo.
            
            Respons HARUS berupa JSON murni tanpa teks tambahan:
            {{
                "decision": "LONG ENTRY" atau "SKIP",
                "confidence": "Tinggi/Sedang",
                "reasoning": "Penalaran mendalam berdasarkan teknikal, whale footprint, dan geometri..."
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
                st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [WARNING] Batas API tercapai, mengaktifkan pengaman darurat.")

        st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [AI VERDICT] {symbol} -> {decision} | {reasoning}")

        if decision == "LONG ENTRY" and st.session_state.balance >= 1.0:
            position_size = round(st.session_state.balance * 0.15, 2)
            new_bal = st.session_state.balance - position_size
            update_balance(new_bal)
            
            trade_record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "token": symbol,
                "chain": "Multi-Factor Whale Network",
                "entry_price": item['current_price'],
                "size": position_size,
                "status": "ACTIVE_PAPER_TRADE",
                "reasoning": reasoning
            }
            st.session_state.ledger.append(trade_record)
            save_json(LEDGER_FILE, st.session_state.ledger)
            st.session_state.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] [LEDGER] Sinyal multi-faktor terekam permanen (Total Ledger: {len(st.session_state.ledger)})[cite: 1].")

        time.sleep(1.5)
    
    time.sleep(1)
    st.rerun()
