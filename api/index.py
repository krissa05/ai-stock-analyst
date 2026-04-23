from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import numpy as np
import os, re
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="AI Stock Analyst API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AnalyzeRequest(BaseModel):
    ticker: str

class ChatRequest(BaseModel):
    message: str
    ticker: Optional[str] = None
    history: Optional[List[dict]] = []

def safe_float(series, default=0.0):
    try:
        val = series.iloc[-1]
        f = float(val)
        return default if (pd.isna(val) or np.isinf(f)) else round(f, 2)
    except:
        return default

def clean_series(lst, decimals=2):
    """Replace NaN/Inf with None — raw .tolist() produces invalid JSON for some stocks."""
    import math
    result = []
    for v in lst:
        try:
            f = float(v)
            result.append(None if (math.isnan(f) or math.isinf(f)) else round(f, decimals))
        except:
            result.append(None)
    return result

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_bollinger(prices, period=20):
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return sma + (std * 2), sma, sma - (std * 2)

def calculate_stochastic(high, low, close, k=14, d=3):
    lowest_low   = low.rolling(k).min()
    highest_high = high.rolling(k).max()
    k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_adx(high, low, close, period=14):
    try:
        tr = pd.concat([high - low,
                        (high - close.shift()).abs(),
                        (low  - close.shift()).abs()], axis=1).max(axis=1)
        dm_plus  = high.diff()
        dm_minus = -low.diff()
        dm_plus[dm_plus < 0]   = 0
        dm_minus[dm_minus < 0] = 0
        dm_plus[dm_plus < dm_minus]   = 0
        dm_minus[dm_minus < dm_plus]  = 0
        atr14   = tr.rolling(period).mean()
        di_plus  = 100 * dm_plus.rolling(period).mean() / atr14
        di_minus = 100 * dm_minus.rolling(period).mean() / atr14
        dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus)
        adx = dx.rolling(period).mean()
        return adx, di_plus, di_minus
    except:
        return pd.Series([25]*len(close), index=close.index), pd.Series([0]*len(close), index=close.index), pd.Series([0]*len(close), index=close.index)

def calculate_vwap(high, low, close, volume):
    typical = (high + low + close) / 3
    return (typical * volume).cumsum() / volume.cumsum()

def calculate_obv(close, volume):
    direction = close.diff().apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
    return (direction * volume).cumsum()

def get_fundamental_score(info):
    score = 0
    try:
        if info.get("trailingPE")    and 0 < info["trailingPE"] < 30:     score += 1
        if info.get("priceToBook")   and 0 < info["priceToBook"] < 3:     score += 1
        if info.get("returnOnEquity") and info["returnOnEquity"] > 0.15:  score += 1
        if info.get("debtToEquity")  and info["debtToEquity"] < 1:        score += 1
        if info.get("profitMargins") and info["profitMargins"] > 0.1:     score += 1
        if info.get("revenueGrowth") and info["revenueGrowth"] > 0.05:    score += 1
        if info.get("trailingEps")   and info["trailingEps"] > 0:         score += 1
        if info.get("dividendYield") and info["dividendYield"] > 0:       score += 1
    except:
        pass
    return score

def resolve_ticker(raw: str):
    """
    Try multiple ticker variants and return (ticker_str, yf.Ticker, hist_df).
    Handles NSE (.NS) -> BSE (.BO) fallback, and common yfinance quirks.
    """
    raw = raw.strip().upper()
    base = raw.split(".")[0]
    suffix = raw.split(".")[-1] if "." in raw else ""

    # Build candidate list in priority order
    if suffix == "NS":
        candidates = [raw, base + ".BO", base]
    elif suffix == "BO":
        candidates = [raw, base + ".NS", base]
    elif suffix in ("KS", "T", "L"):
        candidates = [raw]
    else:
        candidates = [raw, base + ".NS", base + ".BO"]

    for candidate in candidates:
        try:
            t = yf.Ticker(candidate)
            hist = t.history(period="6mo", auto_adjust=True)
            if hist.empty:
                hist = t.history(period="3mo", auto_adjust=True)
            if not hist.empty:
                return candidate, t, hist
        except Exception:
            continue

    tried = ", ".join(candidates)
    raise ValueError(
        f"No data found for \'{raw}\'. Tried: {tried}. "
        f"Make sure the ticker is correct — NSE stocks need .NS (e.g. ZOMATO.NS), "
        f"US stocks use bare ticker (e.g. AAPL), Korean stocks use .KS (e.g. 005930.KS)."
    )


