"""区间震荡子策略 — BB+RSI 均值回归，低买高卖。"""

import pandas as pd

from backtester.event import BarEvent
from .base import SubStrategyBase


class RangingStrategy(SubStrategyBase):

    def __init__(self, strength: float = 0.10, sl_atr: float = 1.5,
                 rsi_entry: float = 35, adx_cap: float = 20):
        self.strength = strength
        self.sl_atr = sl_atr
        self.rsi_entry = rsi_entry
        self.adx_cap = adx_cap

    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        if has_position:
            return None

        # 入场: 价格触BB下轨 + RSI<35 + ADX<20
        # if bar.close > row["bb_lower"]:
        #     return None
        if row["rsi"] >= self.rsi_entry:
            return None
        if row["adx"] >= self.adx_cap:
            return None

        atr_val = row["atr"]
        sl = bar.close - self.sl_atr * atr_val
        tp = (row["bb_mid"] + row["bb_upper"]) / 2  # 目标: BB中轨

        # return None
        if row.low < row.bb_lower and row.close > row.bb_upper:
            return ("BUY", self.strength, sl, tp, 0)
        else:
            return None