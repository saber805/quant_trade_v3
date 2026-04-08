"""Regime-Based 策略回测入口。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtester.engine import BacktestEngine
from backtester.report import plot_equity
from coin_filter import CoinFilter
from strategy import RegimeStrategy


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
    print("  Regime-Based 策略回测")
    print(f"  币种: {len(symbols)}个")
    print(f"  周期: {interval}")
    print(f"  形态: 上升趋势/下降趋势/区间震荡/高波动/突破")
    print("=" * 60)

    # --- 训练集 ---
    strategy_train = RegimeStrategy(symbols)
    engine_train = BacktestEngine(
        strategy=strategy_train,
        symbols=symbols,
        interval=interval,
        use_test_set=False,
        coin_filter=coin_filter,
    )
    engine_train.run()
    engine_train.show_results("Regime 训练集 (75%)")
    engine_train.export_results("regime_train")

    # --- 测试集 ---
    strategy_test = RegimeStrategy(symbols)
    engine_test = BacktestEngine(
        strategy=strategy_test,
        symbols=symbols,
        interval=interval,
        use_test_set=True,
        coin_filter=CoinFilter(),
    )
    engine_test.run()
    engine_test.show_results("Regime 测试集 (25%)")
    engine_test.export_results("regime_test")

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

    # --- 权益曲线图 ---
    plot_equity(
        train_equity=engine_train.portfolio.equity_curve,
        train_metrics=engine_train.metrics,
        test_equity=engine_test.portfolio.equity_curve,
        test_metrics=engine_test.metrics,
        title=f"Regime策略 | {len(symbols)}币种 | {interval}",
    )


if __name__ == "__main__":
    main()
