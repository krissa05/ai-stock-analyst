import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

DEMO_PROFILES = {
    "RELIANCE.NS": {
        "longName": "Reliance Industries Limited", "sector": "Energy",
        "industry": "Oil, Gas & Consumable Fuels", "marketCap": 18_500_000_000_000,
        "currency": "INR", "exchange": "NSE", "country": "India",
        "website": "https://www.ril.com", "fullTimeEmployees": 236334,
        "longBusinessSummary": "Reliance Industries is a Fortune 500 conglomerate spanning O2C, Jio Platforms, Reliance Retail, and New Energy.",
        "returnOnEquity": 0.0879, "returnOnAssets": 0.043,
        "grossMargins": 0.18, "operatingMargins": 0.112, "profitMargins": 0.073,
        "revenueGrowth": 0.07, "earningsGrowth": 0.085,
        "trailingPE": 28.4, "forwardPE": 22.1, "priceToBook": 2.1,
        "priceToSalesTrailing12Months": 1.8, "enterpriseToEbitda": 11.2,
        "debtToEquity": 42.0, "currentRatio": 1.1, "quickRatio": 0.9,
        "totalCash": 2_200_000_000_000, "totalDebt": 3_100_000_000_000,
        "trailingEps": 53.2, "forwardEps": 68.4, "dividendYield": 0.004, "base_price": 1355.0,
    },
    "TCS.NS": {
        "longName": "Tata Consultancy Services", "sector": "Technology",
        "industry": "IT Services & Consulting", "marketCap": 13_800_000_000_000,
        "currency": "INR", "exchange": "NSE", "country": "India",
        "website": "https://www.tcs.com", "fullTimeEmployees": 601546,
        "longBusinessSummary": "TCS is a global leader in IT services and digital solutions across 46 countries.",
        "returnOnEquity": 0.48, "returnOnAssets": 0.27,
        "grossMargins": 0.35, "operatingMargins": 0.245, "profitMargins": 0.195,
        "revenueGrowth": 0.055, "earningsGrowth": 0.09,
        "trailingPE": 29.2, "forwardPE": 24.5, "priceToBook": 13.4,
        "priceToSalesTrailing12Months": 5.6, "enterpriseToEbitda": 20.1,
        "debtToEquity": 5.0, "currentRatio": 2.8, "quickRatio": 2.6,
        "totalCash": 600_000_000_000, "totalDebt": 80_000_000_000,
        "trailingEps": 130.5, "forwardEps": 148.0, "dividendYield": 0.018, "base_price": 3780.0,
    },
}

def get_demo_profile(ticker: str) -> dict:
    k = ticker.upper()
    return DEMO_PROFILES.get(k, {
        "longName": f"{ticker} Ltd", "sector": "Diversified",
        "industry": "Conglomerate", "marketCap": 500_000_000_000,
        "currency": "INR", "exchange": "NSE", "country": "India",
        "website": "N/A", "fullTimeEmployees": 50000,
        "longBusinessSummary": f"{ticker} is a listed Indian company.",
        "returnOnEquity": 0.14, "returnOnAssets": 0.08,
        "grossMargins": 0.25, "operatingMargins": 0.14, "profitMargins": 0.09,
        "revenueGrowth": 0.10, "earningsGrowth": 0.12,
        "trailingPE": 24.0, "forwardPE": 20.0, "priceToBook": 3.5,
        "priceToSalesTrailing12Months": 2.5, "enterpriseToEbitda": 14.0,
        "debtToEquity": 30.0, "currentRatio": 1.5, "quickRatio": 1.1,
        "totalCash": 200_000_000_000, "totalDebt": 250_000_000_000,
        "trailingEps": 40.0, "forwardEps": 48.0, "dividendYield": 0.012, "base_price": 1000.0,
    })

def generate_demo_ohlcv(base_price: float, n: int = 252) -> pd.DataFrame:
    np.random.seed(42)
    mu = 0.0003; sigma = 0.013
    dates = pd.bdate_range(end=datetime.today(), periods=n)
    ret = np.random.normal(mu, sigma, n) + 0.002 * np.sin(np.linspace(0, 2 * np.pi, n))
    close = base_price * np.exp(np.cumsum(ret))
    dv = np.abs(ret)
    opens = np.roll(close, 1); opens[0] = base_price * 0.998
    highs = np.array([max(close[i], opens[i]) * (1 + dv[i] * 0.7) for i in range(n)])
    lows  = np.array([min(close[i], opens[i]) * (1 - dv[i] * 0.7) for i in range(n)])
    vols  = (2_000_000 * (1 + 5 * dv) * np.random.lognormal(0, 0.3, n)).astype(int)
    return pd.DataFrame({
        "Open": np.round(opens, 2), "High": np.round(highs, 2),
        "Low": np.round(lows, 2), "Close": np.round(close, 2), "Volume": vols
    }, index=dates)

def fetch_info(ticker: str) -> dict:
    if YFINANCE_OK:
        try:
            info = yf.Ticker(ticker).info
            if info and info.get("longName"):
                return info
        except Exception:
            pass
    return get_demo_profile(ticker)

def fetch_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    if YFINANCE_OK:
        try:
            df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            if not df.empty:
                return df
        except Exception:
            pass
    p = get_demo_profile(ticker)
    return generate_demo_ohlcv(p.get("base_price", 1000.0))

def fetch_news(ticker: str) -> list:
    if YFINANCE_OK:
        try:
            raw = yf.Ticker(ticker).news or []
            arts = [{
                "title": x.get("title", ""),
                "summary": x.get("summary", ""),
                "date": str(x.get("providerPublishTime", "")),
                "polarity": None
            } for x in raw[:6]]
            if arts:
                return arts
        except Exception:
            pass
    return [
        {"title": f"{ticker} reports steady results", "summary": "Earnings in line with estimates.", "date": "", "polarity": 0.1},
        {"title": f"Analysts maintain BUY on {ticker}", "summary": "Strong fundamentals cited.", "date": "", "polarity": 0.5},
    ]