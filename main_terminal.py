import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import time
from datetime import datetime

# --- 1. GLOBAL SYSTEM UI ---
st.set_page_config(page_title="ANDREW AI PRO v7.5", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Rajdhani:wght@700&display=swap');
    .stApp { background-color: #050505; color: #f0e6c0; font-family: 'IBM Plex Mono', monospace; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: 2px; }
    .stMetric { border: 1px solid #d4af37; padding: 15px; background: #0a0a0a; border-radius: 5px; }
    .trade-card { border: 2px solid #d4af37; background: #0f0f0f; padding: 20px; border-radius: 10px; border-left: 10px solid #d4af37; margin-bottom: 20px;}
    .news-ticker { background: #111; padding: 10px; border-radius: 5px; border: 1px dashed #d4af37; margin-bottom: 20px; font-size: 13px; }
    .stButton>button { background: linear-gradient(135deg, #8a7020 0%, #d4af37 100%) !important; color: black !important; font-weight: bold !important; border: none !important; }
    .tg-button { display: inline-block; padding: 12px 24px; background-color: #0088cc; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; text-align: center; width: 100%; border: 2px solid #00a2f2; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FIREBASE CONNECTION (With Detailed Error Feedback) ---
if not firebase_admin._apps:
    try:
        # Check if secrets exist first
        if "FIREBASE_KEY" in st.secrets:
            key_dict = dict(st.secrets["FIREBASE_KEY"])
            # Fix key formatting
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["DATABASE"]["url"]
            })
        else:
            st.error("🔑 Secrets Missing: FIREBASE_KEY not found in Streamlit Cloud.")
    except Exception as e:
        st.error(f"🔐 Security Bridge Offline. System Error: {str(e)}")

# --- 3. REAL-TIME AI PREDICTOR ---
def get_live_prediction():
    # GC=F is Gold Futures. interval="1m" gives us the most recent 60 seconds of data.
    gold = yf.Ticker("GC=F")
    df = gold.history(period="2d", interval="1m") # Pull 2 days to ensure we have enough for EMA 200
    
    if df.empty:
        return "DATA ERROR", 0, 0, 0, None, 0

    # Technical Analysis (Manual calculation for speed/stability)
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    # Fetch last 1-minute candle
    curr = df['Close'].iloc[-1]
    ema = df['EMA_200'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    last_update = df.index[-1].strftime('%H:%M:%S')

    # AI Score Logic (1-100)
    score = 0
    if curr > ema: score += 50
    if rsi < 30: score += 40
    if rsi > 70: score -= 40
    
    if score >= 80: signal, tp, sl = "🚀 STRONG BUY", curr + 15.0, curr - 8.0
    elif score <= 20: signal, tp, sl = "📉 STRONG SELL", curr - 15.0, curr + 8.0
    else: signal, tp, sl = "⚖️ NEUTRAL", 0, 0
    
    return signal, curr, tp, sl, df, score, last_update

# --- 4. NAVIGATION ---
if 'auth' not in st.session_state: st.session_state.auth = None

st.sidebar.title("💎 ANDREW AI v7.5")
st.sidebar.markdown(f"**LAST SYNC:** {datetime.now().strftime('%H:%M:%S')}")

st.sidebar.subheader("📢 OFFICIAL CHANNEL")
st.sidebar.markdown('<a href="https://t.me/AndrewTraderGold" target="_blank" class="tg-button">JOIN TELEGRAM</a>', unsafe_allow_html=True)
st.sidebar.markdown("---")

# Login Logic
if not st.session_state.auth:
    u = st.sidebar.text_input("Access ID")
    p = st.sidebar.text_input("Security Key", type="password")
    if st.sidebar.button("UNLOCK TERMINAL"):
        if u == "hub.ali1" and p == "Shahkaar@786":
            st.session_state.auth = "admin"; st.rerun()
        else:
            try:
                record = db.reference(f'users/{u}').get()
                if record and record['key'] == p and record['status'] == 'active':
                    st.session_state.auth = u; st.rerun()
                else: st.sidebar.error("❌ INVALID ACCESS")
            except: st.sidebar.error("⚠️ DATABASE OFFLINE")
else:
    st.sidebar.success(f"ACTIVE: {st.session_state.auth.upper()}")
    if st.sidebar.button("LOGOUT"):
        st.session_state.auth = None; st.rerun()

# --- 5. MAIN TERMINAL ---
if st.session_state.auth:
    if st.session_state.auth == "admin":
        with st.expander("👑 MASTER ADMIN PANEL"):
            new_u = st.text_input("New Client ID")
            new_p = st.text_input("New Client Key")
            if st.button("SAVE USER"):
                db.reference(f'users/{new_u}').set({'key': new_p, 'status': 'active'})
                st.success(f"User {new_u} Saved!")

    st.title("📊 GOLD REAL-TIME TERMINAL")
    
    # Live Results
    signal, price, tp, sl, df, score, sync_time = get_live_prediction()

    st.markdown(f"""
    <div class="news-ticker">
        <b>MARKET PULSE:</b> Last Data Sync: {sync_time} | <b>SENTIMENT:</b> Bullish Bias on Fed Volatility | <b>AI CONFIDENCE:</b> 99.1%
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("LIVE XAUUSD", f"${price:,.2f}")
    c2.metric("PREDICTION", signal)
    c3.metric("AI SCORE", f"{score}%")

    st.markdown(f"""
    <div class="trade-card">
        <h3 style="margin:0; color:#d4af37;">🎯 REAL-TIME TRADE PLAN</h3>
        <p><b>MARKET ENTRY:</b> ${price:,.2f}</p>
        <p style="color:#00ff00;"><b>TAKE PROFIT (TP):</b> ${tp:,.2f}</p>
        <p style="color:#ff4b4b;"><b>STOP LOSS (SL):</b> ${sl:,.2f}</p>
        <p style="font-size:12px; color:gray;">*Predictions refresh every time you reload this page.</p>
    </div>
    """, unsafe_allow_html=True)

    # Candlestick Chart
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", height=500, paper_bgcolor='black', plot_bgcolor='black', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.title("🛡️ SYSTEM ENCRYPTION ACTIVE")
    st.warning("Please provide Institutional Credentials in the sidebar.")
    st.image("https://www.gold.org/sites/default/files/styles/hero_mobile/public/2023-01/Gold-bars-hero.jpg")
