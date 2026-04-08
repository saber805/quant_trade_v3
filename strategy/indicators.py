"""技术指标库 — 向量化计算，on_init 中一次性算完。"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """返回 DataFrame 含 adx, plus_di, minus_di 列。"""
    high, low, close = df["high"], df["low"], df["close"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    plus_dm = np.where((high - prev_high) > (prev_low - low),
                       np.maximum(high - prev_high, 0), 0)
    minus_dm = np.where((prev_low - low) > (high - prev_high),
                        np.maximum(prev_low - low, 0), 0)

    atr_vals = atr(df, period)

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(
        span=period, adjust=False).mean() / atr_vals
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(
        span=period, adjust=False).mean() / atr_vals

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_vals = dx.ewm(span=period, adjust=False).mean()

    return pd.DataFrame({
        "adx": adx_vals, "plus_di": plus_di, "minus_di": minus_di,
    }, index=df.index)


def bollinger_bands(series: pd.Series, period: int = 20,
                    num_std: float = 2.0) -> pd.DataFrame:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    return pd.DataFrame({
        "bb_upper": mid + num_std * std,
        "bb_mid": mid,
        "bb_lower": mid - num_std * std,
        "bb_width": (2 * num_std * std) / mid,  # 归一化宽度
    }, index=series.index)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change (%)."""
    return series.pct_change(period) * 100


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """一次性计算所有指标，返回合并后的 DataFrame。"""
    out = df.copy()

    # EMA
    out["ema20"] = ema(df["close"], 20)
    out["ema50"] = ema(df["close"], 50)
    out["ema50_slope"] = out["ema50"].pct_change(5)  # 5根K线变化率

    # ADX
    adx_df = adx(df, 14)
    out = pd.concat([out, adx_df], axis=1)

    # Bollinger Bands
    bb_df = bollinger_bands(df["close"], 20, 2.0)
    out = pd.concat([out, bb_df], axis=1)
    out["bb_width_ma"] = out["bb_width"].rolling(20).mean()

    # RSI
    out["rsi"] = rsi(df["close"], 14)

    # ATR
    out["atr"] = atr(df, 14)
    out["atr_ma"] = out["atr"].rolling(20).mean()

    # ROC
    out["roc"] = roc(df["close"], 10)

    return out
