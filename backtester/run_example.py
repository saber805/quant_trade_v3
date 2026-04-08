"""
SMA交叉策略示例 — 演示回测引擎完整流程。

双均线交叉策略：
- 短期SMA上穿长期SMA → 买入信号
- 短期SMA下穿长期SMA → 卖出信号
"""
import sys
from pathlib import Path

# 确保可以导入backtester包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from backtester.engine import BacktestEngine
from backtester.event import BarEvent, SignalEvent, SignalType
from backtester.strategy_base import StrategyBase
from backtester.report import plot_equity


class SMAStrategy(StrategyBase):
    """简单双均线交叉策略。"""

    def __init__(self, symbols, params=None):
        defaults = {"fast_period": 10, "slow_period": 30}
        if params:
            defaults.update(params)
        super().__init__(symbols, defaults)
        self.indicators: dict[str, pd.DataFrame] = {}

    def on_init(self, historical_bars: dict[str, pd.DataFrame]) -> None:
        """预计算所有币种的SMA指标。"""
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        for sym, df in historical_bars.items():
            ind = pd.DataFrame(index=df.index)
            ind["sma_fast"] = df["close"].rolling(fast).mean()
            ind["sma_slow"] = df["close"].rolling(slow).mean()
            self.indicators[sym] = ind

    def on_bar(self, bar: BarEvent,
               current_positions: dict[str, float]) -> list[SignalEvent] | None:
        """查表判断金叉/死叉。"""
        ind = self.indicators.get(bar.symbol)
        if ind is None or bar.datetime not in ind.index:
            return None

        row = ind.loc[bar.datetime]
        if pd.isna(row["sma_fast"]) or pd.isna(row["sma_slow"]):
            return None

        # 需要前一根bar来判断交叉
        idx = ind.index.get_loc(bar.datetime)
        if idx < 1:
            return None
        prev = ind.iloc[idx - 1]
        if pd.isna(prev["sma_fast"]) or pd.isna(prev["sma_slow"]):
            return None

        # 金叉：fast从下穿上
        if prev["sma_fast"] <= prev["sma_slow"] and row["sma_fast"] > row["sma_slow"]:
            return [SignalEvent(
                symbol=bar.symbol,
                datetime=bar.datetime,
                signal_type=SignalType.BUY,
                strength=0.1,  # 每个信号用10%资金
            )]

        # 死叉：fast从上穿下
        if prev["sma_fast"] >= prev["sma_slow"] and row["sma_fast"] < row["sma_slow"]:
            return [SignalEvent(
                symbol=bar.symbol,
                datetime=bar.datetime,
                signal_type=SignalType.SELL,
                strength=1.0,
            )]

        return None


def main():
    # 选择几个主流币测试
    symbols = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", 
    "UNIUSDT", "ATOMUSDT", "LTCUSDT", "FILUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "NEARUSDT", "SUIUSDT",
    ]
    interval = "1h"

    print("=" * 60)
    print("   策略回测示例")
    print(f"  币种: {', '.join(symbols)}")
    print(f"  周期: {interval}")
    print(f"  参数: fast=10, slow=30")
    print("=" * 60)

    # --- 训练集回测 (75%) ---
    strategy_train = SMAStrategy(symbols, {"fast_period": 10, "slow_period": 30})
    engine_train = BacktestEngine(
        strategy=strategy_train,
        symbols=symbols,
        interval=interval,
        use_test_set=False,
    )
    engine_train.run()
    engine_train.show_results("训练集 (75%) 回测结果")
    engine_train.export_results("sma_train")

    # --- 测试集回测 (25%) ---
    strategy_test = SMAStrategy(symbols, {"fast_period": 10, "slow_period": 30})
    engine_test = BacktestEngine(
        strategy=strategy_test,
        symbols=symbols,
        interval=interval,
        use_test_set=True,
    )
    engine_test.run()
    engine_test.show_results("测试集 (25%) 回测结果")
    engine_test.export_results("sma_test")

    # --- 对比 ---
    print("\n" + "=" * 60)
    print("  训练集 vs 测试集 对比")
    print("=" * 60)
    t1 = engine_train.metrics
    t2 = engine_test.metrics
    for key in ["total_return_pct", "sharpe_ratio", "max_drawdown_pct",
                 "win_rate_pct", "total_trades"]:
        print(f"  {key:30s}  训练={t1[key]:<12}  测试={t2[key]}")
    print("=" * 60)
    print("\n注意：测试集表现不应明显优于训练集，否则可能存在过拟合问题。")

    # --- 权益曲线图 ---
    plot_equity(
        train_equity=engine_train.portfolio.equity_curve,
        train_metrics=engine_train.metrics,
        test_equity=engine_test.portfolio.equity_curve,
        test_metrics=engine_test.metrics,
        title=f"SMA交叉策略 | {len(symbols)}币种 | {interval} | fast=10, slow=30",
    )


if __name__ == "__main__":
    main()