def generate_analysis(ticker: str) -> dict:
    ticker_resolved, t, hist = resolve_ticker(ticker)
    ticker = ticker_resolved  # use whichever variant actually returned data

    # Use fast_info for the most accurate current price
    current_price = None
    try:
        fi = t.fast_info
        current_price = round(float(fi.last_price), 2)
    except:
        pass
    if not current_price:
        current_price = safe_float(hist["Close"].dropna())

    close  = hist["Close"].dropna()
    high   = hist["High"].dropna()
    low    = hist["Low"].dropna()
    volume = hist["Volume"].dropna()

    if len(close) < 2:
        raise ValueError(f"Not enough data for '{ticker}'.")

    # Override last close with real-time price
    close.iloc[-1] = current_price

    info = {}
    try:
        info = t.info or {}
    except:
        pass

    # 10-day change using actual prices
    hist_10d = t.history(period="10d", auto_adjust=True)
    try:
        c10 = hist_10d["Close"].dropna()
        change_10d = round((float(c10.iloc[-1]) - float(c10.iloc[0])) / float(c10.iloc[0]) * 100, 2) if len(c10) >= 2 else 0.0
    except:
        change_10d = 0.0

    # 1-day change
    try:
        prev_close = float(close.iloc[-2])
        change_1d  = round((current_price - prev_close) / prev_close * 100, 2)
    except:
        change_1d  = 0.0

    # ── Indicators ──
    rsi_val = safe_float(calculate_rsi(close), default=50.0) if len(close) >= 15 else 50.0

    macd_val = signal_val = hist_val = 0.0
    if len(close) >= 26:
        m, s, h = calculate_macd(close)
        macd_val   = safe_float(m, default=0.0)
        signal_val = safe_float(s, default=0.0)
        hist_val   = safe_float(h, default=0.0)

    bb_upper_val = current_price * 1.02
    bb_lower_val = current_price * 0.98
    bb_mid_val   = current_price
    if len(close) >= 20:
        bu, bm, bl = calculate_bollinger(close)
        bb_upper_val = safe_float(bu, default=current_price * 1.02)
        bb_mid_val   = safe_float(bm, default=current_price)
        bb_lower_val = safe_float(bl, default=current_price * 0.98)

    ma5  = safe_float(close.rolling(min(5,  len(close))).mean(), default=current_price)
    ma10 = safe_float(close.rolling(min(10, len(close))).mean(), default=current_price)
    ma20 = safe_float(close.rolling(min(20, len(close))).mean(), default=current_price)
    ma50 = safe_float(close.rolling(min(50, len(close))).mean(), default=current_price)

    stoch_k = stoch_d = 50.0
    if len(close) >= 14:
        sk, sd = calculate_stochastic(high, low, close)
        stoch_k = safe_float(sk, default=50.0)
        stoch_d = safe_float(sd, default=50.0)

    atr_val = 0.0
    if len(close) >= 14:
        atr_val = safe_float(calculate_atr(high, low, close), default=0.0)

    adx_val = di_plus = di_minus = 0.0
    if len(close) >= 28:
        adx_s, dip_s, dim_s = calculate_adx(high, low, close)
        adx_val  = safe_float(adx_s,  default=25.0)
        di_plus  = safe_float(dip_s,  default=0.0)
        di_minus = safe_float(dim_s,  default=0.0)

    vwap_val = 0.0
    try:
        vwap_s   = calculate_vwap(high, low, close, volume)
        vwap_val = safe_float(vwap_s, default=0.0)
    except:
        pass

    obv_val = 0.0
    try:
        obv_s   = calculate_obv(close, volume)
        obv_val = round(float(obv_s.iloc[-1]) / 1e6, 2)  # in millions
    except:
        pass

    avg_vol = float(volume.rolling(min(20, len(volume))).mean().iloc[-1]) if len(volume) >= 2 else 0
    cur_vol = float(volume.iloc[-1]) if len(volume) >= 1 else 0
    vol_spike = cur_vol > avg_vol * 1.5 if avg_vol > 0 else False
    vol_ratio = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

    tail = close.tail(20)
    support    = round(float(tail.min()), 2)
    resistance = round(float(tail.max()), 2)

    # ATR-based stop loss (more accurate)
    atr_sl     = round(current_price - (atr_val * 1.5), 2) if atr_val > 0 else round(current_price * 0.99, 2)
    stop_loss  = max(atr_sl, support * 0.99)
    stop_loss  = round(stop_loss, 2)
    tp1        = round(current_price + (current_price - stop_loss) * 1.5, 2)
    tp2        = round(current_price + (current_price - stop_loss) * 3.0, 2)
    rr1        = round((tp1 - current_price) / (current_price - stop_loss), 2) if current_price != stop_loss else 0
    rr2        = round((tp2 - current_price) / (current_price - stop_loss), 2) if current_price != stop_loss else 0

    fund_score = get_fundamental_score(info)

    # ── Verdict ──
    bull = bear = 0
    if rsi_val < 30:            bull += 2
    elif rsi_val > 70:          bear += 2
    if macd_val > signal_val:   bull += 1
    else:                       bear += 1
    if hist_val > 0:            bull += 1
    else:                       bear += 1
    if current_price > ma20 > ma50: bull += 2
    elif current_price < ma20 < ma50: bear += 2
    if current_price < bb_lower_val: bull += 1
    elif current_price > bb_upper_val: bear += 1
    if stoch_k < 20:            bull += 1
    elif stoch_k > 80:          bear += 1
    if adx_val > 25 and di_plus > di_minus: bull += 1
    elif adx_val > 25 and di_minus > di_plus: bear += 1
    if current_price > vwap_val and vwap_val > 0: bull += 1
    else:                       bear += 1
    if vol_spike and macd_val > signal_val: bull += 1
    elif vol_spike:             bear += 1
    if fund_score >= 5:         bull += 1
    elif fund_score <= 2:       bear += 1

    confidence = "HIGH" if abs(bull - bear) >= 5 else "MEDIUM" if abs(bull - bear) >= 3 else "LOW"
    verdict    = "BUY" if bull > bear else "SELL" if bear > bull else "HOLD"
    bias       = "BULLISH" if bull > bear else "BEARISH" if bear > bull else "NEUTRAL"

    # ── OHLCV chart data (last 60 days) ──
    chart_data = []
    h60 = hist.tail(60)
    for idx, row in h60.iterrows():
        chart_data.append({
            "date":   idx.strftime("%Y-%m-%d"),
            "open":   round(float(row["Open"]),   2),
            "high":   round(float(row["High"]),   2),
            "low":    round(float(row["Low"]),    2),
            "close":  round(float(row["Close"]),  2),
            "volume": int(row["Volume"]),
        })

    # ── Indicator series for charts (last 60 days) ──
    # clean_series strips NaN/Inf — raw .tolist() breaks JSON for new/illiquid stocks
    rsi_series   = clean_series(calculate_rsi(close).tail(60))
    macd_series  = clean_series(calculate_macd(close)[0].tail(60)) if len(close)>=26 else []
    sig_series   = clean_series(calculate_macd(close)[1].tail(60)) if len(close)>=26 else []
    hist_series  = clean_series(calculate_macd(close)[2].tail(60)) if len(close)>=26 else []
    vol_series   = clean_series(volume.tail(60), decimals=0)
    ma20_series  = clean_series(close.rolling(20).mean().tail(60))
    ma50_series  = clean_series(close.rolling(50).mean().tail(60))
    bbu_series   = clean_series(calculate_bollinger(close)[0].tail(60)) if len(close)>=20 else []
    bbl_series   = clean_series(calculate_bollinger(close)[2].tail(60)) if len(close)>=20 else []

    return {
        "ticker": ticker, "name": info.get("longName", ticker),
        "price": current_price, "change_1d": change_1d, "change_10d": change_10d,
        "verdict": verdict, "bias": bias, "confidence": confidence,
        "rsi": rsi_val, "macd": macd_val, "signal": signal_val, "histogram": hist_val,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma50": ma50,
        "bb_upper": bb_upper_val, "bb_mid": bb_mid_val, "bb_lower": bb_lower_val,
        "stoch_k": stoch_k, "stoch_d": stoch_d,
        "atr": round(atr_val, 2), "adx": round(adx_val, 2),
        "di_plus": round(di_plus, 2), "di_minus": round(di_minus, 2),
        "vwap": round(vwap_val, 2), "obv": obv_val,
        "support": support, "resistance": resistance,
        "entry": current_price, "sl": stop_loss, "tp1": tp1, "tp2": tp2,
        "rr1": rr1, "rr2": rr2, "fund_score": fund_score,
        "vol_spike": vol_spike, "vol_ratio": vol_ratio,
        "avg_volume": round(avg_vol, 0), "cur_volume": round(cur_vol, 0),
        "bull_signals": bull, "bear_signals": bear,
        "chart_data": chart_data,
        "rsi_series": rsi_series, "macd_series": macd_series,
        "sig_series": sig_series, "hist_series": hist_series,
        "vol_series": vol_series, "ma20_series": ma20_series,
        "ma50_series": ma50_series, "bbu_series": bbu_series, "bbl_series": bbl_series,
    }

