import numpy as np

from .config import ANNUAL_TRADING_DAYS


def compute(equity_curve: list[dict], trade_log: list[dict],
            initial_capital: float, bars_per_day: float = 1.0) -> dict:
    """计算全部绩效指标。

    Args:
        equity_curve: 权益快照列表 [{datetime, total_equity, ...}]
        trade_log: 交易记录列表
        initial_capital: 初始资金
        bars_per_day: 每天的Bar数（1h=24, 4h=6, 1d=1），用于年化计算
    """
    if not equity_curve:
        return _empty_metrics()

    equities = np.array([e["total_equity"] for e in equity_curve], dtype=float)
    n_bars = len(equities)
    n_days = n_bars / bars_per_day if bars_per_day > 0 else n_bars

    # --- 收益率 ---
    final_equity = equities[-1]
    total_return_pct = (final_equity / initial_capital - 1) * 100
    if n_days > 0:
        annualized_return_pct = (
            ((final_equity / initial_capital) ** (ANNUAL_TRADING_DAYS / n_days) - 1)
            * 100
        )
    else:
        annualized_return_pct = 0.0

    # --- 回撤 ---
    peak = np.maximum.accumulate(equities)
    drawdown = (peak - equities) / peak
    max_drawdown_pct = float(np.max(drawdown)) * 100 if len(drawdown) > 0 else 0.0

    # 最大回撤持续期（bar数）
    max_dd_duration = _max_drawdown_duration(equities)

    # --- 日收益率序列（按bars_per_day聚合） ---
    bar_returns = np.diff(equities) / equities[:-1] if len(equities) > 1 else np.array([])
    # 用bar级收益率近似
    volatility = float(np.std(bar_returns) * np.sqrt(ANNUAL_TRADING_DAYS * bars_per_day)) * 100 if len(bar_returns) > 0 else 0.0

    # --- Sharpe / Sortino / Calmar ---
    mean_bar_return = float(np.mean(bar_returns)) if len(bar_returns) > 0 else 0.0
    std_bar_return = float(np.std(bar_returns)) if len(bar_returns) > 0 else 0.0
    annualized_mean = mean_bar_return * ANNUAL_TRADING_DAYS * bars_per_day
    annualized_std = std_bar_return * np.sqrt(ANNUAL_TRADING_DAYS * bars_per_day)

    sharpe_ratio = annualized_mean / annualized_std if annualized_std > 0 else 0.0

    downside = bar_returns[bar_returns < 0]
    downside_std = float(np.std(downside) * np.sqrt(ANNUAL_TRADING_DAYS * bars_per_day)) if len(downside) > 0 else 0.0
    sortino_ratio = annualized_mean / downside_std if downside_std > 0 else 0.0

    calmar_ratio = (annualized_return_pct / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0

    # --- 交易统计 ---
    trade_stats = _compute_trade_stats(trade_log)

    return {
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "max_drawdown_duration_bars": max_dd_duration,
        "volatility_pct": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "sortino_ratio": round(sortino_ratio, 3),
        "calmar_ratio": round(calmar_ratio, 3),
        **trade_stats,
    }


def _max_drawdown_duration(equities: np.ndarray) -> int:
    """计算最大回撤持续期（从峰值到恢复的bar数）。"""
    peak = equities[0]
    duration = 0
    max_duration = 0
    for val in equities:
        if val >= peak:
            peak = val
            duration = 0
        else:
            duration += 1
            max_duration = max(max_duration, duration)
    return max_duration


def _compute_trade_stats(trade_log: list[dict]) -> dict:
    """从交易日志计算交易统计。配对买卖计算盈亏。"""
    if not trade_log:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "avg_trade_return_pct": 0.0,
            "max_consecutive_losses": 0,
        }

    # 配对交易：跟踪每个symbol的买入成本
    open_trades: dict[str, list] = {}  # symbol -> [(qty, price)]
    pnl_list: list[float] = []

    for t in trade_log:
        sym = t["symbol"]
        if t["direction"] == "BUY":
            if sym not in open_trades:
                open_trades[sym] = []
            open_trades[sym].append((t["quantity"], t["price"], t["commission"]))
        elif t["direction"] == "SELL":
            if sym in open_trades and open_trades[sym]:
                # 计算配对盈亏
                entries = open_trades.pop(sym, [])
                total_cost = sum(q * p + c for q, p, c in entries)
                sell_revenue = t["quantity"] * t["price"] - t["commission"]
                pnl_list.append(sell_revenue - total_cost)

    total_trades = len(pnl_list)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "avg_trade_return_pct": 0.0,
            "max_consecutive_losses": 0,
        }

    wins = [p for p in pnl_list if p > 0]
    losses = [p for p in pnl_list if p <= 0]
    win_rate = len(wins) / total_trades * 100
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_return = sum(pnl_list) / total_trades

    # 最大连续亏损
    max_consec = 0
    cur_consec = 0
    for p in pnl_list:
        if p <= 0:
            cur_consec += 1
            max_consec = max(max_consec, cur_consec)
        else:
            cur_consec = 0

    return {
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_trade_return_pct": round(avg_return, 2),
        "max_consecutive_losses": max_consec,
    }


def _empty_metrics() -> dict:
    return {
        "initial_capital": 0,
        "final_equity": 0,
        "total_return_pct": 0.0,
        "annualized_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "max_drawdown_duration_bars": 0,
        "volatility_pct": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "calmar_ratio": 0.0,
        "total_trades": 0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "avg_trade_return_pct": 0.0,
        "max_consecutive_losses": 0,
    }
