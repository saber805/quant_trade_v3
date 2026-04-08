"""下降趋势子策略 — 现货只做多，下跌空仓。"""

import pandas as pd

from backtester.event import BarEvent
from .base import SubStrategyBase


class DowntrendStrategy(SubStrategyBase):

    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        if has_position:
            return ("SELL", 1.0, 0, 0, 0)
        return None
