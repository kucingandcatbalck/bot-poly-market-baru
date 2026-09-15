import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Konfigurasi Halaman & Tema Mode Malam Institusional (ST-Fin Multi-Coin Style)
st.set_page_config(
    page_title="ST-Fin Multi-Coin Scalping Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Tampilan Dark Mode Pro
st.markdown("""
    <style>
    .main {
        background-color: #0b0e14;
        color: #f0f6fc;
    }
    .sidebar .sidebar-content {
        background-color: #111622;
    }
    div.stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    div.stMetric label {
        color: #8b949e !important;
    }
    .agent-log {
        background-color: #161b22;
        border-left: 4px solid #00FF7F;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        margin-bottom: 6px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='color: #00FF7F;'>⚡ ST-FIN MULTI-COIN SCALPING TERMINAL</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e;'>Autonomous Parallel Multi-Agent Execution | Multi-Position Meme & New-Coin Scalper</p>", unsafe_allow_html=True)
st.markdown("---")

# Inisialisasi Exchange Publik Bybit
@st.cache_resource
def init_exchange():
    return ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})

exchange = init_exchange()

# --- SIDEBAR: PANEL INFORMASI ARSITEKTUR ---
st.sidebar.header("📐 Multi-Coin Scalp Specs")
st.sidebar.markdown("**Framework:** Observation → Measurement → Logic Slot")
st.sidebar.markdown("**Mode:** Parallel Multi-Position Scalping")
st.sidebar.markdown("**Max Concurrent Trades:** Up to 4 Active Positions")
st.sidebar.markdown("---")
st.sidebar.info("💡 AI membagi modal secara paralel ke beberapa koin potensial yang terdeteksi secara otonom.")

# Inisialisasi State Sesi (Session State) untuk Multi-Posisi
if 'active_positions' not in st.session_state:
    st.session_state['active_positions'] = {} # Format: { 'PEPE/USDT': {entry, target, sl, tp_pct, sl_pct} }

if 'trade_history' not in st.session_state:
    st.session_state['trade_history'] = []

if 'virtual_balance' not in st.session_state:
    st.session_state['virtual_balance'] = 100.0

if 'initial_balance' not in st.session_state:
    st.session_state['initial_balance'] = 100.0

if 'total_wins' not in st.session_state:
    st.session_state['total_wins'] = 0

if 'total_losses' not in st.session_state:
    st.session_state['total_losses'] = 0

if 'agent_logs' not in st.session_state:
    st.session_state['agent_logs'] = [
        "ST-Fin Scalping Engine Initialized. Parallel Multi-Position Pipeline Active."
    ]

def log_agent(agent_name, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{agent_name}] {message}"
    st.session_state['agent_logs'].insert(0, log_entry)
    if len(st.session_state['agent_logs']) > 8:
        st.session_state['agent_logs'].pop()

# --- STATUS METRIK UTAMA ---
total_pnl_dollar = st.session_state['virtual_balance'] - st.session_state['initial_balance']
total_pnl_persen = (total_pnl_dollar / st.session_state['initial_balance']) * 100
total_trades = st.session_state['total_wins'] + st.session_state['total_losses']
win_rate = (st.session_state['total_wins'] / total_trades * 100) if total_trades > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Scalping Status", "🟢 Parallel Live", "Active")
col2.metric("Total Saldo", f"${st.session_state['virtual_balance']:.2f}", f"{total_pnl_persen:+.2f}%")
col3.metric("Win Rate", f"{win_rate:.1f}%", f"{st.session_state['total_wins']}W / {st.session_state['total_losses']}L")
col4.metric("Posisi Aktif", f"{len(st.session_state['active_positions'])} Koin", "Parallel Pool")
col5.metric("PnL Bersih", f"${total_pnl_dollar:+.2f}", "All-Time")

st.markdown("---")

# Fungsi ambil data candle 1m yang efisien
def fetch_candles_1m(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=40)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        return None

# --- AGENT 1: MARKET SCOUT (MENCARI BEBERAPA KANDIDAT SEKALIGUS) ---
def agent_market_scout(existing_symbols):
    try:
        tickers = exchange.fetch_tickers()
        kandidat = []
        for symbol, ticker in tickers.items():
            if '/USDT' in symbol and symbol not in existing_symbols:
                is_mainstream = any(coin in symbol for coin in ['BTC', 'ETH', 'SOL', 'XRP', 'USDC'])
                if not is_mainstream and ticker.get('percentage') is not None and ticker.get('last') and ticker.get('quoteVolume'):
                    change = ticker['percentage']
                    vol = ticker['quoteVolume']
                    # Saring meme coin & koin baru yang sedang koreksi sehat (-2% s.d -25%)
                    if -25.0 <= change <= -2.0 and vol > 15000:
                        kandidat.append({
                            'symbol': symbol,
                            'change': change,
                            'price': ticker['last']
                        })
        if kandidat:
            # Urutkan dari penurunan terdalam dan ambil beberapa terbaik
            kandidat = sorted(kandidat, key=lambda x: x['change'])
            return kandidat[:3] # Ambil hingga 3 kandidat teratas sekaligus
    except:
        pass
    return []

# --- AGENT 2: QUANT STRATEGIST (KALKULASI DINAMIS TP/SL) ---
def agent_quant_strategist(target_coin):
    price = target_coin['price']
    drop_magnitude = abs(target_coin['change'])
    
    dynamic_tp_pct = round(max(2.0, drop_magnitude * 0.35), 2)
    dynamic_sl_pct = round(max(1.5, drop_magnitude * 0.20), 2)
    
    t_price = price * (1 + (dynamic_tp_pct / 100))
    s_price = price * (1 - (dynamic_sl_pct / 100))
    
    return {
        'symbol': target_coin['symbol'],
        'entry': price,
        'target': t_price,
        'sl': s_price,
        'tp_pct': dynamic_tp_pct,
        'sl_pct': dynamic_sl_pct
    }

# --- AREA UTAMA: MULTI-POSITION STREAM & GRID MONITOR (RUN EVERY 1 DETIK) ---
@st.fragment(run_every=1)
def render_multicoin_terminal():
    # Maksimal 4 posisi aktif secara bersamaan agar modal $100 terdistribusi rapi ($10 per trade)
    MAX_POSITIONS = 4
    ALLOCATION_PER_TRADE = 10.0
    
    # FASE 1: Jika slot masih ada, Agent 1 & 2 mencari dan membuka posisi baru secara paralel
    if len(st.session_state['active_positions']) < MAX_POSITIONS:
        existing_syms = list(st.session_state['active_positions'].keys())
        new_targets = agent_market_scout(existing_syms)
        
        slots_available = MAX_POSITIONS - len(st.session_state['active_positions'])
        for target in new_targets[:slots_available]:
            # Pastikan saldo cukup
            if st.session_state['virtual_balance'] >= ALLOCATION_PER_TRADE:
                strat = agent_quant_strategist(target)
                sym = strat['symbol']
                
                st.session_state['active_positions'][sym] = strat
                log_agent("Agent 1 & 2", f"Buka posisi scalping paralel baru di {sym} | Entry: ${strat['entry']} | TP: +{strat['tp_pct']}%")
                
                st.session_state['trade_history'].insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"), 
                    "symbol": sym, 
                    "type": "BUY (Scalp)", 
                    "price": f"${strat['entry']}", 
                    "status": "Active"
                })
                st.rerun()

    # Layout Dashboard: Kolom Kiri untuk Grid Chart Multi-Posisi, Kolom Kanan untuk Riwayat & Log
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.subheader("📈 Active Scalping Positions Grid (Real-Time 1s)")
        
        active_pos_dict = st.session_state['active_positions']
        
        if not active_pos_dict:
            st.info("🤖 AI sedang memindai seluruh pasar untuk mengisi portofolio scalping paralel...")
        else:
            # Tampilkan posisi aktif dalam bentuk grid interaktif
            symbols = list(active_pos_dict.keys())
            
            # Buat iterasi grid 2 kolom
            for i in range(0, len(symbols), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(symbols):
                        sym = symbols[i + j]
                        posisi = active_pos_dict[sym]
                        
                        with cols[j]:
                            df = fetch_candles_1m(sym)
                            if df is not None and not df.empty:
                                last_price = df['close'].iloc[-1]
                                pnl_persen = ((last_price - posisi['entry']) / posisi['entry']) * 100
                                pnl_dollar = ALLOCATION_PER_TRADE * (pnl_persen / 100)
                                
                                # Mini Line Chart per Koin
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=df['timestamp'],
                                    y=df['close'],
                                    mode='lines',
                                    name=sym,
                                    line=dict(color='#00FF7F' if pnl_dollar >= 0 else '#ef5350', width=2)
                                ))
                                fig.add_hline(y=posisi['target'], line_dash="dash", line_color="#26a69a")
                                fig.add_hline(y=posisi['sl'], line_dash="dash", line_color="#ef5350")
                                
                                fig.update_layout(
                                    title=f"<b>{sym}</b> | PnL: {pnl_persen:+.2f}%",
                                    template="plotly_dark",
                                    paper_bgcolor="#161b22",
                                    plot_bgcolor="#161b22",
                                    height=250,
                                    margin=dict(l=10, r=10, t=30, b=10)
                                )
                                st.plotly_chart(fig, width='stretch', key=f"grid_chart_{sym.replace('/', '_')}")
                                
                                color_style = "color: #26a69a;" if pnl_dollar >= 0 else "color: #ef5350;"
                                st.markdown(f"""
                                    <div style="background-color: #111622; padding: 8px; border-radius: 6px; font-size: 13px; display: flex; justify-content: space-between;">
                                        <span>Entry: ${posisi['entry']}</span>
                                        <span>Live: ${last_price}</span>
                                        <b style="{color_style}">{pnl_dollar:+.2f} USDT</b>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # FASE 3: Agent 3 (Guardian) mengevaluasi TP/SL secara otonom per koin
                                if last_price >= posisi['target']:
                                    cuan = ALLOCATION_PER_TRADE * (posisi['tp_pct'] / 100)
                                    st.session_state['virtual_balance'] += cuan
                                    st.session_state['total_wins'] += 1
                                    log_agent("Agent 3 (Guardian)", f"🎯 TAKE PROFIT tercapai di {sym}! Cuan +${cuan:.2f}")
                                    st.session_state['trade_history'].insert(0, {
                                        "time": datetime.now().strftime("%H:%M:%S"), 
                                        "symbol": sym, 
                                        "type": "TAKE PROFIT", 
                                        "price": f"${last_price}", 
                                        "status": f"+${cuan:.2f} (Win)"
                                    })
                                    del st.session_state['active_positions'][sym]
                                    st.rerun()
                                    
                                elif last_price <= posisi['sl']:
                                    rugi = ALLOCATION_PER_TRADE * (posisi['sl_pct'] / 100)
                                    st.session_state['virtual_balance'] -= rugi
                                    st.session_state['total_losses'] += 1
                                    log_agent("Agent 3 (Guardian)", f"🛡️ STOP-LOSS terpicu di {sym}! Rugi -${rugi:.2f}")
                                    st.session_state['trade_history'].insert(0, {
                                        "time": datetime.now().strftime("%H:%M:%S"), 
                                        "symbol": sym, 
                                        "type": "STOP LOSS", 
                                        "price": f"${last_price}", 
                                        "status": f"-${rugi:.2f} (Loss)"
                                    })
                                    del st.session_state['active_positions'][sym]
                                    st.rerun()

        # --- MULTI-AGENT ACTIVITY STREAM ---
        st.markdown("---")
        st.subheader("🧠 Multi-Agent Scalping Activity Log")
        for log in st.session_state['agent_logs'][:4]:
            st.markdown(f'<div class="agent-log">{log}</div>', unsafe_allow_html=True)

    with right_col:
        st.subheader("📋 Live Riwayat Transaksi")
        st.markdown("Rekam jejak eksekusi multi-posisi paralel.")
        
        if st.session_state['trade_history']:
            history_df = pd.DataFrame(st.session_state['trade_history'])
            st.dataframe(history_df, width='stretch', hide_index=True)
        else:
            st.info("Belum ada transaksi terekam.")
            
        st.markdown("---")
        st.subheader("🤖 Scalping Architecture")
        st.info(
            "• **Market Scout:** Menyisir seluruh token baru untuk mencari beberapa peluang diskon secara paralel[cite: 1].\n\n"
            "• **Quant Strategist:** Menghitung parameter TP/SL adaptif untuk setiap koin[cite: 1].\n\n"
            "• **Guardian Agent:** Memantau semua chart secara serentak tiap detik dan mengeksekusi profit/loss otonom."
        )

render_multicoin_terminal()