"""
Indian Stock Market Analyzer — Full Edition
Live NSE/BSE • Option Chain • Watchlist/Portfolio • Custom Screener • Alerts
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import warnings
warnings.filterwarnings("ignore")

from auth import (
    get_settings, save_settings, get_users, save_users,
    register_user, login_user, trial_days_left, has_access,
    _hash_password, _verify_password, load_json, save_json,
    USERS_FILE, SETTINGS_FILE, DATA_DIR
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🇮🇳 Indian Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF6B35, #F7931E, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header { color: #888; font-size: 1rem; margin-bottom: 1.5rem; }
    .positive { color: #00c853; font-weight: 700; }
    .negative { color: #ff1744; font-weight: 700; }
    .alert-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-left: 4px solid #FF6B35;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJAJFINSV.NS", "WIPRO.NS",
    "ULTRACEMCO.NS", "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "M&M.NS",
    "TECHM.NS", "ONGC.NS", "TATAMOTORS.NS", "ADANIENT.NS", "JSWSTEEL.NS",
    "TATASTEEL.NS", "INDUSINDBK.NS", "COALINDIA.NS", "BAJAJ-AUTO.NS", "HDFCLIFE.NS",
    "DIVISLAB.NS", "GRASIM.NS", "CIPLA.NS", "BPCL.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "HEROMOTOCO.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "SHREECEM.NS",
    "UPL.NS", "TATACONSUM.NS", "ADANIPORTS.NS", "SBILIFE.NS", "HINDALCO.NS"
]

SECTOR_MAP = {
    "RELIANCE.NS": "Energy", "TCS.NS": "IT", "HDFCBANK.NS": "Banking",
    "INFY.NS": "IT", "ICICIBANK.NS": "Banking", "HINDUNILVR.NS": "FMCG",
    "ITC.NS": "FMCG", "SBIN.NS": "Banking", "BHARTIARTL.NS": "Telecom",
    "KOTAKBANK.NS": "Banking", "LT.NS": "Infra", "AXISBANK.NS": "Banking",
    "BAJFINANCE.NS": "Finance", "ASIANPAINT.NS": "Paints", "MARUTI.NS": "Auto",
    "HCLTECH.NS": "IT", "SUNPHARMA.NS": "Pharma", "TITAN.NS": "Consumer",
    "BAJAJFINSV.NS": "Finance", "WIPRO.NS": "IT", "ULTRACEMCO.NS": "Cement",
    "NESTLEIND.NS": "FMCG", "POWERGRID.NS": "Power", "NTPC.NS": "Power",
    "M&M.NS": "Auto", "TECHM.NS": "IT", "ONGC.NS": "Energy",
    "TATAMOTORS.NS": "Auto", "ADANIENT.NS": "Conglomerate", "JSWSTEEL.NS": "Steel",
    "TATASTEEL.NS": "Steel", "INDUSINDBK.NS": "Banking", "COALINDIA.NS": "Mining",
    "BAJAJ-AUTO.NS": "Auto", "HDFCLIFE.NS": "Insurance", "DIVISLAB.NS": "Pharma",
    "GRASIM.NS": "Cement", "CIPLA.NS": "Pharma", "BPCL.NS": "Energy",
    "DRREDDY.NS": "Pharma", "EICHERMOT.NS": "Auto", "HEROMOTOCO.NS": "Auto",
    "BRITANNIA.NS": "FMCG", "APOLLOHOSP.NS": "Healthcare", "SHREECEM.NS": "Cement",
    "UPL.NS": "Agrochem", "TATACONSUM.NS": "FMCG", "ADANIPORTS.NS": "Ports",
    "SBILIFE.NS": "Insurance", "HINDALCO.NS": "Metals"
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "user_data")
os.makedirs(DATA_DIR, exist_ok=True)
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")

# ─────────────────────────────────────────────
# PERSISTENCE HELPERS
# ─────────────────────────────────────────────
def load_json(path, default=None):
    if default is None:
        default = []
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────────
# DATA FETCH HELPERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_live_quote(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        change = last["Close"] - prev["Close"]
        change_pct = (change / prev["Close"]) * 100 if prev["Close"] else 0
        return {
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "full_symbol": symbol,
            "name": info.get("shortName") or info.get("longName") or symbol,
            "price": round(float(last["Close"]), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "open": round(float(last["Open"]), 2),
            "high": round(float(last["High"]), 2),
            "low": round(float(last["Low"]), 2),
            "volume": int(last["Volume"]),
            "prev_close": round(float(prev["Close"]), 2),
            "market_cap": info.get("marketCap"),
            "pe": info.get("trailingPE") or info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "sector": info.get("sector") or SECTOR_MAP.get(symbol, "—"),
            "industry": info.get("industry", "—"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margins": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "current_ratio": info.get("currentRatio"),
            "book_value": info.get("bookValue"),
            "target_mean": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
        }
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_multiple_quotes(symbols: list):
    results = []
    for sym in symbols:
        q = get_live_quote(sym)
        if q:
            results.append(q)
    return results


@st.cache_data(ttl=600)
def get_historical(symbol: str, period: str = "1y"):
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_fundamentals(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        return {
            "info": ticker.info,
            "financials": ticker.financials,
            "balance": ticker.balance_sheet,
            "cashflow": ticker.cashflow,
        }
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_option_chain(symbol: str):
    """Fetch option chain via yfinance. Returns (calls_df, puts_df, expirations) or None."""
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return None
        return expirations
    except Exception:
        return None


@st.cache_data(ttl=180)
def get_option_chain_for_expiry(symbol: str, expiry: str):
    try:
        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiry)
        calls = chain.calls.copy()
        puts = chain.puts.copy()
        # Clean columns
        keep = ["contractSymbol", "strike", "lastPrice", "bid", "ask", "change",
                "percentChange", "volume", "openInterest", "impliedVolatility", "inTheMoney"]
        calls = calls[[c for c in keep if c in calls.columns]]
        puts = puts[[c for c in keep if c in puts.columns]]
        return calls, puts
    except Exception:
        return None, None


def score_stock(q: dict) -> float:
    score = 50.0
    pe = q.get("pe")
    if pe and 0 < pe < 15:
        score += 12
    elif pe and 15 <= pe < 25:
        score += 8
    elif pe and 25 <= pe < 40:
        score += 3
    elif pe and pe >= 40:
        score -= 5
    roe = q.get("roe")
    if roe:
        if roe > 0.20:
            score += 12
        elif roe > 0.15:
            score += 8
        elif roe > 0.10:
            score += 4
        elif roe < 0:
            score -= 8
    de = q.get("debt_to_equity")
    if de is not None:
        if de < 30:
            score += 8
        elif de < 70:
            score += 4
        elif de > 150:
            score -= 8
    pm = q.get("profit_margins")
    if pm:
        if pm > 0.20:
            score += 8
        elif pm > 0.10:
            score += 5
        elif pm < 0:
            score -= 6
    chg = q.get("change_pct", 0)
    if 0 < chg < 3:
        score += 4
    elif chg >= 3:
        score += 2
    elif chg < -3:
        score -= 4
    rg = q.get("revenue_growth")
    if rg and rg > 0.15:
        score += 6
    elif rg and rg > 0.05:
        score += 3
    return max(0, min(100, round(score, 1)))


def format_number(n):
    if n is None:
        return "—"
    if abs(n) >= 1e12:
        return f"₹{n/1e12:.2f}T"
    if abs(n) >= 1e9:
        return f"₹{n/1e9:.2f}B"
    if abs(n) >= 1e7:
        return f"₹{n/1e7:.2f}Cr"
    if abs(n) >= 1e5:
        return f"₹{n/1e5:.2f}L"
    return f"₹{n:,.2f}"


def send_email_alert(to_email: str, subject: str, body: str,
                     smtp_server: str, smtp_port: int,
                     smtp_user: str, smtp_pass: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False




@st.cache_data(ttl=600)
def get_stock_news(symbol: str, limit: int = 12):
    """Company news via yfinance."""
    items = []
    try:
        t = yf.Ticker(symbol)
        raw = t.news or []
        for n in raw[:limit]:
            # yfinance formats vary
            content_block = n.get("content") if isinstance(n.get("content"), dict) else None
            if content_block:
                title = content_block.get("title") or n.get("title") or "Untitled"
                summary = content_block.get("summary") or content_block.get("description") or ""
                pub = content_block.get("provider", {}) if isinstance(content_block.get("provider"), dict) else {}
                publisher = pub.get("displayName") or n.get("publisher") or "News"
                link = ""
                cu = content_block.get("canonicalUrl") or content_block.get("clickThroughUrl") or {}
                if isinstance(cu, dict):
                    link = cu.get("url") or ""
                elif isinstance(cu, str):
                    link = cu
                ts = content_block.get("pubDate") or content_block.get("displayTime") or ""
            else:
                title = n.get("title") or "Untitled"
                summary = n.get("summary") or ""
                publisher = n.get("publisher") or "News"
                link = n.get("link") or ""
                ts = n.get("providerPublishTime") or n.get("pubDate") or ""
                if isinstance(ts, (int, float)):
                    try:
                        ts = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts = str(ts)
            items.append({
                "title": title,
                "summary": (summary or "")[:280],
                "publisher": publisher,
                "link": link,
                "time": str(ts)[:19] if ts else "",
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            })
    except Exception:
        pass
    return items


@st.cache_data(ttl=600)
def get_market_news_bundle():
    """Aggregate news from major Indian tickers + indices."""
    symbols = [
        "^NSEI", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS",
        "SBIN.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "ADANIENT.NS"
    ]
    seen = set()
    all_news = []
    for sym in symbols:
        for item in get_stock_news(sym, limit=5):
            key = (item.get("title") or "")[:80]
            if key and key not in seen:
                seen.add(key)
                all_news.append(item)
    return all_news[:40]


def render_news_cards(items, empty_msg="No news available right now."):
    if not items:
        st.info(empty_msg)
        return
    for it in items:
        link = it.get("link") or ""
        link_html = f'<div class="news-link"><a href="{link}" target="_blank" rel="noopener">Read full article →</a></div>' if link else ""
        st.markdown(f"""
        <div class="news-card">
          <div class="news-title">{it.get("title","")}</div>
          <div class="news-meta">{it.get("publisher","News")} · {it.get("time","")} · {it.get("symbol","")}</div>
          <div style="color:#a0a0b0;font-size:0.9rem;margin:0.4rem 0;">{it.get("summary","")}</div>
          {link_html}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# AUTH GATE + MODERN CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stApp {
  background:
    linear-gradient(165deg, rgba(7,7,12,0.88) 0%, rgba(14,14,22,0.90) 45%, rgba(10,15,24,0.92) 100%),
    url('https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1920&q=80');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  background-repeat: no-repeat;
}
.hero-title { font-size: 2.2rem; font-weight: 800;
  background: linear-gradient(135deg, #00f5d4, #7b2cbf, #f72585);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.login-logo { text-align:center; font-size:2.4rem; font-weight:800;
  background: linear-gradient(135deg, #00f5d4, #7b2cbf, #f72585);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.login-tag { text-align:center; color:#6b6b80; margin-bottom:1.2rem; }
.user-badge { display:inline-block; background:rgba(0,245,212,0.1); border:1px solid rgba(0,245,212,0.25);
  color:#00f5d4; padding:0.25rem 0.7rem; border-radius:999px; font-size:0.8rem; font-weight:600; }
.admin-badge { background:rgba(247,37,133,0.12); border-color:rgba(247,37,133,0.3); color:#f72585; }
.trial-banner { background:rgba(247,37,133,0.12); border:1px solid rgba(247,37,133,0.3);
  border-radius:10px; padding:0.7rem 1rem; color:#ffb3d9; margin:0.5rem 0; }
.paywall-box { background:linear-gradient(145deg,#1a1025,#0f1520); border:1px solid rgba(123,44,191,0.4);
  border-radius:20px; padding:2.2rem; text-align:center; max-width:480px; margin:3rem auto; }
.paywall-box h2 { background:linear-gradient(135deg,#00f5d4,#7b2cbf);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(10,10,18,0.98), rgba(14,14,24,0.98));
  border-right: 1px solid rgba(255,255,255,0.06);
}
.stButton > button[kind="primary"] { background: linear-gradient(135deg,#7b2cbf,#f72585); border:none; border-radius:10px; }
.brand-header {
  display:flex; align-items:center; gap:14px; margin-bottom: 1.2rem;
  padding: 0.9rem 1.1rem; border-radius: 16px;
  background: linear-gradient(135deg, rgba(123,44,191,0.15), rgba(0,245,212,0.08));
  border: 1px solid rgba(255,255,255,0.08);
}
.brand-logo {
  width:48px; height:48px; border-radius:12px;
  background: linear-gradient(135deg, #00f5d4, #7b2cbf, #f72585);
  display:flex; align-items:center; justify-content:center;
  font-size:1.5rem; font-weight:800; color:#0a0a0f;
  box-shadow: 0 8px 24px rgba(123,44,191,0.35);
}
.brand-text h1 { margin:0; font-size:1.35rem; font-weight:800; color:#f0f0f5; letter-spacing:-0.3px; }
.brand-text p { margin:0; color:#8b8b9e; font-size:0.85rem; }
.news-card {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; padding: 1rem 1.15rem; margin-bottom: 0.75rem;
  transition: border-color 0.2s;
}
.news-card:hover { border-color: rgba(0,245,212,0.35); }
.news-title { font-weight: 650; color: #e8e8f0; font-size: 1rem; margin-bottom: 0.35rem; }
.news-meta { color: #7a7a8c; font-size: 0.78rem; }
.news-link a { color: #00f5d4; text-decoration: none; font-size: 0.85rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None

_settings = get_settings()

if not st.session_state.get("authenticated"):
    st.markdown(f'<div class="login-logo">◈ {_settings.get("app_name", "StockVista Pro")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-tag">Indian Markets · Research · Screens · Alerts</div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        t_in, t_up = st.tabs(["Sign In", "Create Account"])
        with t_in:
            with st.form("login_form"):
                _u = st.text_input("Username", placeholder="Your username")
                _p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                    ok, uobj, msg = login_user(_u, _p)
                    if ok:
                        st.session_state["user"] = uobj
                        st.session_state["authenticated"] = True
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            st.caption("Welcome back. Enter your credentials to continue.")
        with t_up:
            with st.form("reg_form"):
                _nu = st.text_input("Username", key="reg_u")
                _ne = st.text_input("Email (optional)", key="reg_e")
                _np1 = st.text_input("Password", type="password", key="reg_p1")
                _np2 = st.text_input("Confirm", type="password", key="reg_p2")
                if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                    if _np1 != _np2:
                        st.error("Passwords do not match")
                    else:
                        ok, msg = register_user(_nu, _np1, _ne)
                        st.success(msg) if ok else st.error(msg)
    st.stop()

_user = st.session_state.get("user")
_users = get_users()
if _user and _user["username"] in _users:
    _user = _users[_user["username"]]
    st.session_state["user"] = _user

if not has_access(_user, _settings):
    _price = _settings.get("payment_price", "Rs 499")
    _link = _settings.get("payment_link", "#")
    _days = _settings.get("trial_days", 7)
    st.markdown(f"""
    <div class="paywall-box">
      <div style="font-size:2.5rem;">◈</div>
      <h2>Trial Ended</h2>
      <p style="color:#9b9bb0;">Your {_days}-day free trial is over.<br>Unlock full access to all modules.</p>
      <div style="font-size:1.8rem;font-weight:700;color:#00f5d4;">{_price}</div>
      <div style="color:#666;font-size:0.85rem;margin-bottom:1rem;">one-time · lifetime</div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.link_button("Unlock Full Access", _link, type="primary", use_container_width=True)
        st.caption("After payment, your access is activated within a short time.")
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    st.stop()

_days_left = trial_days_left(_user, _settings)
_is_admin = _user.get("role") == "admin"
_is_paid = _user.get("paid") or _is_admin


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
      <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#00f5d4,#7b2cbf,#f72585);
      display:flex;align-items:center;justify-content:center;font-weight:800;color:#0a0a0f;">◈</div>
      <div style="font-weight:800;font-size:1.1rem;background:linear-gradient(135deg,#00f5d4,#7b2cbf);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;">StockVista</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    _nav = [
            "🏠 Dashboard",
            "🔥 Trending Screens",
            "📊 Stock Research",
            "🏆 Best Stocks",
            "📰 News",
            "⛓️ Option Chain",
            "⭐ Watchlist & Portfolio",
            "🔍 Custom Screener",
            "🔔 Alerts",
        ]
    if _is_admin:
        _nav.append("⚙️ Settings")
    _nav.append("ℹ️ About")
    page = st.radio("Navigate", _nav, label_visibility="collapsed")
    _badge = "user-badge admin-badge" if _is_admin else "user-badge"
    _role = "ADMIN" if _is_admin else ("PRO" if _is_paid else f"TRIAL · {_days_left}d")
    st.markdown(f'<div class="{_badge}">● {_user["username"]} · {_role}</div>', unsafe_allow_html=True)
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    if not _is_paid and _days_left <= 3:
        st.markdown(f'<div class="trial-banner">Trial: {_days_left} day(s) left</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Quick Search")
    search_symbol = st.text_input("Symbol (e.g. RELIANCE, TCS)", value="RELIANCE").upper().strip()
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    suffix = ".NS" if exchange == "NSE" else ".BO"
    full_symbol = f"{search_symbol}{suffix}"

    st.markdown("---")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S IST')}")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────
if page == "🏠 Dashboard":
    st.markdown(f"""
<div class="brand-header">
  <div class="brand-logo">◈</div>
  <div class="brand-text">
    <h1>{_settings.get('app_name', 'StockVista Pro')}</h1>
    <p>Live NSE & BSE · News · Research · Screens · Alerts</p>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<p class="main-header">🇮🇳 Indian Stock Market Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Live NSE & BSE • Option Chain • Watchlist • Screener • Alerts</p>', unsafe_allow_html=True)

    st.subheader("📈 Market Overview")
    idx_cols = st.columns(4)
    indices = {
        "Nifty 50": "^NSEI",
        "Sensex": "^BSESN",
        "Bank Nifty": "^NSEBANK",
        "India VIX": "^INDIAVIX"
    }
    for col, (name, sym) in zip(idx_cols, indices.items()):
        q = get_live_quote(sym)
        with col:
            if q:
                st.metric(label=name, value=f"{q['price']:,.2f}", delta=f"{q['change_pct']:+.2f}%")
            else:
                st.metric(label=name, value="—", delta="N/A")

    st.markdown("---")
    st.subheader("🚀 Nifty 50 Snapshot (Live)")
    with st.spinner("Fetching live Nifty 50 data..."):
        quotes = get_multiple_quotes(NIFTY50)

    if quotes:
        df = pd.DataFrame(quotes)
        df["Score"] = df.apply(lambda r: score_stock(r), axis=1)
        df = df.sort_values("change_pct", ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🟢 Top Gainers")
            gainers = df.head(5)[["symbol", "price", "change_pct", "volume"]].copy()
            gainers.columns = ["Symbol", "Price (₹)", "Change %", "Volume"]
            st.dataframe(gainers.style.format({
                "Price (₹)": "{:.2f}", "Change %": "{:+.2f}", "Volume": "{:,}"
            }), use_container_width=True, hide_index=True)

        with c2:
            st.markdown("#### 🔴 Top Losers")
            losers = df.tail(5).iloc[::-1][["symbol", "price", "change_pct", "volume"]].copy()
            losers.columns = ["Symbol", "Price (₹)", "Change %", "Volume"]
            st.dataframe(losers.style.format({
                "Price (₹)": "{:.2f}", "Change %": "{:+.2f}", "Volume": "{:,}"
            }), use_container_width=True, hide_index=True)

        st.markdown("#### 🏭 Sector Performance")
        sector_df = df.groupby("sector")["change_pct"].mean().reset_index().sort_values("change_pct", ascending=False)
        fig = px.bar(sector_df, x="sector", y="change_pct", color="change_pct",
                     color_continuous_scale=["#ff1744", "#ffeb3b", "#00c853"],
                     labels={"change_pct": "Avg Change %", "sector": "Sector"})
        fig.update_layout(height=350, margin=dict(t=20, b=40), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 Full Nifty 50 Table")
        display_df = df[["symbol", "name", "price", "change_pct", "volume", "pe", "sector", "Score"]].copy()
        display_df.columns = ["Symbol", "Name", "Price (₹)", "Change %", "Volume", "P/E", "Sector", "Score"]
        st.dataframe(display_df.style.format({
            "Price (₹)": "{:.2f}", "Change %": "{:+.2f}", "Volume": "{:,}",
            "P/E": "{:.1f}", "Score": "{:.1f}"
        }), use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("Could not fetch market data. Please try refreshing.")


# ─────────────────────────────────────────────
# PAGE: TRENDING SCREENS
# ─────────────────────────────────────────────
elif page == "🔥 Trending Screens":
    st.markdown('<p class="main-header">🔥 Trending Screens</p>', unsafe_allow_html=True)
    st.markdown("Discover stocks that are moving right now based on price action, volume & momentum.")

    with st.spinner("Scanning Nifty 50 for trends..."):
        quotes = get_multiple_quotes(NIFTY50)

    if not quotes:
        st.error("Unable to fetch data. Try again later.")
        st.stop()

    df = pd.DataFrame(quotes)
    df["Score"] = df.apply(lambda r: score_stock(r), axis=1)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚀 Momentum", "📈 Volume Surge", "💎 Value Picks", "🛡️ Quality", "⚡ High Beta"
    ])

    with tab1:
        st.markdown("#### Strong Momentum Stocks")
        mom = df.sort_values("change_pct", ascending=False).head(10)
        fig = go.Figure(go.Bar(
            x=mom["change_pct"], y=mom["symbol"], orientation="h",
            marker_color=["#00c853" if x >= 0 else "#ff1744" for x in mom["change_pct"]],
            text=[f"{x:+.2f}%" for x in mom["change_pct"]], textposition="outside"
        ))
        fig.update_layout(height=400, yaxis=dict(autorange="reversed"), margin=dict(l=80))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(mom[["symbol", "name", "price", "change_pct", "volume", "sector"]].rename(columns={
            "symbol": "Symbol", "name": "Name", "price": "Price", "change_pct": "Change %",
            "volume": "Volume", "sector": "Sector"
        }), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### Highest Volume Stocks")
        vol = df.sort_values("volume", ascending=False).head(10)
        fig = px.bar(vol, x="symbol", y="volume", color="change_pct",
                     color_continuous_scale=["#ff1744", "#ffeb3b", "#00c853"])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vol[["symbol", "name", "price", "change_pct", "volume"]].rename(columns={
            "symbol": "Symbol", "name": "Name", "price": "Price", "change_pct": "Change %", "volume": "Volume"
        }), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("#### Value Picks (Low P/E + Decent ROE)")
        val = df[(df["pe"].notna()) & (df["pe"] > 0) & (df["pe"] < 25)].copy()
        if not val.empty:
            val = val.sort_values("pe").head(10)
            st.dataframe(val[["symbol", "name", "price", "pe", "roe", "debt_to_equity", "Score"]].rename(columns={
                "symbol": "Symbol", "name": "Name", "price": "Price", "pe": "P/E",
                "roe": "ROE", "debt_to_equity": "D/E", "Score": "Score"
            }).style.format({"Price": "{:.2f}", "P/E": "{:.1f}", "ROE": "{:.1%}", "D/E": "{:.1f}", "Score": "{:.1f}"}),
            use_container_width=True, hide_index=True)
        else:
            st.info("No stocks currently meet the value criteria.")

    with tab4:
        st.markdown("#### Quality Stocks (High ROE + Low Debt)")
        qual = df[(df["roe"].notna()) & (df["roe"] > 0.12)].copy()
        if not qual.empty:
            qual = qual.sort_values("roe", ascending=False).head(10)
            st.dataframe(qual[["symbol", "name", "price", "roe", "profit_margins", "debt_to_equity", "Score"]].rename(columns={
                "symbol": "Symbol", "name": "Name", "price": "Price", "roe": "ROE",
                "profit_margins": "Profit Margin", "debt_to_equity": "D/E", "Score": "Score"
            }).style.format({"Price": "{:.2f}", "ROE": "{:.1%}", "Profit Margin": "{:.1%}", "D/E": "{:.1f}", "Score": "{:.1f}"}),
            use_container_width=True, hide_index=True)
        else:
            st.info("No stocks currently meet the quality criteria.")

    with tab5:
        st.markdown("#### High Beta / Volatile Stocks")
        beta_df = df[df["beta"].notna()].sort_values("beta", ascending=False).head(10)
        if not beta_df.empty:
            st.dataframe(beta_df[["symbol", "name", "price", "beta", "change_pct", "volume"]].rename(columns={
                "symbol": "Symbol", "name": "Name", "price": "Price", "beta": "Beta",
                "change_pct": "Change %", "volume": "Volume"
            }).style.format({"Price": "{:.2f}", "Beta": "{:.2f}", "Change %": "{:+.2f}", "Volume": "{:,}"}),
            use_container_width=True, hide_index=True)
        else:
            st.info("Beta data not available for enough stocks.")


# ─────────────────────────────────────────────
# PAGE: STOCK RESEARCH
# ─────────────────────────────────────────────
elif page == "📊 Stock Research":
    st.markdown('<p class="main-header">📊 Fundamental Research</p>', unsafe_allow_html=True)

    col_search, col_btn = st.columns([3, 1])
    with col_search:
        research_sym = st.text_input("Enter stock symbol", value=search_symbol, key="research_sym").upper().strip()
    with col_btn:
        st.write("")
        st.write("")
        go_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)

    symbol = f"{research_sym}{suffix}"

    if go_btn or research_sym:
        with st.spinner(f"Fetching data for {research_sym}..."):
            q = get_live_quote(symbol)
            hist = get_historical(symbol, "1y")
            fund = get_fundamentals(symbol)

        if not q:
            st.error(f"Could not find data for **{research_sym}**. Check the symbol and exchange.")
            st.stop()

        st.markdown(f"### {q['name']} (`{q['symbol']}`)")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Price", f"₹{q['price']:,.2f}", f"{q['change_pct']:+.2f}%")
        m2.metric("Open", f"₹{q['open']:,.2f}")
        m3.metric("High", f"₹{q['high']:,.2f}")
        m4.metric("Low", f"₹{q['low']:,.2f}")
        m5.metric("Volume", f"{q['volume']:,}")

        st.markdown("---")
        st.subheader("📌 Key Ratios & Valuation")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(f"**P/E Ratio**  \n`{q['pe']:.2f}`" if q.get("pe") else "**P/E Ratio**  \n`—`")
            st.markdown(f"**P/B Ratio**  \n`{q['pb']:.2f}`" if q.get("pb") else "**P/B Ratio**  \n`—`")
        with r2:
            st.markdown(f"**EPS**  \n`₹{q['eps']:.2f}`" if q.get("eps") else "**EPS**  \n`—`")
            st.markdown(f"**Book Value**  \n`₹{q['book_value']:.2f}`" if q.get("book_value") else "**Book Value**  \n`—`")
        with r3:
            roe_str = f"{q['roe']*100:.1f}%" if q.get("roe") else "—"
            st.markdown(f"**ROE**  \n`{roe_str}`")
            de_str = f"{q['debt_to_equity']:.1f}" if q.get("debt_to_equity") else "—"
            st.markdown(f"**Debt/Equity**  \n`{de_str}`")
        with r4:
            st.markdown(f"**Market Cap**  \n`{format_number(q.get('market_cap'))}`")
            dy = f"{q['dividend_yield']*100:.2f}%" if q.get("dividend_yield") else "—"
            st.markdown(f"**Div Yield**  \n`{dy}`")

        score = score_stock(q)
        score_color = "#00c853" if score >= 65 else ("#ffeb3b" if score >= 45 else "#ff1744")
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:1.2rem;border-radius:12px;border-left:5px solid {score_color};margin:1rem 0;">
            <h3 style="margin:0;">Investment Score: <span style="color:{score_color}">{score}/100</span></h3>
            <p style="color:#aaa;margin:0.3rem 0 0 0;">Based on valuation, profitability, leverage, growth & momentum</p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📉 Price Chart (1 Year)")
        if not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"], name="OHLC"
            ))
            hist["SMA20"] = hist["Close"].rolling(20).mean()
            hist["SMA50"] = hist["Close"].rolling(50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], name="SMA 20", line=dict(width=1)))
            fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], name="SMA 50", line=dict(width=1)))
            fig.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(t=30, b=30),
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

            fig_vol = go.Figure(go.Bar(x=hist.index, y=hist["Volume"], marker_color="#4fc3f7", name="Volume"))
            fig_vol.update_layout(height=180, margin=dict(t=10, b=20), showlegend=False)
            st.plotly_chart(fig_vol, use_container_width=True)

        if q.get("52w_high") and q.get("52w_low"):
            st.subheader("📍 52-Week Range")
            low, high, price = q["52w_low"], q["52w_high"], q["price"]
            pct = (price - low) / (high - low) * 100 if high != low else 50
            st.progress(min(max(pct / 100, 0), 1))
            c1, c2, c3 = st.columns(3)
            c1.metric("52W Low", f"₹{low:,.2f}")
            c2.metric("Current", f"₹{price:,.2f}")
            c3.metric("52W High", f"₹{high:,.2f}")

        st.subheader("📑 Additional Fundamentals")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown(f"**Sector:** {q.get('sector', '—')}")
            st.markdown(f"**Industry:** {q.get('industry', '—')}")
            st.markdown(f"**Beta:** {q.get('beta', '—')}")
        with f2:
            pm = f"{q['profit_margins']*100:.1f}%" if q.get("profit_margins") else "—"
            st.markdown(f"**Profit Margin:** {pm}")
            rg = f"{q['revenue_growth']*100:.1f}%" if q.get("revenue_growth") else "—"
            st.markdown(f"**Revenue Growth:** {rg}")
            eg = f"{q['earnings_growth']*100:.1f}%" if q.get("earnings_growth") else "—"
            st.markdown(f"**Earnings Growth:** {eg}")
        with f3:
            st.markdown(f"**Current Ratio:** {q.get('current_ratio', '—')}")
            st.markdown(f"**Analyst Target:** {format_number(q.get('target_mean'))}")
            st.markdown(f"**Recommendation:** {(q.get('recommendation') or '—').upper()}")

        if fund and fund.get("financials") is not None and not fund["financials"].empty:
            with st.expander("📄 Income Statement (Annual)"):
                st.dataframe(fund["financials"].head(12), use_container_width=True)
            with st.expander("📄 Balance Sheet (Annual)"):
                st.dataframe(fund["balance"].head(12), use_container_width=True)
            with st.expander("📄 Cash Flow (Annual)"):
                st.dataframe(fund["cashflow"].head(12), use_container_width=True)

        st.markdown("---")
        st.subheader("📰 Related News")
        with st.spinner("Loading company news..."):
            _co_news = get_stock_news(symbol, limit=8)
        render_news_cards(_co_news, "No company news available for this symbol.")



# ─────────────────────────────────────────────
# PAGE: BEST STOCKS
# ─────────────────────────────────────────────
elif page == "🏆 Best Stocks":
    st.markdown('<p class="main-header">🏆 Best Stocks to Consider</p>', unsafe_allow_html=True)
    st.markdown("Ranked by our composite **Investment Score** (valuation + quality + growth + momentum).")
    st.info("⚠️ This is an educational scoring model — **not financial advice**. Always do your own research.")

    with st.spinner("Scoring all Nifty 50 stocks..."):
        quotes = get_multiple_quotes(NIFTY50)

    if not quotes:
        st.error("Could not fetch data.")
        st.stop()

    df = pd.DataFrame(quotes)
    df["Score"] = df.apply(lambda r: score_stock(r), axis=1)
    df = df.sort_values("Score", ascending=False)

    st.subheader("🥇 Top 10 Ranked Stocks")
    top10 = df.head(10).copy()
    fig = go.Figure(go.Bar(
        x=top10["Score"], y=top10["symbol"], orientation="h",
        marker=dict(color=top10["Score"], colorscale=[[0, "#ff1744"], [0.5, "#ffeb3b"], [1, "#00c853"]], cmin=30, cmax=90),
        text=[f"{s:.1f}" for s in top10["Score"]], textposition="outside"
    ))
    fig.update_layout(height=420, yaxis=dict(autorange="reversed"), margin=dict(l=90, t=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    show = top10[["symbol", "name", "price", "change_pct", "pe", "roe", "debt_to_equity",
                  "profit_margins", "sector", "Score"]].copy()
    show.columns = ["Symbol", "Name", "Price (₹)", "Change %", "P/E", "ROE", "D/E",
                    "Profit Margin", "Sector", "Score"]
    st.dataframe(show.style.format({
        "Price (₹)": "{:.2f}", "Change %": "{:+.2f}", "P/E": "{:.1f}",
        "ROE": "{:.1%}", "D/E": "{:.1f}", "Profit Margin": "{:.1%}", "Score": "{:.1f}"
    }),
    use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📐 How the Score Works")
    st.markdown("""
    | Factor | Weight Logic |
    |--------|--------------|
    | **P/E Ratio** | Lower is better (sweet spot 10–25) |
    | **ROE** | Higher is better (>15% preferred) |
    | **Debt/Equity** | Lower is better (<70 preferred) |
    | **Profit Margin** | Higher is better (>10% preferred) |
    | **Revenue Growth** | Positive growth adds points |
    | **Momentum** | Mild positive change preferred over extreme moves |
    Score ranges from **0 – 100**. Stocks above **65** are relatively attractive on these metrics.
    """)

    st.subheader("🏭 Best Stock in Each Sector")
    sector_best = df.loc[df.groupby("sector")["Score"].idxmax()][["symbol", "sector", "Score", "price", "pe", "roe"]]
    sector_best = sector_best.sort_values("Score", ascending=False)
    st.dataframe(sector_best.rename(columns={
        "symbol": "Symbol", "sector": "Sector", "Score": "Score",
        "price": "Price", "pe": "P/E", "roe": "ROE"
    }).style.format({"Score": "{:.1f}", "Price": "{:.2f}", "P/E": "{:.1f}", "ROE": "{:.1%}"}),
    use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# PAGE: OPTION CHAIN
# ─────────────────────────────────────────────
elif page == "⛓️ Option Chain":
    st.markdown('<p class="main-header">⛓️ Option Chain</p>', unsafe_allow_html=True)
    st.markdown("Live option chain data for NSE stocks & indices (via Yahoo Finance).")

    oc_col1, oc_col2 = st.columns([2, 1])
    with oc_col1:
        oc_symbol = st.text_input("Symbol for Option Chain", value=search_symbol, key="oc_sym").upper().strip()
    with oc_col2:
        oc_exch = st.selectbox("Exchange", ["NSE", "BSE"], key="oc_exch")
    oc_full = f"{oc_symbol}.{'NS' if oc_exch == 'NSE' else 'BO'}"

    # Also allow index
    use_index = st.checkbox("Use Index (NIFTY / BANKNIFTY)", value=False)
    if use_index:
        idx_choice = st.selectbox("Index", ["^NSEI", "^NSEBANK"])
        oc_full = idx_choice
        oc_symbol = "NIFTY 50" if idx_choice == "^NSEI" else "BANK NIFTY"

    if st.button("📥 Load Option Chain", type="primary"):
        with st.spinner("Fetching available expiries..."):
            expirations = get_option_chain(oc_full)

        if not expirations:
            st.error(f"No option chain available for **{oc_symbol}**. Try a liquid F&O stock (e.g. RELIANCE, TCS, INFY, SBIN) or NIFTY.")
        else:
            st.session_state["oc_expirations"] = list(expirations)
            st.session_state["oc_symbol"] = oc_full
            st.session_state["oc_name"] = oc_symbol
            st.success(f"Found {len(expirations)} expiry dates for {oc_symbol}")

    if "oc_expirations" in st.session_state and st.session_state.get("oc_symbol") == oc_full:
        expiry = st.selectbox("Select Expiry", st.session_state["oc_expirations"])
        with st.spinner(f"Loading chain for {expiry}..."):
            calls, puts = get_option_chain_for_expiry(st.session_state["oc_symbol"], expiry)

        if calls is None or puts is None:
            st.error("Failed to load option chain for this expiry.")
        else:
            # Spot price
            spot_q = get_live_quote(st.session_state["oc_symbol"])
            spot = spot_q["price"] if spot_q else None
            if spot:
                st.metric("Spot Price", f"₹{spot:,.2f}")

            # PCR
            total_call_oi = calls["openInterest"].sum() if "openInterest" in calls.columns else 0
            total_put_oi = puts["openInterest"].sum() if "openInterest" in puts.columns else 0
            pcr = (total_put_oi / total_call_oi) if total_call_oi else 0
            pcr_color = "#00c853" if pcr > 1 else "#ff1744"
            st.markdown(f"**Put-Call Ratio (OI):** <span style='color:{pcr_color};font-size:1.3rem;font-weight:700'>{pcr:.2f}</span>  "
                        f"(Call OI: {int(total_call_oi):,} | Put OI: {int(total_put_oi):,})", unsafe_allow_html=True)

            tab_c, tab_p, tab_both = st.tabs(["📞 Calls", "📉 Puts", "📊 Combined View"])

            with tab_c:
                st.dataframe(calls.style.format({
                    "strike": "{:.1f}", "lastPrice": "{:.2f}", "bid": "{:.2f}", "ask": "{:.2f}",
                    "change": "{:+.2f}", "percentChange": "{:+.2f}", "impliedVolatility": "{:.1%}"
                }, na_rep="—"), use_container_width=True, height=450)

                # OI chart
                if "openInterest" in calls.columns and "strike" in calls.columns:
                    fig = px.bar(calls, x="strike", y="openInterest", title="Call Open Interest by Strike",
                                 color_discrete_sequence=["#00c853"])
                    if spot:
                        fig.add_vline(x=spot, line_dash="dash", line_color="yellow", annotation_text="Spot")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

            with tab_p:
                st.dataframe(puts.style.format({
                    "strike": "{:.1f}", "lastPrice": "{:.2f}", "bid": "{:.2f}", "ask": "{:.2f}",
                    "change": "{:+.2f}", "percentChange": "{:+.2f}", "impliedVolatility": "{:.1%}"
                }, na_rep="—"), use_container_width=True, height=450)

                if "openInterest" in puts.columns and "strike" in puts.columns:
                    fig = px.bar(puts, x="strike", y="openInterest", title="Put Open Interest by Strike",
                                 color_discrete_sequence=["#ff1744"])
                    if spot:
                        fig.add_vline(x=spot, line_dash="dash", line_color="yellow", annotation_text="Spot")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

            with tab_both:
                # Merge on strike for side-by-side
                if "strike" in calls.columns and "strike" in puts.columns:
                    c = calls[["strike", "lastPrice", "openInterest", "volume", "impliedVolatility"]].rename(
                        columns={"lastPrice": "Call LTP", "openInterest": "Call OI", "volume": "Call Vol", "impliedVolatility": "Call IV"})
                    p = puts[["strike", "lastPrice", "openInterest", "volume", "impliedVolatility"]].rename(
                        columns={"lastPrice": "Put LTP", "openInterest": "Put OI", "volume": "Put Vol", "impliedVolatility": "Put IV"})
                    merged = pd.merge(c, p, on="strike", how="outer").sort_values("strike")
                    st.dataframe(merged.style.format({
                        "strike": "{:.1f}", "Call LTP": "{:.2f}", "Put LTP": "{:.2f}",
                        "Call IV": "{:.1%}", "Put IV": "{:.1%}"
                    }, na_rep="—"), use_container_width=True, height=450)

                    # OI comparison
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=merged["strike"], y=merged["Call OI"], name="Call OI", marker_color="#00c853"))
                    fig.add_trace(go.Bar(x=merged["strike"], y=merged["Put OI"], name="Put OI", marker_color="#ff1744"))
                    if spot:
                        fig.add_vline(x=spot, line_dash="dash", line_color="yellow", annotation_text="Spot")
                    fig.update_layout(barmode="group", height=350, title="Call vs Put Open Interest")
                    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE: WATCHLIST & PORTFOLIO
# ─────────────────────────────────────────────
elif page == "⭐ Watchlist & Portfolio":
    st.markdown('<p class="main-header">⭐ Watchlist & Portfolio</p>', unsafe_allow_html=True)

    tab_w, tab_p = st.tabs(["👁️ Watchlist", "💼 Portfolio Tracker"])

    # ── WATCHLIST ──
    with tab_w:
        watchlist = load_json(WATCHLIST_FILE, [])

        st.subheader("Add to Watchlist")
        w1, w2, w3 = st.columns([2, 1, 1])
        with w1:
            add_sym = st.text_input("Symbol", value="", key="wl_add").upper().strip()
        with w2:
            add_exch = st.selectbox("Exchange", ["NSE", "BSE"], key="wl_exch")
        with w3:
            st.write("")
            st.write("")
            if st.button("➕ Add", key="wl_btn"):
                full = f"{add_sym}.{'NS' if add_exch == 'NSE' else 'BO'}"
                if full not in watchlist and add_sym:
                    watchlist.append(full)
                    save_json(WATCHLIST_FILE, watchlist)
                    st.success(f"Added {add_sym}")
                    st.rerun()
                elif full in watchlist:
                    st.warning("Already in watchlist")

        if watchlist:
            st.subheader(f"Your Watchlist ({len(watchlist)} stocks)")
            with st.spinner("Fetching live prices..."):
                wl_quotes = get_multiple_quotes(watchlist)

            if wl_quotes:
                wl_df = pd.DataFrame(wl_quotes)
                wl_df["Score"] = wl_df.apply(lambda r: score_stock(r), axis=1)
                display = wl_df[["symbol", "name", "price", "change_pct", "pe", "sector", "Score"]].copy()
                display.columns = ["Symbol", "Name", "Price (₹)", "Change %", "P/E", "Sector", "Score"]
                st.dataframe(display.style.format({
                    "Price (₹)": "{:.2f}", "Change %": "{:+.2f}", "P/E": "{:.1f}", "Score": "{:.1f}"
                }), use_container_width=True, hide_index=True)

            st.markdown("#### Remove from Watchlist")
            remove_sym = st.selectbox("Select symbol to remove", [s.replace(".NS", "").replace(".BO", "") for s in watchlist])
            if st.button("🗑️ Remove", key="wl_rm"):
                watchlist = [s for s in watchlist if remove_sym not in s]
                save_json(WATCHLIST_FILE, watchlist)
                st.success(f"Removed {remove_sym}")
                st.rerun()
        else:
            st.info("Watchlist is empty. Add stocks above.")

    # ── PORTFOLIO ──
    with tab_p:
        portfolio = load_json(PORTFOLIO_FILE, [])

        st.subheader("Add Holding")
        p1, p2, p3, p4, p5 = st.columns([2, 1, 1, 1, 1])
        with p1:
            p_sym = st.text_input("Symbol", key="pf_sym").upper().strip()
        with p2:
            p_exch = st.selectbox("Exch", ["NSE", "BSE"], key="pf_exch")
        with p3:
            p_qty = st.number_input("Qty", min_value=1, value=1, key="pf_qty")
        with p4:
            p_buy = st.number_input("Buy Price (₹)", min_value=0.01, value=100.0, key="pf_buy", format="%.2f")
        with p5:
            st.write("")
            st.write("")
            if st.button("➕ Add Holding", key="pf_add"):
                if p_sym:
                    full = f"{p_sym}.{'NS' if p_exch == 'NSE' else 'BO'}"
                    portfolio.append({
                        "symbol": full,
                        "qty": int(p_qty),
                        "buy_price": float(p_buy),
                        "added": datetime.now().strftime("%Y-%m-%d")
                    })
                    save_json(PORTFOLIO_FILE, portfolio)
                    st.success(f"Added {p_qty} × {p_sym} @ ₹{p_buy}")
                    st.rerun()

        if portfolio:
            st.subheader("Your Portfolio")
            rows = []
            total_invested = 0
            total_current = 0
            for h in portfolio:
                q = get_live_quote(h["symbol"])
                if q:
                    invested = h["qty"] * h["buy_price"]
                    current = h["qty"] * q["price"]
                    pnl = current - invested
                    pnl_pct = (pnl / invested) * 100 if invested else 0
                    total_invested += invested
                    total_current += current
                    rows.append({
                        "Symbol": q["symbol"],
                        "Name": q["name"],
                        "Qty": h["qty"],
                        "Buy Price": h["buy_price"],
                        "LTP": q["price"],
                        "Invested": invested,
                        "Current": current,
                        "P&L": pnl,
                        "P&L %": pnl_pct,
                        "Day %": q["change_pct"],
                    })

            if rows:
                pf_df = pd.DataFrame(rows)
                total_pnl = total_current - total_invested
                total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Invested", f"₹{total_invested:,.0f}")
                m2.metric("Current Value", f"₹{total_current:,.0f}")
                m3.metric("Total P&L", f"₹{total_pnl:,.0f}", f"{total_pnl_pct:+.2f}%")
                day_pnl = sum(r["Qty"] * (r["LTP"] - r["LTP"] / (1 + r["Day %"]/100) if r["Day %"] != -100 else 0) for r in rows)
                m4.metric("Day Change % (avg)", f"{pf_df['Day %'].mean():+.2f}%")

                st.dataframe(pf_df.style.format({
                    "Buy Price": "₹{:.2f}", "LTP": "₹{:.2f}",
                    "Invested": "₹{:,.0f}", "Current": "₹{:,.0f}",
                    "P&L": "₹{:+,.0f}", "P&L %": "{:+.2f}%", "Day %": "{:+.2f}%"
                }).map(lambda x: "color: #00c853" if isinstance(x, (int, float)) and x > 0 else (
                    "color: #ff1744" if isinstance(x, (int, float)) and x < 0 else ""), subset=["P&L", "P&L %"]),
                use_container_width=True, hide_index=True)

                # Allocation pie
                fig = px.pie(pf_df, values="Current", names="Symbol", title="Portfolio Allocation")
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Remove Holding")
            rm_idx = st.selectbox("Select holding to remove",
                                  [f"{h['symbol'].replace('.NS','').replace('.BO','')} × {h['qty']} @ ₹{h['buy_price']}" for h in portfolio],
                                  key="pf_rm_sel")
            if st.button("🗑️ Remove Holding", key="pf_rm"):
                idx = [f"{h['symbol'].replace('.NS','').replace('.BO','')} × {h['qty']} @ ₹{h['buy_price']}" for h in portfolio].index(rm_idx)
                portfolio.pop(idx)
                save_json(PORTFOLIO_FILE, portfolio)
                st.success("Removed")
                st.rerun()
        else:
            st.info("Portfolio is empty. Add holdings above.")


# ─────────────────────────────────────────────
# PAGE: CUSTOM SCREENER
# ─────────────────────────────────────────────
elif page == "🔍 Custom Screener":
    st.markdown('<p class="main-header">🔍 Custom Screener</p>', unsafe_allow_html=True)
    st.markdown("Build your own stock filter on Nifty 50 using fundamental & technical criteria.")

    with st.spinner("Loading Nifty 50 data for screening..."):
        quotes = get_multiple_quotes(NIFTY50)

    if not quotes:
        st.error("Could not fetch data.")
        st.stop()

    df = pd.DataFrame(quotes)
    df["Score"] = df.apply(lambda r: score_stock(r), axis=1)

    st.subheader("Set Your Filters")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Valuation**")
        pe_min, pe_max = st.slider("P/E Range", 0.0, 100.0, (0.0, 40.0), 1.0)
        pb_min, pb_max = st.slider("P/B Range", 0.0, 20.0, (0.0, 10.0), 0.5)
        score_min = st.slider("Min Investment Score", 0, 100, 40)

    with c2:
        st.markdown("**Quality & Leverage**")
        roe_min = st.slider("Min ROE (%)", -20.0, 50.0, 0.0, 1.0) / 100
        de_max = st.slider("Max Debt/Equity", 0.0, 300.0, 150.0, 5.0)
        pm_min = st.slider("Min Profit Margin (%)", -20.0, 50.0, 0.0, 1.0) / 100

    with c3:
        st.markdown("**Momentum & Growth**")
        chg_min, chg_max = st.slider("Day Change % Range", -15.0, 15.0, (-15.0, 15.0), 0.5)
        sectors = st.multiselect("Sectors (leave empty = all)", sorted(df["sector"].dropna().unique().tolist()))
        beta_max = st.slider("Max Beta", 0.0, 3.0, 3.0, 0.1)

    # Apply filters
    mask = pd.Series([True] * len(df))
    if pe_min > 0 or pe_max < 100:
        mask &= df["pe"].isna() | ((df["pe"] >= pe_min) & (df["pe"] <= pe_max))
    if pb_min > 0 or pb_max < 20:
        mask &= df["pb"].isna() | ((df["pb"] >= pb_min) & (df["pb"] <= pb_max))
    mask &= df["Score"] >= score_min
    mask &= df["roe"].isna() | (df["roe"] >= roe_min)
    mask &= df["debt_to_equity"].isna() | (df["debt_to_equity"] <= de_max)
    mask &= df["profit_margins"].isna() | (df["profit_margins"] >= pm_min)
    mask &= (df["change_pct"] >= chg_min) & (df["change_pct"] <= chg_max)
    if sectors:
        mask &= df["sector"].isin(sectors)
    mask &= df["beta"].isna() | (df["beta"] <= beta_max)

    filtered = df[mask].sort_values("Score", ascending=False)

    st.markdown(f"### Results: **{len(filtered)}** stocks matched")
    if filtered.empty:
        st.warning("No stocks match your criteria. Try relaxing some filters.")
    else:
        show = filtered[["symbol", "name", "price", "change_pct", "pe", "pb", "roe",
                         "debt_to_equity", "profit_margins", "beta", "sector", "Score"]].copy()
        show.columns = ["Symbol", "Name", "Price", "Change %", "P/E", "P/B", "ROE",
                        "D/E", "Profit Margin", "Beta", "Sector", "Score"]
        st.dataframe(show.style.format({
            "Price": "{:.2f}", "Change %": "{:+.2f}", "P/E": "{:.1f}", "P/B": "{:.2f}",
            "ROE": "{:.1%}", "D/E": "{:.1f}", "Profit Margin": "{:.1%}", "Beta": "{:.2f}", "Score": "{:.1f}"
        }),
        use_container_width=True, hide_index=True)

        # Quick chart of top results
        if len(filtered) >= 2:
            fig = px.scatter(filtered.head(20), x="pe", y="roe", size="Score", color="sector",
                             hover_name="symbol", title="P/E vs ROE (bubble size = Score)",
                             labels={"pe": "P/E", "roe": "ROE"})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE: ALERTS
# ─────────────────────────────────────────────
elif page == "🔔 Alerts":
    st.markdown('<p class="main-header">🔔 Price Alerts</p>', unsafe_allow_html=True)
    st.markdown("Set price alerts. When you open this page, triggered alerts are highlighted. Optionally send email.")

    alerts = load_json(ALERTS_FILE, [])

    # ── Create Alert ──
    st.subheader("Create New Alert")
    a1, a2, a3, a4 = st.columns([2, 1, 1, 1])
    with a1:
        a_sym = st.text_input("Symbol", key="al_sym").upper().strip()
    with a2:
        a_exch = st.selectbox("Exch", ["NSE", "BSE"], key="al_exch")
    with a3:
        a_cond = st.selectbox("Condition", ["Above", "Below"], key="al_cond")
    with a4:
        a_price = st.number_input("Target Price (₹)", min_value=0.01, value=1000.0, format="%.2f", key="al_price")

    a_note = st.text_input("Note (optional)", key="al_note")

    if st.button("➕ Create Alert", type="primary"):
        if a_sym:
            full = f"{a_sym}.{'NS' if a_exch == 'NSE' else 'BO'}"
            alerts.append({
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "symbol": full,
                "condition": a_cond,
                "target": float(a_price),
                "note": a_note,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "triggered": False,
            })
            save_json(ALERTS_FILE, alerts)
            st.success(f"Alert set: {a_sym} {a_cond} ₹{a_price}")
            st.rerun()

    st.markdown("---")

    # ── Check Alerts ──
    st.subheader("Active Alerts")
    if not alerts:
        st.info("No alerts set yet.")
    else:
        triggered_list = []
        for al in alerts:
            q = get_live_quote(al["symbol"])
            if not q:
                continue
            ltp = q["price"]
            is_triggered = (al["condition"] == "Above" and ltp >= al["target"]) or \
                           (al["condition"] == "Below" and ltp <= al["target"])
            al["triggered"] = is_triggered
            al["ltp"] = ltp
            if is_triggered:
                triggered_list.append(al)

        save_json(ALERTS_FILE, alerts)  # persist triggered status

        for al in alerts:
            status = "🔴 TRIGGERED" if al.get("triggered") else "🟢 Watching"
            color = "#ff1744" if al.get("triggered") else "#00c853"
            ltp_str = f"₹{al.get('ltp', '—')}" if al.get("ltp") else "—"
            st.markdown(f"""
            <div class="alert-box">
                <b>{al['symbol'].replace('.NS','').replace('.BO','')}</b> &nbsp;
                {al['condition']} <b>₹{al['target']}</b> &nbsp;|&nbsp;
                LTP: {ltp_str} &nbsp;|&nbsp;
                <span style="color:{color}">{status}</span><br>
                <small style="color:#888">{al.get('note','')} · Created {al.get('created','')}</small>
            </div>
            """, unsafe_allow_html=True)

        if triggered_list:
            st.warning(f"⚠️ {len(triggered_list)} alert(s) have been triggered!")

        # Remove alert
        st.markdown("#### Delete Alert")
        del_opts = [f"{a['symbol'].replace('.NS','').replace('.BO','')} {a['condition']} ₹{a['target']} ({a['id']})" for a in alerts]
        del_sel = st.selectbox("Select alert to delete", del_opts, key="al_del")
        if st.button("🗑️ Delete Alert"):
            del_id = del_sel.split("(")[-1].rstrip(")")
            alerts = [a for a in alerts if a["id"] != del_id]
            save_json(ALERTS_FILE, alerts)
            st.success("Deleted")
            st.rerun()

    # ── Email Settings ──
    st.markdown("---")
    st.subheader("📧 Email Notification (Optional)")
    st.caption("Configure SMTP to receive email when alerts trigger. Uses your own Gmail / email account.")

    with st.expander("SMTP Settings"):
        smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
        smtp_port = st.number_input("Port", value=587)
        smtp_user = st.text_input("Email (from)")
        smtp_pass = st.text_input("App Password", type="password",
                                  help="For Gmail: create an App Password at myaccount.google.com/apppasswords")
        to_email = st.text_input("Send alerts to", value=smtp_user)

        if st.button("📤 Send Test Email"):
            if smtp_user and smtp_pass and to_email:
                ok = send_email_alert(
                    to_email, "Test Alert — Indian Stock Analyzer",
                    f"This is a test email from your Stock Analyzer.\nTime: {datetime.now()}",
                    smtp_server, int(smtp_port), smtp_user, smtp_pass
                )
                if ok:
                    st.success("Test email sent successfully!")
            else:
                st.warning("Fill in email credentials first.")

        if st.button("📨 Email All Triggered Alerts Now") and triggered_list:
            if smtp_user and smtp_pass and to_email:
                body_lines = [f"Triggered Alerts — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
                for al in triggered_list:
                    body_lines.append(
                        f"• {al['symbol'].replace('.NS','').replace('.BO','')} "
                        f"{al['condition']} ₹{al['target']} | LTP: ₹{al.get('ltp','—')} | {al.get('note','')}"
                    )
                ok = send_email_alert(
                    to_email, f"🔔 {len(triggered_list)} Stock Alert(s) Triggered",
                    "\n".join(body_lines),
                    smtp_server, int(smtp_port), smtp_user, smtp_pass
                )
                if ok:
                    st.success(f"Emailed {len(triggered_list)} triggered alert(s)!")
            else:
                st.warning("Configure SMTP settings first.")


# ─────────────────────────────────────────────
# PAGE: ABOUT
# ─────────────────────────────────────────────

elif page == "📰 News":
    st.markdown(f"""
    <div class="brand-header">
      <div class="brand-logo">◈</div>
      <div class="brand-text">
        <h1>Market & Stock News</h1>
        <p>Economic · Markets · Company-specific headlines</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    nt1, nt2 = st.tabs(["🌐 Market News", "🏢 Stock-specific News"])

    with nt1:
        st.caption("Headlines aggregated from major Indian stocks & Nifty-related coverage.")
        with st.spinner("Fetching latest market news..."):
            market_items = get_market_news_bundle()
        render_news_cards(market_items, "Could not load market news. Try Refresh.")

    with nt2:
        c1, c2 = st.columns([3, 1])
        with c1:
            news_sym = st.text_input("Company symbol", value=search_symbol, key="news_sym").upper().strip()
        with c2:
            news_ex = st.selectbox("Exchange", ["NSE", "BSE"], key="news_ex")
        full_ns = f"{news_sym}.{ 'NS' if news_ex == 'NSE' else 'BO'}"
        if st.button("Load company news", type="primary", key="load_co_news") or news_sym:
            with st.spinner(f"Fetching news for {news_sym}..."):
                co_items = get_stock_news(full_ns, limit=15)
            st.markdown(f"#### News related to **{news_sym}**")
            render_news_cards(co_items, f"No recent news found for {news_sym}. Try another symbol.")


elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ Settings (Admin)</p>', unsafe_allow_html=True)
    s = get_settings()
    tg, tu, tp = st.tabs(["General", "Users", "Password"])
    with tg:
        an = st.text_input("App Name", value=s.get("app_name", "StockVista Pro"))
        td = st.number_input("Trial days", min_value=1, max_value=90, value=int(s.get("trial_days", 7)))
        pp = st.text_input("Price label", value=s.get("payment_price", "Rs 499"))
        pl = st.text_input("Payment link", value=s.get("payment_link", "https://"))
        if st.button("Save Settings", type="primary"):
            s.update({"app_name": an, "trial_days": int(td), "payment_price": pp, "payment_link": pl})
            save_settings(s)
            st.success("Saved")
            st.rerun()
    with tu:
        users = get_users()
        import pandas as _pd
        rows = [{"Username": u, "Role": users[u].get("role"), "Paid": users[u].get("paid"),
                 "Trial left": trial_days_left(users[u], s) if users[u].get("role") != "admin" else "inf",
                 "Created": users[u].get("created")} for u in users]
        st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True)
        ulist = [u for u in users if users[u].get("role") != "admin"]
        if ulist:
            sel = st.selectbox("User", ulist)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Mark PAID", type="primary"):
                    users[sel]["paid"] = True
                    save_users(users)
                    st.success("Done")
                    st.rerun()
            with c2:
                if st.button("Mark unpaid"):
                    users[sel]["paid"] = False
                    save_users(users)
                    st.rerun()
            with c3:
                if st.button("Reset trial"):
                    users[sel]["trial_start"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
                    users[sel]["paid"] = False
                    save_users(users)
                    st.success("Trial reset")
                    st.rerun()
        else:
            st.info("No regular users yet.")
    with tp:
        with st.form("pwd_form"):
            old = st.text_input("Current password", type="password")
            n1 = st.text_input("New password", type="password")
            n2 = st.text_input("Confirm", type="password")
            if st.form_submit_button("Update password", type="primary"):
                users = get_users()
                me = users.get(_user["username"])
                if not me or not _verify_password(old, me["password_hash"], me["salt"]):
                    st.error("Wrong current password")
                elif n1 != n2:
                    st.error("Passwords do not match")
                elif len(n1) < 4:
                    st.error("Too short")
                else:
                    ph, salt = _hash_password(n1)
                    users[_user["username"]]["password_hash"] = ph
                    users[_user["username"]]["salt"] = salt
                    save_users(users)
                    st.success("Password updated")

else:
    st.markdown("""
    <div class="brand-header">
      <div class="brand-logo">◈</div>
      <div class="brand-text">
        <h1>About</h1>
        <p>Your smart companion for Indian markets</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ### What you can do

    - **Dashboard** — Live market overview and Nifty 50 movers  
    - **Trending** — Momentum, volume, value and quality screens  
    - **Research** — Company ratios, charts and related news  
    - **Best Stocks** — Ranked ideas based on a research score  
    - **News** — Market and company headlines  
    - **Option Chain** — Calls, puts and open interest  
    - **Watchlist & Portfolio** — Track stocks and holdings with live P&L  
    - **Screener** — Filter stocks by your own criteria  
    - **Alerts** — Price alerts when levels are crossed  

    ---

    **Important**  
    This platform is for research and learning only. It is **not** investment advice.  
    Always do your own research before making any financial decision.
    """)
