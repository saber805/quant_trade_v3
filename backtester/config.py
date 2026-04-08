from pathlib import Path

# 费率
DEFAULT_COMMISSION_RATE = 0.001    # 币安Taker费率 0.1%
DEFAULT_SLIPPAGE_RATE = 0.0005     # 滑点 0.05%

# 资金
DEFAULT_INITIAL_CAPITAL = 10000    # USDT

# 数据分割
TRAIN_RATIO = 0.75

# 路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
OUTPUT_DIR = BASE_DIR / "output"

# 年化天数（加密市场全年无休）
ANNUAL_TRADING_DAYS = 365
