"""币种分类器：基于历史数据将币种分为低/中/高波动率三组。"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from .config import BLACKLIST, VOLATILITY_BOUNDARIES


# 分组名称常量
GROUP_LOW = "low_vol"
GROUP_MID = "mid_vol"
GROUP_HIGH = "high_vol"


@dataclass
class CoinProfile:
    """单个币种的统计画像。"""
    symbol: str
    volatility: float       # 日收益率标准差
    avg_daily_volume: float  # 日均成交量（以base资产计）
    group: str = ""          # 分组标签


@dataclass
class ClassifyResult:
    """分类结果。"""
    profiles: dict[str, CoinProfile] = field(default_factory=dict)
    groups: dict[str, list[str]] = field(default_factory=dict)  # group -> [symbols]
    boundaries: tuple[float, float] = (0.0, 0.0)

    def get_group(self, symbol: str) -> str:
        """获取币种所属分组。"""
        p = self.profiles.get(symbol)
        return p.group if p else ""

    def get_symbols(self, group: str) -> list[str]:
        """获取某分组下的所有币种。"""
        return self.groups.get(group, [])

    def summary(self) -> str:
        """打印分组摘要。"""
        lines = ["═══ 币种分组结果 ═══"]
        for g in [GROUP_LOW, GROUP_MID, GROUP_HIGH]:
            syms = self.groups.get(g, [])
            lines.append(f"\n【{g}】({len(syms)}个)")
            for s in syms:
                p = self.profiles[s]
                lines.append(f"  {s:<12s}  vol={p.volatility:.4f}  avg_vol={p.avg_daily_volume:,.0f}")
        return "\n".join(lines)


class CoinClassifier:
    """根据历史K线数据对币种进行波动率分组。

    用法::

        classifier = CoinClassifier()
        result = classifier.classify(historical_data)  # {symbol: DataFrame}
        print(result.summary())
        low_vol_coins = result.get_symbols("low_vol")
    """

    def __init__(self, blacklist: list[str] | None = None,
                 boundaries: tuple[float, float] | None = None):
        self.blacklist = set(blacklist or BLACKLIST)
        self.manual_boundaries = boundaries or VOLATILITY_BOUNDARIES

    def classify(self, data: dict[str, pd.DataFrame]) -> ClassifyResult:
        """对所有币种计算统计指标并分组。

        Parameters
        ----------
        data : dict[str, DataFrame]
            {symbol: OHLCV DataFrame}，与回测引擎使用的格式一致。

        Returns
        -------
        ClassifyResult
        """
        profiles: dict[str, CoinProfile] = {}

        for symbol, df in data.items():
            if symbol in self.blacklist:
                continue
            if len(df) < 30:  # 数据太少，跳过
                continue

            returns = df["close"].pct_change().dropna()
            volatility = float(returns.std())
            avg_volume = float(df["volume"].mean())

            profiles[symbol] = CoinProfile(
                symbol=symbol,
                volatility=volatility,
                avg_daily_volume=avg_volume,
            )

        # 确定分组边界
        vols = np.array([p.volatility for p in profiles.values()])
        if self.manual_boundaries:
            low_hi, hi_lo = self.manual_boundaries
        else:
            low_hi = float(np.percentile(vols, 33))
            hi_lo = float(np.percentile(vols, 67))

        # 分配分组
        groups: dict[str, list[str]] = {
            GROUP_LOW: [], GROUP_MID: [], GROUP_HIGH: [],
        }
        for p in profiles.values():
            if p.volatility <= low_hi:
                p.group = GROUP_LOW
            elif p.volatility <= hi_lo:
                p.group = GROUP_MID
            else:
                p.group = GROUP_HIGH
            groups[p.group].append(p.symbol)

        return ClassifyResult(
            profiles=profiles,
            groups=groups,
            boundaries=(low_hi, hi_lo),
        )
