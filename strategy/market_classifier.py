"""市场形态分类器 — 5种形态 + 3根K线确认过滤。"""

from enum import Enum

import pandas as pd


class Regime(Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGING = "RANGING"
    CHAOTIC = "CHAOTIC"
    BREAKOUT = "BREAKOUT"


class MarketClassifier:
    """基于 ADX / EMA斜率 / BB宽度 / ROC 的决策树分类。"""

    def __init__(self, adx_trend: float = 25, adx_no_trend: float = 20,
                 bb_expand_ratio: float = 1.5, roc_threshold: float = 3.0,
                 confirm_bars: int = 3, atr_expand_ratio: float = 1.0):
        self.adx_trend = adx_trend
        self.adx_no_trend = adx_no_trend
        self.bb_expand_ratio = bb_expand_ratio
        self.roc_threshold = roc_threshold
        self.confirm_bars = confirm_bars
        self.atr_expand_ratio = atr_expand_ratio

    def classify_series(self, indicators: pd.DataFrame) -> pd.Series:
        """向量化分类整个序列，返回 Regime Series。"""
        adx_val = indicators["adx"]
        slope = indicators["ema50_slope"]
        bb_width = indicators["bb_width"]
        bb_width_ma = indicators["bb_width_ma"]
        roc_val = indicators["roc"].abs()
        atr_val = indicators["atr"]
        atr_ma = indicators["atr_ma"]

        bb_expanding = bb_width > (bb_width_ma * self.bb_expand_ratio)
        roc_confirm = roc_val > self.roc_threshold
        atr_high = atr_val > (atr_ma * self.atr_expand_ratio)

        # 原始分类（无确认）— 默认 RANGING
        raw = pd.Series(Regime.RANGING, index=indicators.index)

        # ADX > 25: 趋势市场
        trend_mask = adx_val > self.adx_trend
        raw[trend_mask & (slope > 0)] = Regime.UPTREND
        raw[trend_mask & (slope <= 0)] = Regime.DOWNTREND

        # ADX < 20: 无趋势
        no_trend = adx_val < self.adx_no_trend
        raw[no_trend & bb_expanding & roc_confirm] = Regime.BREAKOUT

        # ADX 20-25: 过渡区
        transition = (adx_val >= self.adx_no_trend) & (adx_val <= self.adx_trend)
        raw[transition & bb_expanding & roc_confirm] = Regime.BREAKOUT

        # RANGING 中 ATR 偏高 → CHAOTIC（高波动无序）
        still_ranging = raw == Regime.RANGING
        raw[still_ranging & atr_high] = Regime.CHAOTIC

        # 3根K线确认过滤
        return self._apply_confirmation(raw)

    def _apply_confirmation(self, raw: pd.Series) -> pd.Series:
        """形态切换需连续 confirm_bars 根K线确认。"""
        confirmed = raw.copy()
        prev_regime = raw.iloc[0] if len(raw) > 0 else Regime.RANGING
        count = 0

        for i in range(len(raw)):
            current_raw = raw.iloc[i]
            if current_raw == prev_regime:
                confirmed.iloc[i] = prev_regime
                count = 0
            else:
                count += 1
                if count >= self.confirm_bars:
                    prev_regime = current_raw
                    confirmed.iloc[i] = current_raw
                    count = 0
                else:
                    confirmed.iloc[i] = prev_regime

        return confirmed
