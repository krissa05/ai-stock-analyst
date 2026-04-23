import numpy as np
import pandas as pd

def calc_rsi(c: pd.Series, n=14) -> pd.Series:
    d = c.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = g.ewm(alpha=1/n, min_periods=n).mean()
    al = l.ewm(alpha=1/n, min_periods=n).mean()
    return 100 - (100 / (1 + ag / al.replace(0, np.nan)))

def calc_macd(c: pd.Series, f=12, s=26, sig=9):
    m = c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean()
    sl = m.ewm(span=sig, adjust=False).mean()
    return m, sl, m - sl

def calc_bb(c: pd.Series, n=20, k=2):
    m = c.rolling(n).mean()
    sd = c.rolling(n).std()
    u = m + k * sd
    l = m - k * sd
    return u, m, l, (u - l) / m * 100, (c - l) / (u - l)

def calc_sma(c: pd.Series, n) -> pd.Series:
    return c.rolling(n).mean()

def calc_atr(df: pd.DataFrame, n=14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    return pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1).rolling(n).mean()