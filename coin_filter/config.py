"""币种分类与过滤模块配置。"""

# ── 黑名单：手动排除的币种（交易对名称） ──
BLACKLIST: list[str] = [
    # 示例: "LUNAUSDT", "FTTUSDT"
]

# ── 分组阈值 ──
# 按日收益率标准差（年化波动率的代理指标）将币种分为三组
# 阈值会由 CoinClassifier 根据数据自动计算（三分位），也可手动覆盖
VOLATILITY_BOUNDARIES: tuple[float, float] | None = None  # (low_high, high_very_high)

# ── 运行时过滤参数 ──
# 成交量异常：当前Bar成交量 < 滚动均值 × 此比例 → 跳过
VOLUME_ANOMALY_RATIO = 0.10

# 成交量滚动窗口（Bar数）
VOLUME_ROLLING_WINDOW = 48  # 1h周期=2天, 4h周期=8天, 1d周期=48天

# 价格异常：单Bar涨跌幅超过此阈值 → 跳过（避免在极端行情中开新仓）
PRICE_SPIKE_THRESHOLD = 0.15  # 15%
