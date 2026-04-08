import pandas as pd
from pathlib import Path

from .config import DATA_DIR, TRAIN_RATIO


def load(symbol: str, interval: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """加载单个币种的CSV数据，返回以datetime为索引的DataFrame。"""
    file_path = data_dir / interval / f"{symbol}.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {file_path}")

    df = pd.read_csv(file_path)
    # 兼容毫秒时间戳和 "YYYY-MM-DD HH:MM:SS" 两种格式
    raw = df["open_time"]
    if pd.api.types.is_numeric_dtype(raw):
        df["datetime"] = pd.to_datetime(raw, unit="ms")
    else:
        df["datetime"] = pd.to_datetime(raw)
    df = df.set_index("datetime")
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df.attrs["symbol"] = symbol
    return df


def load_multiple(symbols: list[str], interval: str,
                  data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """加载多个币种的数据。"""
    result = {}
    for symbol in symbols:
        result[symbol] = load(symbol, interval, data_dir)
    return result


def split(df: pd.DataFrame, train_ratio: float = TRAIN_RATIO
          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按行数比例分割为训练集和测试集。"""
    split_idx = int(len(df) * train_ratio)
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()
