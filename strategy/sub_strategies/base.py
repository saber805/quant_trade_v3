"""子策略接口。"""

from abc import ABC, abstractmethod

import pandas as pd

from backtester.event import BarEvent


class SubStrategyBase(ABC):
    """所有子策略的基类。返回 (action, strength, sl, tp, trailing_dist)。"""

    @abstractmethod
    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        """
        评估当前K线，返回:
          ("BUY", strength, stop_loss, take_profit, trailing_distance)
          ("SELL", 1.0, 0, 0, 0)  — 平仓
          None — 无操作
        """
        ...
