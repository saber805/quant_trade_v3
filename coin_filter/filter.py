"""运行时币种过滤器：逐Bar检测流动性异常和价格异常。"""

from __future__ import annotations

import numpy as np
from collections import defaultdict

from .config import (
    BLACKLIST,
    VOLUME_ANOMALY_RATIO,
    VOLUME_ROLLING_WINDOW,
    PRICE_SPIKE_THRESHOLD,
)


class CoinFilter:
    """运行时过滤器，在回测/实盘的每个Bar判断是否应跳过该币种。

    用法::

        filt = CoinFilter()
        # 在 on_init 阶段用历史数据预热
        filt.warm_up(historical_data)

        # 在每个Bar调用
        if filt.should_skip(symbol, close_price, volume):
            continue  # 跳过该币种
    """

    def __init__(
        self,
        blacklist: list[str] | None = None,
        volume_anomaly_ratio: float = VOLUME_ANOMALY_RATIO,
        volume_window: int = VOLUME_ROLLING_WINDOW,
        price_spike_threshold: float = PRICE_SPIKE_THRESHOLD,
    ):
        self.blacklist = set(blacklist or BLACKLIST)
        self.volume_anomaly_ratio = volume_anomaly_ratio
        self.volume_window = volume_window
        self.price_spike_threshold = price_spike_threshold

        # 滚动状态：每个币种维护最近N个Bar的成交量和上一个收盘价
        self._volume_buf: dict[str, list[float]] = defaultdict(list)
        self._last_close: dict[str, float] = {}
        self._skip_count: dict[str, int] = defaultdict(int)

    def warm_up(self, data: dict[str, "pd.DataFrame"]) -> None:
        """用历史数据预热滚动窗口，避免开始阶段误判。"""
        for symbol, df in data.items():
            volumes = df["volume"].values[-self.volume_window:]
            self._volume_buf[symbol] = list(volumes)
            self._last_close[symbol] = float(df["close"].iloc[-1])

    def should_skip(self, symbol: str, close: float, volume: float) -> bool:
        """判断当前Bar是否应跳过该币种。

        Returns True 表示应跳过（不开新仓），False 表示正常交易。
        注意：跳过只影响开新仓，不影响已有持仓的平仓信号。
        """
        skip = False

        # 1. 黑名单
        if symbol in self.blacklist:
            skip = True

        # 2. 成交量异常
        if not skip:
            buf = self._volume_buf[symbol]
            if len(buf) >= self.volume_window:
                avg_vol = np.mean(buf[-self.volume_window:])
                if avg_vol > 0 and volume < avg_vol * self.volume_anomaly_ratio:
                    skip = True

        # 3. 价格异常（单Bar涨跌幅过大）
        if not skip:
            last = self._last_close.get(symbol)
            if last and last > 0:
                change = abs(close - last) / last
                if change > self.price_spike_threshold:
                    skip = True

        # 更新滚动状态
        self._volume_buf[symbol].append(volume)
        if len(self._volume_buf[symbol]) > self.volume_window * 2:
            self._volume_buf[symbol] = self._volume_buf[symbol][-self.volume_window:]
        self._last_close[symbol] = close

        if skip:
            self._skip_count[symbol] += 1

        return skip

    def add_to_blacklist(self, symbol: str) -> None:
        """动态添加黑名单。"""
        self.blacklist.add(symbol)

    def remove_from_blacklist(self, symbol: str) -> None:
        """动态移除黑名单。"""
        self.blacklist.discard(symbol)

    def get_skip_stats(self) -> dict[str, int]:
        """返回各币种被跳过的次数统计。"""
        return dict(self._skip_count)
