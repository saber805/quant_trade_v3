"""突破子策略 — 波动率扩张 + 动量确认。"""

import pandas as pd

from backtester.event import BarEvent
from .base import SubStrategyBase


class BreakoutStrategy(SubStrategyBase):

    def __init__(self, strength: float = 0.12, sl_atr: float = 1.5,
                 tp_atr: float = 3.0, roc_threshold: float = 3.0,
                 volume_ratio: float = 1.5):
        self.strength = strength
        self.sl_atr = sl_atr
        self.tp_atr = tp_atr
        self.roc_threshold = roc_threshold
        self.volume_ratio = volume_ratio

    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        if has_position:
            return None

        # 入场: 收盘>BB上轨 + BB宽度扩张 + ROC>3% + 放量
        if bar.close <= row["bb_upper"]:
            return None
        if row["bb_width"] <= row["bb_width_ma"] * 1.5:
            return None
        if row["roc"] <= self.roc_threshold:
            return None
        if row.get("volume_ratio", 2.0) < self.volume_ratio:
            return None

        atr_val = row["atr"]
        sl = bar.close - self.sl_atr * atr_val
        tp = bar.close + self.tp_atr * atr_val

        return None

        # return ("BUY", self.strength, sl, tp, 0)
