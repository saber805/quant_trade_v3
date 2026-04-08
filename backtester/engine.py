from __future__ import annotations

import pandas as pd

from . import data_loader
from .config import (
    DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE,
    DEFAULT_INITIAL_CAPITAL, TRAIN_RATIO,
)
from .event import BarEvent, SignalType
from .execution import SimulatedExecution
from .metrics import compute as compute_metrics
from .portfolio import Portfolio
from .report import print_summary, export, plot_equity
from .strategy_base import StrategyBase


# 周期对应每天的bar数
BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}


class BacktestEngine:
    """回测引擎：编排数据加载、策略执行、组合管理、成交模拟。"""

    def __init__(
        self,
        strategy: StrategyBase,
        symbols: list[str],
        interval: str = "1d",
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        commission_rate: float = DEFAULT_COMMISSION_RATE,
        slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
        use_test_set: bool = False,
        train_ratio: float = TRAIN_RATIO,
        coin_filter=None,  # CoinFilter 实例，可选
    ):
        self.strategy = strategy
        self.symbols = symbols
        self.interval = interval
        self.initial_capital = initial_capital
        self.use_test_set = use_test_set
        self.train_ratio = train_ratio
        self.coin_filter = coin_filter

        self.portfolio = Portfolio(initial_capital, symbols)
        self.execution = SimulatedExecution(commission_rate, slippage_rate)
        self.bars_per_day = BARS_PER_DAY.get(interval, 1)

        self.metrics: dict = {}

    def run(self) -> dict:
        """执行回测，返回绩效指标。"""
        # 1. 加载数据
        all_data = data_loader.load_multiple(self.symbols, self.interval)

        # 2. 分割数据，选择训练/测试集
        active_data: dict[str, pd.DataFrame] = {}
        full_data: dict[str, pd.DataFrame] = {}
        for sym, df in all_data.items():
            train_df, test_df = data_loader.split(df, self.train_ratio)
            active_data[sym] = test_df if self.use_test_set else train_df
            full_data[sym] = df

        # 3. 策略初始化（传入完整历史数据供预计算指标）
        self.strategy.on_init(full_data)

        # 3.5 过滤器预热（用训练集之前的数据填充滚动窗口）
        if self.coin_filter is not None:
            self.coin_filter.warm_up(full_data)

        # 4. 对齐时间戳：取所有活跃数据的时间并排序
        all_timestamps = sorted(set(
            ts for df in active_data.values() for ts in df.index
        ))

        # 5. 逐Bar驱动
        set_label = "测试集" if self.use_test_set else "训练集"
        print(f"开始回测 [{set_label}] | 币种数={len(self.symbols)} "
              f"| 周期={self.interval} | Bars={len(all_timestamps)}")

        for ts in all_timestamps:
            # 对每个有数据的币种处理
            for sym in self.symbols:
                df = active_data[sym]
                if ts not in df.index:
                    continue

                row = df.loc[ts]
                bar = BarEvent(
                    symbol=sym,
                    datetime=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )

                # 更新最新价格
                self.portfolio.update_price(sym, bar.close)

                # 1) 策略产生信号
                signals = self.strategy.on_bar(bar, self.portfolio.positions)
                if not signals:
                    continue

                # 1.5) 过滤器：跳过异常币种的开仓信号，保留平仓信号
                if self.coin_filter is not None:
                    skip = self.coin_filter.should_skip(sym, bar.close, bar.volume)
                    if skip:
                        signals = [s for s in signals if s.signal_type == SignalType.SELL]
                        if not signals:
                            continue

                # 2-4) 信号 → 订单 → 成交 → 更新持仓
                for signal in signals:
                    order = self.portfolio.on_signal(signal)
                    if order is None:
                        continue
                    fill = self.execution.execute(order, bar.close)
                    self.portfolio.on_fill(fill)

            # 5) 所有币种处理完，记录权益快照
            self.portfolio.update_equity(ts)

        # 6. 策略结束回调
        self.strategy.on_finish()

        # 7. 计算指标
        self.metrics = compute_metrics(
            self.portfolio.equity_curve,
            self.portfolio.trade_log,
            self.initial_capital,
            self.bars_per_day,
        )

        # 8. 过滤器统计
        if self.coin_filter is not None:
            skip_stats = self.coin_filter.get_skip_stats()
            if skip_stats:
                total = sum(skip_stats.values())
                print(f"过滤器共跳过 {total} 次开仓信号")
            self.metrics["filter_skip_stats"] = skip_stats

        return self.metrics

    def show_results(self, label: str | None = None) -> None:
        """打印结果摘要。"""
        if label is None:
            label = f"{'测试集' if self.use_test_set else '训练集'} 回测结果"
        print_summary(self.metrics, label)

    def export_results(self, label: str | None = None) -> None:
        """导出结果文件。"""
        if label is None:
            set_tag = "test" if self.use_test_set else "train"
            label = f"{self.interval}_{set_tag}"
        export(
            self.portfolio.equity_curve,
            self.portfolio.trade_log,
            self.metrics,
            label=label,
        )
