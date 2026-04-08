"""Regime-Based 主策略 — 继承 StrategyBase，接入回测引擎。"""

import pandas as pd

from backtester.strategy_base import StrategyBase
from backtester.event import BarEvent, SignalEvent, SignalType

from .indicators import compute_all
from .market_classifier import MarketClassifier, Regime
from .trade_manager import TradeManager
from .sub_strategies import (
    UptrendStrategy, DowntrendStrategy, RangingStrategy, BreakoutStrategy,
    ChaoticStrategy,
)


class RegimeStrategy(StrategyBase):

    def __init__(self, symbols: list[str], params: dict | None = None):
        defaults = {
            "adx_trend": 25,
            "adx_no_trend": 20,
            "confirm_bars": 3,
        }
        if params:
            defaults.update(params)
        super().__init__(symbols, defaults)

        self.indicators: dict[str, pd.DataFrame] = {}
        self.regimes: dict[str, pd.Series] = {}

        self.classifier = MarketClassifier(
            adx_trend=defaults["adx_trend"],
            adx_no_trend=defaults["adx_no_trend"],
            confirm_bars=defaults["confirm_bars"],
        )
        self.trade_mgr = TradeManager()

        self.sub_strategies = {
            Regime.UPTREND: UptrendStrategy(),
            Regime.DOWNTREND: DowntrendStrategy(),
            Regime.RANGING: RangingStrategy(),
            Regime.CHAOTIC: ChaoticStrategy(),
            Regime.BREAKOUT: BreakoutStrategy(),
        }

        # 统计
        self.regime_counts: dict[str, int] = {r.value: 0 for r in Regime}
        self.exit_reasons: dict[str, int] = {"SL": 0, "TP": 0, "TRAIL": 0, "REGIME": 0}

    def on_init(self, historical_bars: dict[str, pd.DataFrame]) -> None:
        for symbol, df in historical_bars.items():
            ind = compute_all(df)
            # 前一根K线的 EMA 值（用于交叉检测）
            ind["prev_ema20"] = ind["ema20"].shift(1)
            ind["prev_ema50"] = ind["ema50"].shift(1)
            # 成交量比率（当前/20日均量）
            ind["volume_ratio"] = ind["volume"] / ind["volume"].rolling(20).mean()

            self.indicators[symbol] = ind
            self.regimes[symbol] = self.classifier.classify_series(ind)

    def on_bar(self, bar: BarEvent,
               current_positions: dict[str, float]) -> list[SignalEvent] | None:
        symbol = bar.symbol
        ind = self.indicators.get(symbol)
        if ind is None or bar.datetime not in ind.index:
            return None

        row = ind.loc[bar.datetime]
        # 跳过指标未就绪的K线
        if pd.isna(row.get("adx")) or pd.isna(row.get("atr")):
            return None

        has_position = current_positions.get(symbol, 0) > 0

        # 1. 检查止盈止损
        if has_position:
            exit_reason = self.trade_mgr.check_exits(
                symbol, bar.low, bar.high, bar.close)
            if exit_reason:
                self.trade_mgr.remove(symbol)
                self.exit_reasons[exit_reason] = self.exit_reasons.get(exit_reason, 0) + 1
                return [SignalEvent(symbol, bar.datetime, SignalType.SELL, 1.0)]

            # 2. 更新追踪止损
            self.trade_mgr.update_trailing(symbol, bar.high, row["atr"])

        # 3. 获取当前形态
        regime = self.regimes[symbol].get(bar.datetime, Regime.RANGING)
        self.regime_counts[regime.value] += 1

        # 4. 委托子策略
        sub = self.sub_strategies[regime]
        result = sub.evaluate(bar, row, has_position)

        if result is None:
            return None

        action, strength, sl, tp, trailing = result

        if action == "SELL" and has_position:
            self.trade_mgr.remove(symbol)
            self.exit_reasons["REGIME"] += 1
            return [SignalEvent(symbol, bar.datetime, SignalType.SELL, 1.0)]

        if action == "BUY" and not has_position:
            # 注册交易到 TradeManager
            self.trade_mgr.register(
                symbol, bar.close, bar.datetime, sl, tp, trailing)
            return [SignalEvent(symbol, bar.datetime, SignalType.BUY, strength)]

        return None

    def on_finish(self) -> None:
        total = sum(self.regime_counts.values()) or 1
        print("\n=== Regime 分布 ===")
        for regime, count in self.regime_counts.items():
            print(f"  {regime:12s}: {count:6d} ({count/total*100:.1f}%)")

        print("\n=== 出场原因 ===")
        for reason, count in self.exit_reasons.items():
            print(f"  {reason:6s}: {count}")
