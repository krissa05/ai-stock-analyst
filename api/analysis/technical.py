import numpy as np
import pandas as pd
from .indicators import calc_rsi, calc_macd, calc_bb, calc_sma, calc_atr

def compute_technicals(df: pd.DataFrame) -> dict:
    close = df["Close"].squeeze()
    cp = float(close.iloc[-1])

    rsi_s = calc_rsi(close)
    rsi = float(rsi_s.iloc[-1])

    macd_s, sig_s, hist_s = calc_macd(close)
    m = float(macd_s.iloc[-1])
    s = float(sig_s.iloc[-1])
    h = float(hist_s.iloc[-1])

    bbu_s, bbm_s, bbl_s, bw_s, pb_s = calc_bb(close)
    bbu = float(bbu_s.iloc[-1])
    bbm = float(bbm_s.iloc[-1])
    bbl = float(bbl_s.iloc[-1])
    bw = float(bw_s.iloc[-1])
    pb = float(pb_s.iloc[-1])

    s20 = float(calc_sma(close, 20).iloc[-1])
    s50_s = calc_sma(close, 50)
    s200_s = calc_sma(close, 200)
    s50 = float(s50_s.dropna().iloc[-1]) if not s50_s.dropna().empty else None
    s200 = float(s200_s.dropna().iloc[-1]) if not s200_s.dropna().empty else None

    c10 = (cp - float(close.iloc[-10])) / float(close.iloc[-10]) * 100
    c20 = (cp - float(close.iloc[-20])) / float(close.iloc[-20]) * 100

    if s200 and s50:
        if cp > s20 > s50 > s200:       ts = "Strong Bullish"
        elif s50 < s200:                 ts = "Bearish (Death Cross)"
        elif s50 > s200 and cp > s50:   ts = "Bullish (Golden Cross)"
        elif cp < s20 < s50 < s200:     ts = "Strong Bearish"
        elif cp > s200:                 ts = "Neutral/Weak Bullish"
        else:                           ts = "Neutral"
    else:
        ts = "Neutral"

    macd_cross = ""
    if m > s and float(macd_s.iloc[-2]) <= float(sig_s.iloc[-2]):
        macd_cross = "BULLISH CROSSOVER"
    elif m < s and float(macd_s.iloc[-2]) >= float(sig_s.iloc[-2]):
        macd_cross = "BEARISH CROSSOVER"

    return {
        "current_price": cp,
        "rsi": round(rsi, 2),
        "macd": round(m, 4),
        "macd_signal": round(s, 4),
        "macd_hist": round(h, 4),
        "macd_cross": macd_cross,
        "bb_upper": round(bbu, 2),
        "bb_mid": round(bbm, 2),
        "bb_lower": round(bbl, 2),
        "bb_bw": round(bw, 2),
        "bb_pb": round(pb, 4),
        "sma20": round(s20, 2),
        "sma50": round(s50, 2) if s50 else None,
        "sma200": round(s200, 2) if s200 else None,
        "trend": ts,
        "change_10d": round(c10, 2),
        "change_20d": round(c20, 2),
    }

def compute_snr(df: pd.DataFrame, tech: dict) -> tuple:
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    cp = tech["current_price"]
    sups, ress = [], []

    for w in [10, 20, 50, 63]:
        s = float(low.rolling(w).min().iloc[-1])
        r = float(high.rolling(w).max().iloc[-1])
        if s < cp: sups.append(s)
        if r > cp: ress.append(r)

    n = min(252, len(low))
    wl = float(low.rolling(n).min().iloc[-1])
    wh = float(high.rolling(n).max().iloc[-1])
    if wl < cp: sups.append(wl)
    if wh > cp: ress.append(wh)

    for v in [tech.get("sma20"), tech.get("sma50"), tech.get("sma200")]:
        if v is None: continue
        if v < cp: sups.append(v)
        else: ress.append(v)

    sups = sorted(set(round(x, 2) for x in sups), reverse=True)[:5]
    ress = sorted(set(round(x, 2) for x in ress))[:5]
    return sups, ress

def compute_trade(df: pd.DataFrame, tech: dict, sups: list, ress: list) -> dict:
    cp = tech["current_price"]
    rsi = tech["rsi"]
    m = tech["macd"]
    s = tech["macd_signal"]
    s20 = tech.get("sma20")
    s50 = tech.get("sma50")
    s200 = tech.get("sma200")
    atr = float(calc_atr(df).iloc[-1])

    score = 0
    reasons = []

    if rsi <= 35:   score += 2; reasons.append(("RSI deeply oversold — strong buy signal", "bull"))
    elif rsi <= 45: score += 1; reasons.append(("RSI bearish but nearing recovery zone", "bull"))
    elif rsi >= 70: score -= 2; reasons.append(("RSI overbought — high reversal risk", "bear"))
    elif rsi >= 60: score -= 1; reasons.append(("RSI elevated — limited upside headroom", "bear"))

    if m > s:  score += 1; reasons.append(("MACD above signal — bullish momentum", "bull"))
    else:      score -= 1; reasons.append(("MACD below signal — bearish momentum", "bear"))

    if s50 and s200:
        if s50 > s200: score += 1; reasons.append(("Golden Cross structure (50>200 SMA)", "bull"))
        else:          score -= 1; reasons.append(("Death Cross active (50<200 SMA)", "bear"))

    if s200:
        if cp > s200: score += 1; reasons.append(("Price above 200 SMA — uptrend intact", "bull"))
        else:         score -= 1; reasons.append(("Price below 200 SMA — downtrend active", "bear"))

    if s20:
        if cp > s20: score += 1; reasons.append(("Price above 20 SMA — short-term bullish", "bull"))
        else:        score -= 1; reasons.append(("Price below 20 SMA — short-term bearish", "bear"))

    bias = "BULLISH" if score >= 3 else ("BEARISH" if score <= -3 else "NEUTRAL")

    if bias == "BULLISH":
        entry = round(cp, 2)
        sl = round(max(cp - 2.5 * atr, sups[0] - atr * 0.3 if sups else cp * 0.94), 2)
        tp1 = round(ress[0] if ress else cp * 1.05, 2)
        tp2 = round(ress[1] if len(ress) > 1 else cp * 1.10, 2)
    elif bias == "BEARISH":
        entry = round(cp, 2)
        sl = round(min(cp + 2.5 * atr, ress[0] + atr * 0.3 if ress else cp * 1.06), 2)
        tp1 = round(sups[0] if sups else cp * 0.95, 2)
        tp2 = round(sups[1] if len(sups) > 1 else cp * 0.90, 2)
    else:
        entry = round(cp, 2)
        sl = round(cp - 2 * atr, 2)
        tp1 = round(cp + 2 * atr, 2)
        tp2 = round(cp + 4 * atr, 2)

    risk = abs(entry - sl)
    rew1 = abs(tp1 - entry)
    rew2 = abs(tp2 - entry)
    rr1 = round(rew1 / risk, 2) if risk else 0
    rr2 = round(rew2 / risk, 2) if risk else 0

    return {
        "bias": bias, "entry": entry, "sl": sl,
        "tp1": tp1, "tp2": tp2, "rr1": rr1, "rr2": rr2,
        "score": score, "reasons": reasons, "atr": round(atr, 2)
    }