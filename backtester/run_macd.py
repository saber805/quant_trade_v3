"""
MACD策略回测 — 经典MACD交叉 + 零轴过滤。

信号逻辑：
- MACD线上穿信号线 且 MACD柱状图 > 0（零轴之上）→ 买入
- MACD线下穿信号线 → 卖出（不要求零轴条件，及时止损）

参数：
- fast_ema: 快线EMA周期（默认12）
- slow_ema: 慢线EMA周期（默认26）
- signal_period: 信号线周期（默认9）
- strength: 每次开仓使用的资金比例（默认0.1 = 10%）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from backtester.engine import BacktestEngine
from backtester.event import BarEvent, SignalEvent, SignalType
from backtester.strategy_base import StrategyBase
from backtester.report import plot_equity
from coin_filter import CoinFilter


class MACDStrategy(StrategyBase):
    """MACD交叉策略，带零轴过滤。"""

    def __init__(self, symbols, params=None):
        defaults = {
            "fast_ema": 12,
            "slow_ema": 26,
            "signal_period": 9,
            "strength": 0.1,
        }
        if params:
            defaults.update(params)
        super().__init__(symbols, defaults)
        self.indicators: dict[str, pd.DataFrame] = {}

    def on_init(self, historical_bars: dict[str, pd.DataFrame]) -> None:
        fast = self.params["fast_ema"]
        slow = self.params["slow_ema"]
        sig = self.params["signal_period"]

        for sym, df in historical_bars.items():
            close = df["close"]
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=sig, adjust=False).mean()
            histogram = macd_line - signal_line

            ind = pd.DataFrame(index=df.index)
            ind["macd"] = macd_line
            ind["signal"] = signal_line
            ind["hist"] = histogram
            self.indicators[sym] = ind

    def on_bar(self, bar: BarEvent,
               current_positions: dict[str, float]) -> list[SignalEvent] | None:
        ind = self.indicators.get(bar.symbol)
        if ind is None or bar.datetime not in ind.index:
            return None

        idx = ind.index.get_loc(bar.datetime)
        if idx < 1:
            return None

        cur = ind.iloc[idx]
        prev = ind.iloc[idx - 1]

        if pd.isna(cur["macd"]) or pd.isna(prev["macd"]):
            return None

        # 买入：MACD上穿信号线 + 柱状图为正（零轴之上确认趋势）
        if (prev["macd"] <= prev["signal"]
                and cur["macd"] > cur["signal"]
                and cur["hist"] > 0):
            return [SignalEvent(
                symbol=bar.symbol,
                datetime=bar.datetime,
                signal_type=SignalType.BUY,
                strength=self.params["strength"],
            )]

        # 卖出：MACD下穿信号线（不要求零轴条件，快速离场）
        if (prev["macd"] >= prev["signal"]
                and cur["macd"] < cur["signal"]):
            return [SignalEvent(
                symbol=bar.symbol,
                datetime=bar.datetime,
                signal_type=SignalType.SELL,
                strength=1.0,
            )]

        return None


def main():
    symbols = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "UNIUSDT", "ATOMUSDT", "LTCUSDT", "FILUSDT",
        "APTUSDT", "ARBUSDT", "OPUSDT", "NEARUSDT", "SUIUSDT",
    ]
    interval = "1h"
    coin_filter = CoinFilter()

    print("=" * 60)
    print("  MACD策略回测")
    print(f"  币种: {len(symbols)}个")
    print(f"  周期: {interval}")
    print(f"  参数: EMA(12,26), Signal(9), 零轴过滤")
    print("=" * 60)

    # --- 训练集 ---
    engine_train = BacktestEngine(
        strategy=MACDStrategy(symbols),
        symbols=symbols,
        interval=interval,
        use_test_set=False,
        coin_filter=coin_filter,
    )
    engine_train.run()
    engine_train.show_results("MACD 训练集 (75%)")
    engine_train.export_results("macd_train")

    # --- 测试集 ---
    coin_filter_test = CoinFilter()
    engine_test = BacktestEngine(
        strategy=MACDStrategy(symbols),
        symbols=symbols,
        interval=interval,
        use_test_set=True,
        coin_filter=coin_filter_test,
    )
    engine_test.run()
    engine_test.show_results("MACD 测试集 (25%)")
    engine_test.export_results("macd_test")

    # --- 对比 ---
    print("\n" + "=" * 60)
    print("  训练集 vs 测试集 对比")
    print("=" * 60)
    t1 = engine_train.metrics
    t2 = engine_test.metrics
    for key in ["total_return_pct", "sharpe_ratio", "max_drawdown_pct",
                "win_rate_pct", "total_trades", "profit_factor"]:
        v1 = t1.get(key, "N/A")
        v2 = t2.get(key, "N/A")
        print(f"  {key:30s}  训练={str(v1):<12s}  测试={v2}")
    print("=" * 60)

    # --- 权益曲线图（训练集+测试集合并） ---
    plot_equity(
        train_equity=engine_train.portfolio.equity_curve,
        train_metrics=engine_train.metrics,
        test_equity=engine_test.portfolio.equity_curve,
        test_metrics=engine_test.metrics,
        title=f"MACD策略 | {len(symbols)}币种 | {interval} | EMA(12,26) Signal(9)",
    )


if __name__ == "__main__":
    main()
