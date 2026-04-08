from .config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from .event import FillEvent, OrderEvent, OrderDirection


class SimulatedExecution:
    """模拟成交引擎：加入滑点和手续费。"""

    def __init__(self, commission_rate: float = DEFAULT_COMMISSION_RATE,
                 slippage_rate: float = DEFAULT_SLIPPAGE_RATE):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def execute(self, order: OrderEvent, close_price: float) -> FillEvent:
        """根据订单和当前收盘价模拟成交。"""
        if order.direction == OrderDirection.BUY:
            fill_price = close_price * (1 + self.slippage_rate)
        else:
            fill_price = close_price * (1 - self.slippage_rate)

        commission = fill_price * order.quantity * self.commission_rate

        return FillEvent(
            symbol=order.symbol,
            datetime=order.datetime,
            direction=order.direction,
            quantity=order.quantity,
            fill_price=fill_price,
            commission=commission,
        )
