import math

def compute_fundamentals(info: dict) -> dict:
    def pct(v):
        return round(v * 100, 2) if v and not (isinstance(v, float) and math.isnan(v)) else None
    def val(v, r=2):
        return round(v, r) if v and not (isinstance(v, float) and math.isnan(v)) else None

    roe = pct(info.get("returnOnEquity"))
    roa = pct(info.get("returnOnAssets"))
    gm  = pct(info.get("grossMargins"))
    om  = pct(info.get("operatingMargins"))
    nm  = pct(info.get("profitMargins"))
    rg  = pct(info.get("revenueGrowth"))
    eg  = pct(info.get("earningsGrowth"))
    pe  = val(info.get("trailingPE"))
    fpe = val(info.get("forwardPE"))
    pb  = val(info.get("priceToBook"))
    ps  = val(info.get("priceToSalesTrailing12Months"))
    ev  = val(info.get("enterpriseToEbitda"))
    de  = val(info.get("debtToEquity"))
    cr  = val(info.get("currentRatio"))
    qr  = val(info.get("quickRatio"))
    et  = val(info.get("trailingEps"))
    ef  = val(info.get("forwardEps"))
    dy  = pct(info.get("dividendYield"))

    score = 0
    if roe and roe >= 15: score += 1
    if roa and roa >= 10: score += 1
    if om  and om  >= 15: score += 1
    if nm  and nm  >= 10: score += 1
    if rg  and rg  >= 15: score += 1
    if de  and de  <= 50: score += 1
    if cr  and cr  >= 1.5: score += 1
    if et  and ef  and ef > et: score += 1

    return {
        "roe": roe, "roa": roa, "gm": gm, "om": om, "nm": nm,
        "rg": rg, "eg": eg, "pe": pe, "fpe": fpe, "pb": pb,
        "ps": ps, "ev": ev, "de": de, "cr": cr, "qr": qr,
        "et": et, "ef": ef, "dy": dy, "score": min(score, 8)
    }

def compute_verdict(tech: dict, trade: dict, fs: int, mkt: str, news: str) -> dict:
    total = trade["score"] * 2 + fs
    total += {"BULLISH": 2, "BEARISH": -2, "SIDEWAYS": 0}.get(mkt, 0)
    total += {"POSITIVE": 1, "NEGATIVE": -1, "NEUTRAL": 0}.get(news, 0)
    if trade["rr1"] >= 2.5: total += 1
    if trade["rr1"] < 1.0:  total -= 1

    if total >= 6:    dec = "BUY";          conf = "HIGH" if total >= 10 else "MEDIUM"
    elif total <= -4: dec = "SELL";         conf = "HIGH" if total <= -8 else "MEDIUM"
    else:             dec = "AVOID / WAIT"; conf = "MEDIUM"

    return {"decision": dec, "confidence": conf, "total": total}