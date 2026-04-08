from datetime import datetime

from .event import (
    BarEvent, SignalEvent, SignalType, OrderEvent, OrderDirection, FillEvent,
)


class Portfolio:
    """持仓管理：资金追踪、信号→订单转换、权益快照。"""

    def __init__(self, initial_capital: float, symbols: list[str]):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, float] = {s: 0.0 for s in symbols}
        self.equity_curve: list[dict] = []
        self.trade_log: list[dict] = []
        self._latest_prices: dict[str, float] = {}

    def on_signal(self, signal: SignalEvent) -> OrderEvent | None:
        """将信号转换为订单。BUY用strength×可用资金，SELL平掉全部仓位。"""
        if signal.signal_type == SignalType.BUY:
            if self.positions.get(signal.symbol, 0) > 0:
                return None  # 已有仓位，不加仓
            # 用 strength × 可用资金 / 当前价格 计算数量
            price = self._latest_prices.get(signal.symbol, 0)
            if price <= 0:
                return None
            alloc = self.cash * signal.strength
            quantity = alloc / price
            if quantity <= 0:
                return None
            return OrderEvent(
                symbol=signal.symbol,
                datetime=signal.datetime,
                direction=OrderDirection.BUY,
                quantity=quantity,
            )

        elif signal.signal_type == SignalType.SELL:
            qty = self.positions.get(signal.symbol, 0)
            if qty <= 0:
                return None  # 无仓位可卖
            return OrderEvent(
                symbol=signal.symbol,
                datetime=signal.datetime,
                direction=OrderDirection.SELL,
                quantity=qty,
            )

        return None

    def on_fill(self, fill: FillEvent) -> None:
        """更新持仓和现金，记录交易日志。"""
        if fill.direction == OrderDirection.BUY:
            cost = fill.fill_price * fill.quantity + fill.commission
            self.cash -= cost
            self.positions[fill.symbol] = (
                self.positions.get(fill.symbol, 0) + fill.quantity
            )
        else:
            revenue = fill.fill_price * fill.quantity - fill.commission
            self.cash += revenue
            self.positions[fill.symbol] = (
                self.positions.get(fill.symbol, 0) - fill.quantity
            )

        self.trade_log.append({
            "datetime": fill.datetime,
            "symbol": fill.symbol,
            "direction": fill.direction.value,
            "quantity": fill.quantity,
            "price": fill.fill_price,
            "commission": fill.commission,
            "cash_after": self.cash,
        })

    def update_price(self, symbol: str, price: float) -> None:
        """更新最新价格（用于计算权益和下单数量）。"""
        self._latest_prices[symbol] = price

    def update_equity(self, dt: datetime) -> None:
        """快照当前权益：现金 + 持仓市值。"""
        position_value = sum(
            qty * self._latest_prices.get(sym, 0)
            for sym, qty in self.positions.items()
        )
        total_equity = self.cash + position_value
        self.equity_curve.append({
            "datetime": dt,
            "cash": self.cash,
            "position_value": position_value,
            "total_equity": total_equity,
        })

    def get_total_equity(self) -> float:
        position_value = sum(
            qty * self._latest_prices.get(sym, 0)
            for sym, qty in self.positions.items()
        )
        return self.cash + position_value
