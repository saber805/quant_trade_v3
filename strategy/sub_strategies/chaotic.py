"""高波动无序子策略 — 不开新仓，有仓则平。"""

import pandas as pd

from backtester.event import BarEvent
from .base import SubStrategyBase


class ChaoticStrategy(SubStrategyBase):

    def evaluate(self, bar: BarEvent, row: pd.Series,
                 has_position: bool) -> tuple | None:
        if has_position:
            return ("SELL", 1.0, 0, 0, 0)
        return None
