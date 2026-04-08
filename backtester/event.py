from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BarEvent:
    symbol: str
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SignalEvent:
    symbol: str
    datetime: datetime
    signal_type: SignalType
    strength: float  # 0-1, 用于仓位计算


@dataclass
class OrderEvent:
    symbol: str
    datetime: datetime
    direction: OrderDirection
    quantity: float


@dataclass
class FillEvent:
    symbol: str
    datetime: datetime
    direction: OrderDirection
    quantity: float
    fill_price: float
    commission: float
