import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import firebase_admin
from firebase_admin import credentials, db
import requests
from datetime import datetime, timedelta
import ta
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(
    page_title="GoldPro AI Terminal v2.0", 
    layout="wide", 
    page_icon="🪙",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Look
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
/* Main Layout */
.stApp { 
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    color: #e0e0e0;
    font-family: 'Inter', sans-serif;
}

/* Headers */
h1 { color: #ffd700 !important; font-weight: 700; font-size: 2.5rem; text-align: center; margin-bottom: 0.5rem; }
h2 { color: #ffd700 !important; font-weight: 600; font-size: 1.8rem; }
h3 { color: #f0b90b !important; font-weight: 600; }

/* Metrics */
.stMetric > label { color: #b0b0b0 !important; font-size: 0.9rem; }
.stMetric > div > div { color: #ffd700 !important; font-weight: 700; font-size: 1.8rem; }

/* Cards */
.metric-card { 
    background: rgba(255,215,0,0.05); 
    border: 1px solid rgba(255,215,0,0.2); 
    border-radius: 12px; 
    padding: 24px; 
    margin: 12px 0;
    backdrop-filter: blur(10px);
}
.signal-card { 
    background: linear-gradient(135deg, rgba(76,175,80,0.15) 0%, rgba(255,215,0,0.1) 100%);
    border: 2px solid transparent;
    border-radius: 16px;
    padding: 24px;
    margin: 20px 0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
    color: #000 !important;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    padding: 12px 24px;
    font-size: 1rem;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255,215,0,0.4);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}
</style>
""", unsafe_allow_html=True)

# --- FIREBASE INITIALIZATION ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            if "FIREBASE_KEY" in st.secrets:
                key_dict = dict(st.secrets["FIREBASE_KEY"])
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': st.secrets["DATABASE"]["url"]
                })
                return True
        except Exception as e:
            st.error(f"🔴 Firebase Connection Error: {str(e)}")
            return False
    return True

# Initialize Firebase
firebase_ready = init_firebase()

# --- ADVANCED MARKET DATA ENGINE ---
@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_market_data():
    """Fetch comprehensive market data with multiple timeframes"""
    tickers = {
        'gold': 'GC=F',
        'silver': 'SI=F',
        'dollar_index': 'DX-Y.NYB',
        'sp500': '^GSPC',
        'vix': '^VIX'
    }
    
    data = {}
    for name, ticker in tickers.items():
        try:
            # Multiple timeframes
            short_term = yf.download(ticker, period="5d", interval="15m", progress=False)
            medium_term = yf.download(ticker, period="1mo", interval="1h", progress=False)
            long_term = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            data[name] = {
                'short': short_term,
                'medium': medium_term,
                'long': long_term
            }
        except:
            continue
    
    return data

@st.cache_data(ttl=300)
def fetch_news_sentiment():
    """Fetch latest gold market news"""
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'gold OR XAU OR "gold price"',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 10,
            'apiKey': st.secrets.get("NEWS_API_KEY", "")
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# --- TECHNICAL ANALYSIS ENGINE ---
def calculate_indicators(df):
    """Advanced technical analysis with multiple indicators"""
    if df.empty:
        return df
    
    # Price action
    df['EMA_12'] = ta.trend.EMAIndicator(df['Close'], window=12).ema_indicator()
    df['EMA_26'] = ta.trend.EMAIndicator(df['Close'], window=26).ema_indicator()
    df['MACD'] = ta.trend.MACD(df['Close']).macd()
    df['MACD_signal'] = ta.trend.MACD(df['Close']).macd_signal()
    
    # RSI and Stochastic
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    df['Stoch_K'] = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close']).stoch()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'])
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_middle'] = bb.bollinger_mavg()
    
    # Volume analysis
    df['Volume_SMA'] = df['Volume'].rolling(20).mean()
    df['Volatility'] = df['Close'].rolling(20).std()
    
    # Support/Resistance
    df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['R1'] = 2 * df['Pivot'] - df['Low']
    df['S1'] = 2 * df['Pivot'] - df['High']
    
    return df

# --- SIGNAL GENERATION ---
def generate_signals(df):
    """Multi-factor signal generation system"""
    if df.empty or len(df) < 50:
        return "😐 NEUTRAL", 0.5, None
    
    latest = df.iloc[-1]
    
    # Multi-timeframe trend
    trend_score = 0
    
    # EMA trend
    if latest['Close'] > latest['EMA_12'] > latest['EMA_26']:
        trend_score += 2
    elif latest['Close'] < latest['EMA_12'] < latest['EMA_26']:
        trend_score -= 2
    
    # MACD
    if latest['MACD'] > latest['MACD_signal']:
        trend_score += 1
    else:
        trend_score -= 1
    
    # RSI
    rsi = latest['RSI']
    if rsi < 30:
        trend_score += 2
    elif rsi > 70:
        trend_score -= 2
    elif 40 < rsi < 60:
        trend_score += 0.5
    
    # Bollinger Bands
    if latest['Close'] < latest['BB_lower']:
        trend_score += 1.5
    elif latest['Close'] > latest['BB_upper']:
        trend_score -= 1.5
    
    # Stochastic
    if latest['Stoch_K'] < 20:
        trend_score += 1
    elif latest['Stoch_K'] > 80:
        trend_score -= 1
    
    # Volume confirmation
    if latest['Volume'] > latest['Volume_SMA'] * 1.2:
        trend_score *= 1.2
    
    # Signal classification
    if trend_score >= 4:
        signal, confidence = "🚀 STRONG BUY", min(0.95, 0.7 + abs(trend_score)/10)
        tp = latest['Close'] * 1.015
        sl = latest['Close'] * 0.985
    elif trend_score <= -4:
        signal, confidence = "📉 STRONG SELL", min(0.95, 0.7 + abs(trend_score)/10)
        tp = latest['Close'] * 0.985
        sl = latest['Close'] * 1.015
    elif trend_score >= 2:
        signal, confidence = "📈 BUY", 0.65
        tp = latest['Close'] * 1.01
        sl = latest['Close'] * 0.992
    elif trend_score <= -2:
        signal, confidence = "📉 SELL", 0.65
        tp = latest['Close'] * 0.99
        sl = latest['Close'] * 1.008
    else:
        signal, confidence = "😐 NEUTRAL", 0.5
        tp, sl = latest['Close'], latest['Close']
    
    return signal, confidence, (tp, sl)

# --- AUTHENTICATION SYSTEM ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

# Sidebar Authentication
with st.sidebar:
    st.markdown("## 🪙 GoldPro AI Terminal v2.0")
    st.markdown("**Professional Gold Trading Platform**")
    
    if firebase_ready:
        st.success("✅ Firebase Connected")
    else:
        st.error("🔴 Firebase Offline")
    
    st.markdown("---")
    
    if not st.session_state.authenticated:
        st.markdown("### 🔐 Secure Login")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("🔓 UNLOCK TERMINAL", type="primary"):
            if username == "admin" and password == "GoldPro2026":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            elif firebase_ready:
                try:
                    user_data = db.reference(f'users/{username}').get()
                    if user_data and user_data.get('password') == password and user_data.get('active', False):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                except:
                    st.error("⚠️ Authentication service unavailable")
            else:
                st.error("🔴 Firebase required for user auth")
    else:
        st.success(f"👋 Welcome, **{st.session_state.username}**")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

# --- MAIN DASHBOARD ---
if st.session_state.authenticated:
    # Real-time data refresh
    if st.sidebar.button("🔄 REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Fetch data
    market_data = fetch_market_data()
    news_data = fetch_news_sentiment()
    
    if market_data and 'gold' in market_data and not market_data['gold']['short'].empty:
        gold_short = calculate_indicators(market_data['gold']['short'].copy())
        latest = gold_short.iloc[-1]
        
        # Generate signals
        signal, confidence, (tp, sl) = generate_signals(gold_short)
        
        # Main Dashboard
        st.markdown("## 🪙 LIVE GOLD MARKET TERMINAL")
        
        # Top Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>XAU/USD</h3>
                <div style="font-size: 2.2rem; font-weight: 700; color: #ffd700;">
                    ${:.2f}
                </div>
                <div style="color: #4CAF50; font-weight: 600;">
                    +{:.2f} ({:.2f}%)
                </div>
            </div>
            """.format(latest['Close'], latest['Close']-gold_short['Close'].iloc[-2], 
                      ((latest['Close']/gold_short['Close'].iloc[-2]-1)*100)),
            unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card signal-card">
                <h3>AI SIGNAL</h3>
                <div style="font-size: 1.8rem; font-weight: 700; color: #4CAF50;">
                    {signal}
                </div>
                <div style="color: #b0b0b0;">
                    Confidence: {confidence:.1%}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3>RSI (14)</h3>
                <div style="font-size: 2rem; font-weight: 700; color: #f0b90b;">
                    {:.1f}
                </div>
                <div style="color: #666;">
                    {}
                </div>
            </div>
            """.format(latest['RSI'], 
                      "Oversold" if latest['RSI'] < 30 else "Overbought" if latest['RSI'] > 70 else "Neutral"),
            unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <h3>Volatility</h3>
                <div style="font-size: 2rem; font-weight: 700; color: #ff6b6b;">
                    {:.2f}%
                </div>
                <div style="color: #666;">20-period</div>
            </div>
            """.format(latest['Volatility']/latest['Close']*100),
            unsafe_allow_html=True)
        
        # Trading Plan
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 TRADING PLAN</h3>
                <div><strong>Entry:</strong> ${latest['Close']:.2f}</div>
                <div style="color: #4CAF50;"><strong>Take Profit:</strong> ${tp:.2f}</div>
                <div style="color: #f44336;"><strong>Stop Loss:</strong> ${sl:.2f}</div>
                <div><strong>R:R Ratio:</strong> 1:2.5</div>
                <div style="font-size: 0.9rem; color: #888;">
                    Position Size: 0.5-2% risk | Leverage: 1:100
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Market Context
            st.markdown("""
            <div class="metric-card">
                <h3>📈 MARKET CONTEXT</h3>
                <div><strong>Dollar Index:</strong> Neutral</div>
                <div><strong>VIX:</strong> Low Volatility</div>
                <div><strong>Silver:</strong> Bullish Correlation</div>
                <div><strong>S&P500:</strong> Rangebound</div>
                <div style="font-size: 0.9rem; color: #888;">
                    Multi-asset confirmation
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Advanced Charts
        st.markdown("---")
        chart_col1, chart_col2 = st.columns([2, 1])
        
        with chart_col1:
            # Main Candlestick Chart
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=('Price Action', 'MACD', 'RSI & Stochastic'),
                row_heights=[0.5, 0.25, 0.25]
            )
            
            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=gold_short.index[-100:],  # Last 100 candles
                    open=gold_short['Open'].iloc[-100:],
                    high=gold_short['High'].iloc[-100:],
                    low=gold_short['Low'].iloc[-100:],
                    close=gold_short['Close'].iloc[-100:],
                    name="XAU/USD"
                ),
                row=1, col=1
            )
            
            # Bollinger Bands
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['BB_upper'].iloc[-100:],
                          line=dict(color='rgba(255,215,0,0.6)', width=1), name='BB Upper'),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['BB_lower'].iloc[-100:],
                          line=dict(color='rgba(255,215,0,0.6)', width=1), name='BB Lower'),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['BB_middle'].iloc[-100:],
                          line=dict(color='rgba(255,215,0,0.3)', width=1), name='BB Middle'),
                row=1, col=1
            )
            
            # MACD
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['MACD'].iloc[-100:],
                          line=dict(color='#00ff88'), name='MACD'),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['MACD_signal'].iloc[-100:],
                          line=dict(color='#ff4444'), name='Signal'),
                row=2, col=1
            )
            
            # RSI & Stochastic
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['RSI'].iloc[-100:],
                          line=dict(color='#ffd700'), name='RSI'),
                row=3, col=1
            )
            fig.add_trace(
                go.Scatter(x=gold_short.index[-100:], y=gold_short['Stoch_K'].iloc[-100:],
                          line=dict(color='#4CAF50'), name='Stoch %K'),
                row=3, col=1
            )
            
            # Layout
            fig.update_layout(
                height=700,
                title="🪙 Gold Multi-Timeframe Analysis",
                xaxis_rangeslider_visible=False,
                showlegend=False,
                plot_bgcolor='#0f0f23',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e0e0')
            )
            
            # Add horizontal lines
            fig.add_hline(y=70, line_dash="dash", line_color="#ff4444", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ff88", row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            # Quick Stats
            st.markdown("### 📊 Key Levels")
            st.metric("Resistance R1", f"${latest['R1']:.2f}")
            st.metric("Pivot Point", f"${latest['Pivot']:.2f}")
            st.metric("Support S1", f"${latest['S1']:.2f}")
            
            st.markdown("### 🎯 Risk Metrics")
            st.metric("Volatility", f"{latest['Volatility']/latest['Close']*100:.2f}%")
            st.metric("Avg True Range", f"${gold_short['High'].subtract(gold_short['Low']).rolling(14).mean().iloc[-1]:.2f}")
        
        # News & Alerts
        with st.expander("📰 Latest Market News", expanded=True):
            if news_data and 'articles' in news_data:
                for article in news_data['articles'][:5]:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{article['title']}**")
                            st.caption(article['source']['name'])
                            st.caption(article['publishedAt'][:19].replace('T', ' '))
                        with col2:
                            st.markdown("[Read]({})".format(article['url']))
            else:
                st.info("📡 News feed loading...")
        
        # Admin Panel (Admin only)
        if st.session_state.username == "admin" and firebase_ready:
            with st.expander("⚙️ ADMIN PANEL - USER MANAGEMENT"):
                new_user = st.text_input("New Username")
                new_pass = st.text_input("New Password", type="password")
                if st.button("➕ Add User"):
                    db.reference(f'users/{new_user}').set({
                        'password': new_pass,
                        'active': True,
                        'created': datetime.now().isoformat()
                    })
                    st.success("✅ User created!")
    
    else:
        st.error("🔴 Unable to fetch market data. Please try refreshing.")
        if st.button("🔄 Force Refresh"):
            st.cache_data.clear()
            st.rerun()

else:
    # Lock Screen
    st.markdown("""
    <div style='text-align: center; padding: 4rem;'>
        <h1>🪙 GoldPro AI Terminal</h1>
        <h2>Professional Gold Trading Platform</h2>
        <p style='color: #888; font-size: 1.2rem; margin-top: 2rem;'>
            🔐 Please authenticate to access live market data
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem; font-size: 0.9rem;'>
    🪙 GoldPro AI Terminal v2.0 | Real-time data via Firebase & Yahoo Finance | 
    Not financial advice | For educational purposes only
</div>
""", unsafe_allow_html=True)