def extract_ticker(text):
    matches = re.findall(r'\b([A-Z]{2,10}(?:\.NS|\.BSE)?)\b', text.upper())
    skip = {"THE","AND","FOR","RSI","MACD","BUY","SELL","HOW","WHAT","WHY","WHO",
            "GIVE","SHOW","TELL","FULL","JUST","GET","SET","USE","CAN","ARE","THIS",
            "THAT","FROM","WITH","STOP","LOSS","RISK","GOOD","HIGH","LOW","NSE",
            "BSE","SEBI","SMA","EMA","ANALYZE","ANALYSIS","TRADE","SETUP","TREND",
            "ATR","ADX","VWAP","OBV","STOCH","BOLLINGER","VOLUME","CHART"}
    for m in matches:
        base = m.split(".")[0]
        if base not in skip and len(base) >= 2:
            return m
    return None

def generate_chat_reply(message, ticker, data):
    msg = message.lower()

    if "rsi" in msg and data is None:
        return ("**RSI (Relative Strength Index)** ranges 0–100.\n\n"
                "- **< 30** → Oversold → Potential BUY 🟢\n"
                "- **> 70** → Overbought → Potential SELL 🔴\n"
                "- **40–60** → Neutral zone\n\nBest combined with MACD and MA.")

    if "macd" in msg and data is None:
        return ("**MACD** = 12 EMA − 26 EMA | Signal = 9 EMA of MACD\n\n"
                "- MACD crosses *above* Signal → **BUY** 🟢\n"
                "- MACD crosses *below* Signal → **SELL** 🔴\n"
                "- Histogram above zero → bullish momentum")

    if "stop loss" in msg and data is None:
        return ("**Stop Loss** limits downside risk.\n\n"
                "- Intraday: 1–2% below entry\n- Swing: ATR × 1.5 below entry\n"
                "- Or just below nearest support\n\n⚠ Never skip it!")

    if "risk" in msg and "reward" in msg and data is None:
        return ("**R:R Ratio** = profit potential ÷ risk\n\n"
                "- **1:1.5** → Minimum ✅\n- **1:2+** → Good ✅\n- **1:3+** → Excellent ✅\n"
                "- **< 1:1** → Avoid ❌")

    if "atr" in msg and data is None:
        return ("**ATR (Average True Range)** measures volatility.\n\n"
                "- Higher ATR = more volatile stock\n"
                "- Use ATR × 1.5 for stop loss placement\n"
                "- Low ATR = quiet stock, breakout may come")

    if "adx" in msg and data is None:
        return ("**ADX (Average Directional Index)** measures trend strength.\n\n"
                "- **ADX < 20** → No trend, sideways\n"
                "- **ADX 20–40** → Moderate trend\n"
                "- **ADX > 40** → Strong trend\n\nDoes NOT tell direction — use +DI/-DI for that.")

    if "vwap" in msg and data is None:
        return ("**VWAP (Volume Weighted Average Price)** = fair value for the day.\n\n"
                "- Price **above** VWAP → Bullish bias 🟢\n"
                "- Price **below** VWAP → Bearish bias 🔴\n"
                "- Used heavily by institutional traders")

    if "stoch" in msg and data is None:
        return ("**Stochastic Oscillator** measures momentum (0–100).\n\n"
                "- **< 20** → Oversold → BUY signal 🟢\n"
                "- **> 80** → Overbought → SELL signal 🔴\n"
                "- %K crossing above %D → bullish crossover")

    if data is None:
        return ("I can analyze any NSE, BSE, or US stock with **10+ indicators**!\n\n"
                "Try: *Analyze RELIANCE.NS* or *Is TCS.NS a buy?*\n\n"
                "I compute: RSI · MACD · Bollinger · Stochastic · ATR · ADX · VWAP · OBV + charts 📊")

    d    = data
    sym  = d["ticker"]
    p    = d["price"]
    icon = "🟢" if d["verdict"] == "BUY" else "🔴" if d["verdict"] == "SELL" else "🟡"

    if any(w in msg for w in ["analyze","analysis","full","trade setup","verdict","technical"]):
        trend_ma = ("uptrend ✅" if p > d["ma20"] > d["ma50"]
                    else "downtrend ❌" if p < d["ma20"] < d["ma50"] else "mixed ↔")
        return (
            f"## {sym} — Full Technical Analysis\n\n"
            f"**Price:** ₹{p} | **1d:** {'+' if d['change_1d']>=0 else ''}{d['change_1d']}% | **10d:** {'+' if d['change_10d']>=0 else ''}{d['change_10d']}%\n\n"
            f"---\n\n"
            f"**📊 Momentum Indicators:**\n"
            f"- RSI (14): **{d['rsi']}** — {'oversold 🟢' if d['rsi']<30 else 'overbought 🔴' if d['rsi']>70 else 'neutral'}\n"
            f"- MACD: **{d['macd']}** vs Signal **{d['signal']}** → {'Bullish ↑' if d['macd']>d['signal'] else 'Bearish ↓'}\n"
            f"- Stochastic %K: **{d['stoch_k']}** | %D: **{d['stoch_d']}** — {'oversold 🟢' if d['stoch_k']<20 else 'overbought 🔴' if d['stoch_k']>80 else 'neutral'}\n\n"
            f"**📈 Trend Indicators:**\n"
            f"- MA20: ₹{d['ma20']} | MA50: ₹{d['ma50']} → {trend_ma}\n"
            f"- ADX: **{d['adx']}** ({'Strong' if d['adx']>40 else 'Moderate' if d['adx']>20 else 'Weak'} trend) | +DI: {d['di_plus']} | -DI: {d['di_minus']}\n"
            f"- Bollinger: Upper ₹{d['bb_upper']} | Mid ₹{d['bb_mid']} | Lower ₹{d['bb_lower']}\n"
            f"- VWAP: ₹{d['vwap']} → price is **{'above' if p>d['vwap'] else 'below'}** VWAP\n\n"
            f"**📦 Volume:**\n"
            f"- Volume ratio: **{d['vol_ratio']}x** avg {'⚡ Spike!' if d['vol_spike'] else ''}\n"
            f"- OBV: {d['obv']}M | ATR: ₹{d['atr']}\n\n"
            f"**🎯 Trade Setup:**\n"
            f"- Entry: ₹{d['entry']}\n"
            f"- Stop Loss: ₹{d['sl']} (ATR-based)\n"
            f"- Target 1: ₹{d['tp1']} (R:R 1:{d['rr1']})\n"
            f"- Target 2: ₹{d['tp2']} (R:R 1:{d['rr2']})\n"
            f"- Support: ₹{d['support']} | Resistance: ₹{d['resistance']}\n\n"
            f"**🏦 Fundamentals:** {d['fund_score']}/8\n\n"
            f"**{icon} Verdict: {d['verdict']}** ({d['confidence']} confidence)\n"
            f"Bias: **{d['bias']}** — {d['bull_signals']} bullish vs {d['bear_signals']} bearish signals."
        )

    if "rsi" in msg:
        state = "oversold 🟢" if d["rsi"]<30 else "overbought 🔴" if d["rsi"]>70 else "neutral 🟡"
        return f"**{sym} RSI:** {d['rsi']} — {state}"

    if "macd" in msg:
        return (f"**{sym} MACD:** {d['macd']} | Signal: {d['signal']} | Histogram: {d['histogram']}\n"
                f"→ **{'Bullish 🟢' if d['macd']>d['signal'] else 'Bearish 🔴'}**")

    if "vwap" in msg:
        return (f"**{sym} VWAP:** ₹{d['vwap']}\nCurrent: ₹{d['price']}\n"
                f"→ Trading **{'above' if d['price']>d['vwap'] else 'below'}** VWAP — {'bullish 🟢' if d['price']>d['vwap'] else 'bearish 🔴'}")

    if "atr" in msg:
        return f"**{sym} ATR (14):** ₹{d['atr']}\nThis means average daily range is ₹{d['atr']}. Use for stop loss sizing."

    if "adx" in msg:
        return (f"**{sym} ADX:** {d['adx']} → {'Strong trend' if d['adx']>40 else 'Moderate trend' if d['adx']>20 else 'Weak/no trend'}\n"
                f"+DI: {d['di_plus']} | -DI: {d['di_minus']}\n"
                f"→ {'Bulls in control' if d['di_plus']>d['di_minus'] else 'Bears in control'}")

    if any(w in msg for w in ["buy","sell","should","worth","good"]):
        return (f"{icon} **{sym} — {d['verdict']}** ({d['confidence']} confidence)\n\n"
                f"₹{p} | RSI: {d['rsi']} | ADX: {d['adx']} | **{d['bias']}**\n\n"
                + (f"Entry ₹{d['entry']}, SL ₹{d['sl']}, Target ₹{d['tp1']}." if d["verdict"]=="BUY"
                   else "Under pressure. Avoid fresh longs." if d["verdict"]=="SELL"
                   else f"Consolidating. Watch ₹{d['resistance']}."))

    if "support" in msg or "resistance" in msg:
        return (f"**{sym} Key Levels:**\n🔵 Support: ₹{d['support']}\n🔴 Resistance: ₹{d['resistance']}\nCurrent: ₹{p}")

    return (f"**{sym}** ₹{p} | {icon} **{d['verdict']}** ({d['bias']})\n"
            f"RSI: {d['rsi']} | MACD: {'↑' if d['macd']>d['signal'] else '↓'} | ADX: {d['adx']}\n\n"
            "Ask for *full analysis*, *trade setup*, *RSI*, *MACD*, *VWAP*, *ADX*, or *should I buy?*")


