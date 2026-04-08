"""数据采集主逻辑 - 批量采集、断点续传"""

import os
import pandas as pd
from binance_client import BinanceClient
import config


class DataCollector:
    """批量采集K线数据并存储为CSV"""

    def __init__(self, symbols=None, intervals=None,
                 start_time=None, end_time=None):
        self.symbols = symbols or config.SYMBOLS
        self.intervals = intervals or config.INTERVALS
        self.start_time = start_time or config.START_TIME
        self.end_time = end_time or config.END_TIME
        self.client = BinanceClient()

    def run(self):
        """执行完整采集流程"""
        total = len(self.symbols) * len(self.intervals)
        completed = 0
        failed = []

        print(f"开始采集数据: {len(self.symbols)}个币种 × {len(self.intervals)}个周期 = {total}个任务")
        print(f"时间范围: {self.start_time.strftime('%Y-%m-%d')} ~ {self.end_time.strftime('%Y-%m-%d')}")
        print("-" * 60)

        for interval in self.intervals:
            # 确保目录存在
            interval_dir = os.path.join(config.DATA_DIR, interval)
            os.makedirs(interval_dir, exist_ok=True)

            for symbol in self.symbols:
                completed += 1
                print(f"[{completed}/{total}] {symbol} {interval} ... ", end="", flush=True)

                try:
                    self._collect_symbol(symbol, interval, interval_dir)
                except Exception as e:
                    print(f"失败: {e}")
                    failed.append((symbol, interval, str(e)))

        print("-" * 60)
        print(f"采集完成: 成功 {total - len(failed)}/{total}")
        if failed:
            print(f"失败列表:")
            for symbol, interval, err in failed:
                print(f"  {symbol} {interval}: {err}")

    def _collect_symbol(self, symbol: str, interval: str, interval_dir: str):
        """采集单个币种单个周期的数据，始终获取最近1年完整数据。"""
        filepath = os.path.join(interval_dir, f"{symbol}.csv")

        start_ms = int(self.start_time.timestamp() * 1000)
        end_ms = int(self.end_time.timestamp() * 1000)

        # 直接拉取完整时间范围的数据
        df = self.client.fetch_klines(symbol, interval, start_ms, end_ms)

        if df.empty:
            print("无数据")
            return

        df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time")
        df.to_csv(filepath, index=False)
        print(f"{len(df)}条")

    def close(self):
        self.client.close()
