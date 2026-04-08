from abc import ABC, abstractmethod

from .event import BarEvent, SignalEvent


class StrategyBase(ABC):
    """策略抽象基类。

    策略在 on_init 中用向量化 pandas 预计算指标，
    on_bar 中只做查表，保证回测速度。
    """

    def __init__(self, symbols: list[str], params: dict | None = None):
        self.symbols = symbols
        self.params = params or {}

    def on_init(self, historical_bars: dict[str, "pd.DataFrame"]) -> None:
        """预计算指标（可选覆写）。historical_bars: {symbol: DataFrame}"""
        pass

    @abstractmethod
    def on_bar(self, bar: BarEvent,
               current_positions: dict[str, float]) -> list[SignalEvent] | None:
        """核心逻辑：接收Bar，返回信号列表或None。"""
        ...

    def on_finish(self) -> None:
        """回测结束清理（可选覆写）。"""
        pass
