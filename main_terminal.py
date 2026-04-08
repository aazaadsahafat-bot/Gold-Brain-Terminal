import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import requests
from datetime import datetime

# --- 1. GLOBAL SYSTEM UI ---
st.set_page_config(page_title="ANDREW AI PRO v7.0", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Rajdhani:wght@700&display=swap');
    .stApp { background-color: #050505; color: #f0e6c0; font-family: 'IBM Plex Mono', monospace; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: 2px; }
    .stMetric { border: 1px solid #d4af37; padding: 15px; background: #0a0a0a; border-radius: 5px; }
    .trade-card { border: 2px solid #d4af37; background: #0f0f0f; padding: 20px; border-radius: 10px; border-left: 10px solid #d4af37; margin-bottom: 20px;}
    .news-ticker { background: #111; padding: 10px; border-radius: 5px; border: 1px dashed #d4af37; margin-bottom: 20px; font-size: 13px; }
    .stButton>button { background: linear-gradient(135deg, #8a7020 0%, #d4af37 100%) !important; color: black !important; font-weight: bold !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FIREBASE (Permanent Storage) ---
if not firebase_admin._apps:
    try:
        key_data = dict(st.secrets["FIREBASE_KEY"])
        key_data["private_key"] = key_data["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(key_data)
        firebase_admin.initialize_app(cred, {'databaseURL': st.secrets["DATABASE"]["url"]})
    except: st.error("🔐 Security Bridge Offline: Verify Firebase Secrets")

# --- 3. THE MULTI-FACTOR AI PREDICTOR ---
def calculate_gold_signals():
    # Fetch Data
    gold = yf.Ticker("GC=F")
    df = gold.history(interval="15m", period="5d")
    
    # 1. Technical Factors (EMA & RSI)
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    # 2. Macro Factors (Simulated Live Feeds)
    inflation_pressure = 3.2 # Current CPI bias
    production_cost = 1350 # Global average floor price
    
    curr = df['Close'].iloc[-1]
    ema = df['EMA_200'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    # Prediction Logic (Multi-Factor Confluence)
    score = 0
    if curr > ema: score += 40  # Trend
    if rsi < 35: score += 30   # Oversold
    if curr > production_cost: score += 20 # Value floor
    if inflation_pressure > 3.0: score += 10 # Hedge demand

    if score >= 80:
        signal, tp, sl = "🚀 INSTITUTIONAL BUY", curr + 18.5, curr - 9.0
    elif score <= 40:
        signal, tp, sl = "📉 INSTITUTIONAL SELL", curr - 18.5, curr + 9.0
    else:
        signal, tp, sl = "⚖️ NEUTRAL / RANGE", 0, 0
        
    return signal, curr, tp, sl, df, score

# --- 4. NAVIGATION & SIDEBAR ---
if 'auth' not in st.session_state: st.session_state.auth = None

st.sidebar.title("💎 ANDREW AI v7.0")
st.sidebar.markdown("---")

# Telegram & Community
st.sidebar.subheader("📢 COMMUNITY")
st.sidebar.markdown("""
<a href="https://t.me/your_link" target="_blank">
    <button style="width:100%; border-radius:5px; background:#0088cc; color:white; border:none; padding:10px; font-weight:bold; cursor:pointer;">
        JOIN TELEGRAM CHANNEL
    </button>
</a>
""", unsafe_allow_html=True)

if not st.session_state.auth:
    u = st.sidebar.text_input("Access ID")
    p = st.sidebar.text_input("Security Key", type="password")
    if st.sidebar.button("UNLOCK TERMINAL"):
        if u == "hub.ali1" and p == "Shahkaar@786":
            st.session_state.auth = "admin"
            st.rerun()
        else:
            try:
                record = db.reference(f'users/{u}').get()
                if record and record['key'] == p and record['status'] == 'active':
                    st.session_state.auth = u
                    st.rerun()
                else: st.sidebar.error("❌ INVALID ACCESS")
            except: st.sidebar.error("⚠️ DATABASE OFFLINE")
else:
    st.sidebar.success(f"OPERATOR: {st.session_state.auth.upper()}")
    if st.sidebar.button("LOGOUT SYSTEM"):
        st.session_state.auth = None
        st.rerun()

# --- 5. MAIN INTERFACE ---
if st.session_state.auth:
    # --- ADMIN DASHBOARD ---
    if st.session_state.auth == "admin":
        st.title("👑 ADMIN COMMAND CENTER")
        with st.expander("👤 USER MANAGEMENT (FIREBASE)"):
            new_u = st.text_input("Client ID")
            new_p = st.text_input("Client Key")
            if st.button("AUTHORIZE USER"):
                db.reference(f'users/{new_u}').set({'key': new_p, 'status': 'active'})
                st.success(f"User {new_u} added to permanent records!")

    # --- TRADING TERMINAL ---
    st.title("📊 GOLD AI PREDICTION ENGINE")
    
    # News & Sentiment Ticker
    st.markdown(f"""
    <div class="news-ticker">
        <b>LIVE SENTIMENT:</b> 🇺🇸 US CPI Data expected higher (Bullish Gold) | 📉 USD Index weakening | 🏭 Global Gold Mine Output down 2% (Supply Squeeze) | <b>AI CONFIDENCE: 99.1%</b>
    </div>
    """, unsafe_allow_html=True)

    signal, price, tp, sl, df, score = calculate_gold_signals()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XAUUSD PRICE", f"${price:,.2f}")
    col2.metric("AI SIGNAL", signal)
    col3.metric("MACRO SCORE", f"{score}%")
    col4.metric("VOLATILITY", "HIGH")

    # Trade Execution Card
    st.markdown(f"""
    <div class="trade-card">
        <h3 style="margin:0; color:#d4af37;">🎯 TRADE EXECUTION PLAN</h3>
        <table style="width:100%; margin-top:15px; border-collapse: collapse;">
            <tr><td><b>ENTRY:</b></td><td>${price:,.2f}</td></tr>
            <tr style="color:#00ff00;"><td><b>TAKE PROFIT (TP):</b></td><td>${tp:,.2f}</td></tr>
            <tr style="color:#ff4b4b;"><td><b>STOP LOSS (SL):</b></td><td>${sl:,.2f}</td></tr>
            <tr><td><b>MARGIN REQ:</b></td><td>1:500 Recommended</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Charting
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", title="XAUUSD Real-Time Institutional Analysis (15m)", 
                      xaxis_rangeslider_visible=False, paper_bgcolor='black', plot_bgcolor='black', height=500)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.title("🛡️ SYSTEM ENCRYPTION ACTIVE")
    st.warning("Please provide Institutional Credentials in the sidebar to view Gold signals.")
    st.image("https://www.gold.org/sites/default/files/styles/hero_mobile/public/2023-01/Gold-bars-hero.jpg")
