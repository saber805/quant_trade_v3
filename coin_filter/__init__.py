"""币种分类与过滤模块。

提供三个核心能力：
1. CoinClassifier - 基于历史数据将币种按波动率/成交量分组
2. CoinFilter - 运行时逐Bar过滤（流动性异常、价格异常）
3. 黑名单机制 - 手动/自动排除问题币种
"""

from .classifier import CoinClassifier
from .filter import CoinFilter

__all__ = ["CoinClassifier", "CoinFilter"]
