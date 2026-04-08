"""示例：币种分类 + 过滤器集成回测。

运行: python -m coin_filter.example
"""

import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtester import data_loader
from backtester.config import DATA_DIR
from coin_filter.classifier import CoinClassifier, GROUP_LOW, GROUP_MID, GROUP_HIGH
from coin_filter.filter import CoinFilter


def _available_symbols(interval: str = "1d") -> list[str]:
    """扫描数据目录，返回实际存在的币种列表。"""
    data_path = DATA_DIR / interval
    return sorted(p.stem for p in data_path.glob("*.csv"))


def main():
    print("=" * 60)
    print("  币种分类与过滤器示例")
    print("=" * 60)

    # 1. 加载日线数据用于分类
    print("\n加载日线数据...")
    symbols = _available_symbols("1d")
    data = data_loader.load_multiple(symbols, "1d")
    print(f"已加载 {len(data)} 个币种")

    # 2. 分类
    classifier = CoinClassifier()
    result = classifier.classify(data)
    print(result.summary())

    # 3. 打印分组边界
    lo, hi = result.boundaries
    print(f"\n波动率分组边界: low/mid={lo:.4f}, mid/high={hi:.4f}")

    # 4. 展示如何为不同分组设置不同策略参数
    group_params = {
        GROUP_LOW:  {"fast_period": 10, "slow_period": 30},  # 稳定币用短周期
        GROUP_MID:  {"fast_period": 15, "slow_period": 45},
        GROUP_HIGH: {"fast_period": 20, "slow_period": 60},  # 高波动用长周期
    }
    print("\n推荐策略参数:")
    for group, params in group_params.items():
        syms = result.get_symbols(group)
        print(f"  {group}: {params}  → {syms}")

    # 5. 创建过滤器并预热
    filt = CoinFilter()
    filt.warm_up(data)
    print(f"\n过滤器已预热，黑名单: {filt.blacklist or '(空)'}")

    # 6. 模拟几个Bar的过滤判断
    print("\n模拟过滤判断:")
    test_sym = symbols[0]
    df = data[test_sym]
    for i in range(-5, 0):
        row = df.iloc[i]
        skip = filt.should_skip(test_sym, float(row["close"]), float(row["volume"]))
        print(f"  {test_sym} {df.index[i].strftime('%Y-%m-%d')} "
              f"close={row['close']:.2f} vol={row['volume']:.0f} → {'跳过' if skip else '正常'}")

    print("\n完成。")


if __name__ == "__main__":
    main()
