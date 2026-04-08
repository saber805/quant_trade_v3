"""数据采集入口脚本"""

import argparse
from datetime import datetime, timedelta, timezone
from collector import DataCollector
import config


def parse_args():
    parser = argparse.ArgumentParser(description="币安K线数据采集工具")

    parser.add_argument(
        "-s", "--symbols",
        nargs="+",
        help="指定币种（如 BTCUSDT ETHUSDT），默认采集全部主流币",
    )
    parser.add_argument(
        "-i", "--intervals",
        nargs="+",
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        help="指定K线周期（如 1h 4h），默认: 1h 4h 1d",
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=365,
        help="采集最近N天的数据，默认365天",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    symbols = args.symbols
    intervals = args.intervals

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=args.days)

    # 如果指定了币种但没有USDT后缀，自动补上
    if symbols:
        symbols = [s if s.endswith("USDT") else s + "USDT" for s in symbols]

    collector = DataCollector(
        symbols=symbols,
        intervals=intervals,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        collector.run()
    finally:
        collector.close()


if __name__ == "__main__":
    main()
