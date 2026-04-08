import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from .config import OUTPUT_DIR


def print_summary(metrics: dict, label: str = "回测结果") -> None:
    """控制台打印绩效摘要。"""
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  初始资金:         ${metrics['initial_capital']:,.2f}")
    print(f"  最终权益:         ${metrics['final_equity']:,.2f}")
    print(f"  总收益率:         {metrics['total_return_pct']:+.2f}%")
    print(f"  年化收益率:       {metrics['annualized_return_pct']:+.2f}%")
    print(f"  最大回撤:         {metrics['max_drawdown_pct']:.2f}%")
    print(f"  回撤持续(bars):   {metrics['max_drawdown_duration_bars']}")
    print(f"  年化波动率:       {metrics['volatility_pct']:.2f}%")
    print(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:.3f}")
    print(f"  Sortino Ratio:    {metrics['sortino_ratio']:.3f}")
    print(f"  Calmar Ratio:     {metrics['calmar_ratio']:.3f}")
    print(f"  ---")
    print(f"  总交易次数:       {metrics['total_trades']}")
    print(f"  胜率:             {metrics['win_rate_pct']:.2f}%")
    print(f"  盈亏比:           {metrics['profit_factor']:.3f}")
    print(f"  平均交易盈亏:     ${metrics['avg_trade_return_pct']:.2f}")
    print(f"  最大连续亏损:     {metrics['max_consecutive_losses']}")
    print(f"{'='*50}\n")


def export(equity_curve: list[dict], trade_log: list[dict],
           metrics: dict, label: str = "backtest",
           output_dir: Path = OUTPUT_DIR) -> None:
    """导出回测结果到CSV和JSON文件。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 权益曲线 CSV
    eq_path = output_dir / f"{label}_equity.csv"
    if equity_curve:
        fields = list(equity_curve[0].keys())
        with open(eq_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(equity_curve)
        print(f"  权益曲线已导出: {eq_path}")

    # 交易日志 CSV
    trades_path = output_dir / f"{label}_trades.csv"
    if trade_log:
        fields = list(trade_log[0].keys())
        with open(trades_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(trade_log)
        print(f"  交易日志已导出: {trades_path}")

    # 指标 JSON
    metrics_path = output_dir / f"{label}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"  绩效指标已导出: {metrics_path}")


def plot_equity(train_equity: list[dict], train_metrics: dict,
                test_equity: list[dict], test_metrics: dict,
                title: str = "策略回测",
                output_dir: Path = OUTPUT_DIR) -> None:
    """将训练集和测试集权益曲线绘制在同一张图上并保存为PNG。

    上图：权益曲线（蓝=训练集，橙=测试集，竖线=分割点）
    下图：回撤曲线
    """
    if not train_equity and not test_equity:
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    df_train = pd.DataFrame(train_equity)
    df_train["datetime"] = pd.to_datetime(df_train["datetime"])
    df_test = pd.DataFrame(test_equity)
    df_test["datetime"] = pd.to_datetime(df_test["datetime"])

    initial = train_metrics.get("initial_capital", 10000)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                    height_ratios=[3, 1], sharex=True)

    # ── 上图：权益曲线 ──
    train_ret = train_metrics.get("total_return_pct", 0)
    test_ret = test_metrics.get("total_return_pct", 0)

    ax1.plot(df_train["datetime"], df_train["total_equity"],
             color="#2196F3", linewidth=1.2,
             label=f"训练集 ({train_ret:+.2f}%)")
    ax1.plot(df_test["datetime"], df_test["total_equity"],
             color="#FF9800", linewidth=1.2,
             label=f"测试集 ({test_ret:+.2f}%)")

    # 分割线
    split_time = df_test["datetime"].iloc[0]
    ax1.axvline(x=split_time, color="red", linestyle="--",
                linewidth=0.9, alpha=0.7, label="训练/测试分割")

    # 初始资金线
    ax1.axhline(y=initial, color="gray", linestyle="--",
                linewidth=0.8, alpha=0.5)

    # 末端标注收益率
    ax1.annotate(f"{train_ret:+.2f}%",
                 xy=(df_train["datetime"].iloc[-1],
                     df_train["total_equity"].iloc[-1]),
                 fontsize=9, color="#2196F3", fontweight="bold",
                 xytext=(5, 0), textcoords="offset points")
    ax1.annotate(f"{test_ret:+.2f}%",
                 xy=(df_test["datetime"].iloc[-1],
                     df_test["total_equity"].iloc[-1]),
                 fontsize=9, color="#FF9800", fontweight="bold",
                 xytext=(5, 0), textcoords="offset points")

    ax1.set_ylabel("权益 (USDT)")
    ax1.set_title(title, fontsize=14, fontweight="bold")
    ax1.legend(loc="best", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 副标题：关键指标对比
    train_s = train_metrics.get("sharpe_ratio", 0)
    test_s = test_metrics.get("sharpe_ratio", 0)
    train_mdd = train_metrics.get("max_drawdown_pct", 0)
    test_mdd = test_metrics.get("max_drawdown_pct", 0)
    info = (f"Sharpe: 训练={train_s:.3f} / 测试={test_s:.3f}  |  "
            f"MaxDD: 训练={train_mdd:.1f}% / 测试={test_mdd:.1f}%")
    ax1.text(0.5, 0.97, info, transform=ax1.transAxes,
             fontsize=8, color="gray", ha="center", va="top")

    # ── 下图：回撤曲线 ──
    for df, color, label in [
        (df_train, "#2196F3", "训练集"),
        (df_test, "#FF9800", "测试集"),
    ]:
        peak = df["total_equity"].cummax()
        dd = (df["total_equity"] - peak) / peak * 100
        ax2.fill_between(df["datetime"], dd, 0, color=color, alpha=0.2)
        ax2.plot(df["datetime"], dd, color=color, linewidth=0.8, label=label)

    ax2.axvline(x=split_time, color="red", linestyle="--",
                linewidth=0.9, alpha=0.7)
    ax2.set_ylabel("回撤 (%)")
    ax2.set_xlabel("日期")
    ax2.legend(loc="lower left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate(rotation=30)

    plt.tight_layout()
    png_path = output_dir / "equity_curve.png"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  权益曲线图已保存: {png_path}")
