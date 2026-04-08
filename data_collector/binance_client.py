"""币安API客户端 - 封装K线数据请求"""

import time
import requests
import pandas as pd
import config


class BinanceClient:
    """币安公开API客户端，用于获取K线数据"""

    def __init__(self):
        self.session = requests.Session()
        self.base_url = config.BASE_URL

    def fetch_klines(self, symbol: str, interval: str,
                     start_time: int, end_time: int) -> pd.DataFrame:
        """
        获取指定币种和周期的K线数据，自动分页处理。

        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: K线周期，如 "1h", "4h", "1d"
            start_time: 起始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）

        Returns:
            包含K线数据的DataFrame
        """
        all_data = []
        current_start = start_time

        while current_start < end_time:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_time,
                "limit": config.MAX_LIMIT,
            }

            data = self._request_with_retry(params)
            if not data:
                break

            all_data.extend(data)

            # 下一页从最后一条的close_time + 1开始
            last_close_time = data[-1][6]
            current_start = last_close_time + 1

            # 如果返回数据不足limit，说明已到末尾
            if len(data) < config.MAX_LIMIT:
                break

            time.sleep(config.REQUEST_INTERVAL)

        if not all_data:
            return pd.DataFrame(columns=config.SAVE_COLUMNS)

        df = pd.DataFrame(all_data, columns=config.KLINE_COLUMNS)

        # 转换数据类型
        numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume",
                        "taker_buy_volume", "taker_buy_quote_volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(pd.to_numeric(df["open_time"]), unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
        df["close_time"] = pd.to_datetime(pd.to_numeric(df["close_time"]), unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
        df["trades"] = pd.to_numeric(df["trades"])

        return df[config.SAVE_COLUMNS].reset_index(drop=True)

    def _request_with_retry(self, params: dict) -> list:
        """带重试的API请求"""
        url = self.base_url + config.KLINE_ENDPOINT

        for attempt in range(config.MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt < config.MAX_RETRIES - 1:
                    wait = config.RETRY_DELAY * (attempt + 1)
                    print(f"  请求失败({e})，{wait}秒后重试...")
                    time.sleep(wait)
                else:
                    print(f"  请求失败，已达最大重试次数: {e}")
                    raise

    def close(self):
        self.session.close()
