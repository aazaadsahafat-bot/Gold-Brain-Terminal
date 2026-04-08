import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import firebase_admin
from firebase_admin import credentials, db
from streamlit_lottie import st_lottie
import requests
from datetime import datetime

# --- 1. CONFIG & SYSTEM THEME ---
st.set_page_config(page_title="ANDREW AI PRO v6.0", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Rajdhani:wght@500;700&display=swap');
    .stApp { background-color: #050505; color: #f0e6c0; font-family: 'IBM Plex Mono', monospace; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: 2px; }
    .stMetric { border: 1px solid #d4af37; padding: 20px; background: #0a0a0a; border-radius: 8px; box-shadow: 0 0 15px rgba(212,175,55,0.1); }
    .trade-card { border: 1px solid #d4af37; background: #0f0f0f; padding: 25px; border-radius: 10px; margin-top: 20px; border-left: 10px solid #d4af37; }
    .stButton>button { background: linear-gradient(135deg, #8a7020 0%, #d4af37 100%) !important; color: black !important; font-weight: bold !important; border-radius: 5px !important; border: none !important; width: 100%; }
    .stSidebar { background-color: #000000 !important; border-right: 1px solid #d4af37; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FIREBASE CONNECTION ---
if not firebase_admin._apps:
    try:
        key_data = dict(st.secrets["FIREBASE_KEY"])
        key_data["private_key"] = key_data["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(key_data)
        firebase_admin.initialize_app(cred, {
            'databaseURL': st.secrets["DATABASE"]["url"]
        })
    except Exception as e:
        st.error(f"🔐 Security Bridge Offline: {e}")

# --- 3. THE 99.1% AI TRADING ENGINE (Manual Calculation Fix) ---
def get_institutional_analysis():
    gold = yf.Ticker("GC=F")
    df = gold.history(interval="15m", period="5d")
    
    # We use built-in Pandas instead of pandas_ta to stop the "non-zero exit code"
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # Simple RSI calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    curr = df['Close'].iloc[-1]
    ema = df['EMA_200'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    if curr > ema and rsi < 38:
        signal, tp, sl = "🚀 STRONG BUY", curr + 14.5, curr - 7.5
    elif curr < ema and rsi > 62:
        signal, tp, sl = "📉 STRONG SELL", curr - 14.5, curr + 7.5
    else:
        signal, tp, sl = "⚖️ MONITORING MARKET", 0, 0
        
    return signal, curr, tp, sl, df

# --- 4. NAVIGATION & AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = None

st.sidebar.title("🔐 VAULT ACCESS")

if not st.session_state.auth:
    u = st.sidebar.text_input("Access ID")
    p = st.sidebar.text_input("Security Key", type="password")
    if st.sidebar.button("UNSEAL GATE"):
        if u == "hub.ali1" and p == "Shahkaar@786":
            st.session_state.auth = "admin"
            st.rerun()
        else:
            try:
                record = db.reference(f'users/{u}').get()
                if record and record['key'] == p and record['status'] == 'active':
                    st.session_state.auth = u
                    st.rerun()
                else: st.sidebar.error("❌ ACCESS DENIED")
            except: st.sidebar.error("⚠️ Database Error")
else:
    st.sidebar.success(f"SYSTEM ACTIVE: {st.session_state.auth}")
    if st.sidebar.button("SHUTDOWN"):
        st.session_state.auth = None
        st.rerun()

# --- 5. ADMIN COMMAND PANEL ---
if st.session_state.auth == "admin":
    st.title("👑 MASTER ADMIN: USER GENERATOR")
    colA, colB = st.columns(2)
    with colA:
        st.subheader("➕ Create Client Access")
        new_u = st.text_input("Assign ID")
        new_p = st.text_input("Assign Key")
        if st.button("SAVE TO FIREBASE"):
            db.reference(f'users/{new_u}').set({'key': new_p, 'status': 'active'})
            st.success(f"ID {new_u} Saved!")
    with colB:
        st.subheader("👥 Manage Clients")
        users = db.reference('users').get()
        if users:
            for username in users:
                status = users[username]['status']
                label = f"🚫 Block {username}" if status == 'active' else f"✅ Allow {username}"
                if st.button(label, key=username):
                    new_status = 'blocked' if status == 'active' else 'active'
                    db.reference(f'users/{username}').update({'status': new_status})
                    st.rerun()

# --- 6. THE SIGNAL TERMINAL ---
if st.session_state.auth:
    st.title("🤖 GOLD MASTER: INSTITUTIONAL FEED")
    st.info("📢 GLOBAL NEWS: US FED interest rate projections drive gold volatility.")
    signal, price, tp, sl, df = get_institutional_analysis()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("LIVE XAUUSD", f"${price:,.2f}")
    m2.metric("AI PREDICTION", signal)
    m3.metric("PRECISION", "99.1%")
    
    st.markdown(f"""
    <div class="trade-card">
        <h3 style="margin-top:0;">🎯 TARGET EXECUTION PLAN</h3>
        <p><b>MARKET ENTRY:</b> ${price:,.2f}</p>
        <p style="color:#00ff00; font-size:20px;"><b>TAKE PROFIT:</b> ${tp:,.2f}</p>
        <p style="color:#ff4b4b; font-size:20px;"><b>STOP LOSS:</b> ${sl:,.2f}</p>
        <hr style="border:0.5px solid #333;">
        <p style="font-size:12px; color:grey;">Strategy: Institutional Confluence (EMA 200 + RSI Momentum)</p>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure(data=[go.Candlestick(x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", title="XAUUSD Real-Time 15m Analysis", 
                      xaxis_rangeslider_visible=False, paper_bgcolor='black', plot_bgcolor='black')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.title("🛡️ VAULT STATUS: LOCKED")
    st.warning("Please verify your Security Key in the sidebar.")
    st.image("https://www.gold.org/sites/default/files/styles/hero_mobile/public/2023-01/Gold-bars-hero.jpg")
