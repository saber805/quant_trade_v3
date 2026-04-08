"""止盈止损管理器 — 策略层内部跟踪，不修改 Portfolio。"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradeRecord:
    symbol: str
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    trailing_active: bool = False
    trailing_stop: float = 0.0
    trailing_distance: float = 0.0  # ATR 倍数对应的绝对值


class TradeManager:
    """每根K线检查 SL/TP，触发则返回需要平仓的 symbol 列表。"""

    def __init__(self):
        self.active_trades: dict[str, TradeRecord] = {}

    def register(self, symbol: str, entry_price: float, entry_time: datetime,
                 stop_loss: float, take_profit: float,
                 trailing_distance: float = 0.0) -> None:
        self.active_trades[symbol] = TradeRecord(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=entry_time,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_distance=trailing_distance,
        )

    def check_exits(self, symbol: str, bar_low: float, bar_high: float,
                    bar_close: float) -> str | None:
        """检查是否触发止损/止盈。返回 'SL'/'TP'/'TRAIL' 或 None。"""
        trade = self.active_trades.get(symbol)
        if trade is None:
            return None

        effective_sl = max(trade.stop_loss, trade.trailing_stop) \
            if trade.trailing_active else trade.stop_loss

        # SL 优先（用 bar.low 检查）
        if bar_low <= effective_sl:
            return "SL"

        # TP 检查（用 bar.high）
        if bar_high >= trade.take_profit:
            return "TP"

        return None

    def update_trailing(self, symbol: str, bar_high: float,
                        atr_value: float, activate_threshold: float = 1.5,
                        trail_multiplier: float = 1.5) -> None:
        """更新追踪止损。盈利超 activate_threshold×ATR 后激活。"""
        trade = self.active_trades.get(symbol)
        if trade is None or trade.trailing_distance == 0:
            return

        profit = bar_high - trade.entry_price
        activation_level = activate_threshold * atr_value

        if profit >= activation_level:
            trade.trailing_active = True
            new_trail = bar_high - trail_multiplier * atr_value
            if new_trail > trade.trailing_stop:
                trade.trailing_stop = new_trail

    def remove(self, symbol: str) -> TradeRecord | None:
        return self.active_trades.pop(symbol, None)

    def has_trade(self, symbol: str) -> bool:
        return symbol in self.active_trades
