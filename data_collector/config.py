"""数据采集模块配置"""

import os
from datetime import datetime, timedelta, timezone

# 币种列表（主流币，交易对后缀为USDT）
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "UNIUSDT", "ATOMUSDT", "LTCUSDT", "FILUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "NEARUSDT", "SUIUSDT",
]

# K线周期
INTERVALS = ["1h", "4h", "1d"]

# 数据时间范围：最近1年
END_TIME = datetime.now(timezone.utc)
START_TIME = END_TIME - timedelta(days=365)

# 币安API配置
BASE_URL = "https://api.binance.com"
KLINE_ENDPOINT = "/api/v3/klines"
MAX_LIMIT = 1000  # 单次最多返回条数

# 请求频率控制（秒）
REQUEST_INTERVAL = 0.1  # 100ms间隔，远低于限流阈值

# 请求重试
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

# 数据存储路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# K线数据列名
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_buy_volume",
    "taker_buy_quote_volume", "ignore",
]

# 保存到CSV时使用的列
SAVE_COLUMNS = ["open_time", "open", "high", "low", "close", "volume", "close_time"]

# 定时更新配置
# schedule库支持的星期: monday, tuesday, wednesday, thursday, friday, saturday, sunday
SCHEDULE_DAY = "monday"   # 每周一执行
SCHEDULE_TIME = "00:00"   # UTC时间 00:00（北京时间周一早8点）

# 日志路径
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scheduler.log")
