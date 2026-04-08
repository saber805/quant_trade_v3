"""上升趋势子策略 — EMA交叉跟踪，ATR追踪止损。"""

import pandas as pd

from backtester.event import BarEvent
from .base import SubStrategyBase


class UptrendStrategy(SubStrategyBase):

    def __init__(self, strength: float = 0.15, sl_atr: float = 2.0,
                 tp_atr: float = 3.0, rsi_cap: float = 75):
        self.strength = strength
        self.sl_atr = sl_atr
        self.tp_atr = tp_atr
        self.rsi_cap = rsi_cap

    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        if has_position:
            return None  # 持仓由 TradeManager 管理

        # 入场: EMA20 上穿 EMA50 + ADX>25 + RSI<75
        ema20 = row["ema20"]
        ema50 = row["ema50"]
        prev_ema20 = row.get("prev_ema20", ema20)
        prev_ema50 = row.get("prev_ema50", ema50)

        crossover = (prev_ema20 <= prev_ema50) and (ema20 > ema50)
        if not crossover:
            return None

        if row["adx"] <= 25 or row["rsi"] >= self.rsi_cap:
            return None

        atr_val = row["atr"]
        sl = bar.close - self.sl_atr * atr_val
        tp = bar.close + self.tp_atr * atr_val
        trailing = 1.5 * atr_val  # 追踪止损距离

        return None

        # return ("BUY", self.strength, sl, tp, trailing)