@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    import math
    def sanitize(obj):
        if isinstance(obj, float):
            return None if (math.isnan(obj) or math.isinf(obj)) else obj
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(i) for i in obj]
        return obj
    try:
        return sanitize(generate_analysis(req.ticker))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        ticker = req.ticker or extract_ticker(req.message)
        data = None
        if ticker:
            try:
                data = generate_analysis(ticker)
            except:
                data = None
        return {"reply": generate_chat_reply(req.message, ticker, data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/quote/{symbol}")
async def quote(symbol: str):
    try:
        t    = yf.Ticker(symbol)
        price = None
        try:
            price = round(float(t.fast_info.last_price), 2)
        except:
            pass
        if not price:
            hist  = t.history(period="2d", auto_adjust=True)
            price = round(float(hist["Close"].dropna().iloc[-1]), 2)
        hist10 = t.history(period="10d", auto_adjust=True)
        c10    = hist10["Close"].dropna()
        change = round((float(c10.iloc[-1]) - float(c10.iloc[0])) / float(c10.iloc[0]) * 100, 2) if len(c10)>=2 else 0.0
        return {"symbol": symbol, "price": price, "change": change}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

import pathlib
BASE_DIR     = pathlib.Path(__file__).parent.parent
FRONTEND_DIR = str(BASE_DIR / "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/chat")
async def serve_chat():
    return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))