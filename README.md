# 加密货币量化交易系统

通用策略扫描全市场的量化回测框架。支持多币种、多周期、事件驱动回测，内置币种分类过滤和绩效评估。

## 项目结构

```
quant_trade/
├── data_collector/              # 数据采集模块
│   ├── config.py                # 币种列表、API配置、调度参数
│   ├── binance_client.py        # 币安REST API封装
│   ├── collector.py             # 历史K线采集、增量更新
│   ├── scheduler.py             # 定时调度（每周一UTC 00:00）
│   └── run.py                   # 采集入口脚本
│
├── data/                        # K线数据存储
│   ├── 1h/                      # 1小时K线 (每币种约8761条)
│   ├── 4h/                      # 4小时K线 (每币种约2190条)
│   └── 1d/                      # 日K线 (每币种约365条)
│       └── {SYMBOL}.csv         # 列: open_time,open,high,low,close,volume,close_time
│
├── backtester/                  # 回测引擎
│   ├── config.py                # 回测参数（费率、资金、路径）
│   ├── event.py                 # 事件数据模型
│   ├── data_loader.py           # CSV加载、训练/测试分割
│   ├── strategy_base.py         # 策略抽象基类
│   ├── portfolio.py             # 持仓管理、信号→订单转换
│   ├── execution.py             # 模拟成交（滑点+手续费）
│   ├── metrics.py               # 绩效指标计算
│   ├── report.py                # 控制台输出、CSV/JSON导出、权益曲线图
│   ├── engine.py                # 主事件循环编排
│   ├── run_example.py           # SMA交叉策略示例
│   └── output/                  # 回测输出文件
│
├── coin_filter/                 # 币种分类与过滤
│   ├── config.py                # 黑名单、波动率阈值、过滤参数
│   ├── classifier.py            # 波动率三分组
│   └── filter.py                # 运行时异常过滤
│
├── strategy/                    # Regime-Based 策略
│   ├── indicators.py            # 技术指标库（EMA/ADX/BB/RSI/ATR/ROC）
│   ├── market_classifier.py     # 市场形态分类器（4种形态+确认过滤）
│   ├── trade_manager.py         # 止盈止损管理器（固定SL/TP+追踪止损）
│   ├── regime_strategy.py       # 主策略（继承StrategyBase，编排子策略）
│   └── sub_strategies/          # 4个子策略
│       ├── base.py              # 子策略抽象基类
│       ├── uptrend.py           # 上升趋势：EMA交叉+ATR追踪止损
│       ├── downtrend.py         # 下降趋势：现货空仓
│       ├── ranging.py           # 区间震荡：BB+RSI均值回归
│       └── breakout.py          # 突破：波动率扩张+动量确认
│
├── run_regime.py                # Regime策略回测入口
├── requirements.txt             # 依赖: pandas, numpy, requests, schedule, matplotlib
└── progress.md                  # 项目进度跟踪
```

## 币种覆盖

19个主流币种，均为USDT交易对：

```
BTC  ETH  BNB  SOL  XRP  ADA  DOGE  AVAX  DOT  LINK
UNI  ATOM LTC  FIL  APT  ARB  OP    NEAR  SUI
```

---

## 完整数据流

下面是从原始CSV到最终报告的完整流程，标注了每一步调用的函数和计算内容。

```
                        ┌──────────────────────────────────┐
                        │  CSV 文件                         │
                        │  data/{1h,4h,1d}/{SYMBOL}.csv    │
                        │  列: open_time, OHLCV, close_time│
                        └───────────────┬──────────────────┘
                                        │
                        ┌───────────────▼──────────────────┐
                        │  data_loader.load()               │
                        │  · pd.read_csv() 读取CSV          │
                        │  · open_time(ms) → datetime索引   │
                        │  · 保留 [open,high,low,close,vol] │
                        │  · 存入 df.attrs["symbol"]        │
                        └───────────────┬──────────────────┘
                                        │
                        ┌───────────────▼──────────────────┐
                        │  data_loader.load_multiple()      │
                        │  · 循环调用 load()                 │
                        │  · 返回 {symbol: DataFrame}       │
                        └───────────────┬──────────────────┘
                                        │
                        ┌───────────────▼──────────────────┐
                        │  data_loader.split()              │
                        │  · 按行数比例切分                   │
                        │  · 前75% → train_df (训练集)       │
                        │  · 后25% → test_df  (测试集)       │
                        │  · active_data = 选中的那一份       │
                        │  · full_data   = 完整历史           │
                        └───────────────┬──────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────────┐
│ strategy.on_init()   │ │ coin_filter.warm_up() │ │ 对齐时间戳                │
│ · 接收 full_data     │ │ · 取每币种最后48条vol │ │ · 合并所有active_data索引 │
│ · 调用               │ │   填入 _volume_buf    │ │ · 排序去重                │
│   indicators.        │ │ · 记录最后收盘价      │ │ · 得到统一时间线          │
│   compute_all(df)    │ │   到 _last_close      │ └──────────────────────────┘
│   计算全部技术指标    │ └──────────────────────┘
│   (详见下方指标表)    │
│ · 追加辅助列:         │
│   prev_ema20/50(交叉) │
│   volume_ratio(放量)  │
│ · 调用 classifier.   │
│   classify_series()  │
│   识别市场形态        │
│   (详见下方形态分类)  │
│ · 结果存入:           │
│   indicators[sym]    │
│   regimes[sym]       │
└──────────────────────┘
              │
              └─────────────────────────┬─────────────────────────┘
                                        │
                                        ▼
              ┌─────────────────────────────────────────────────────┐
              │                                                     │
              │              ═══ 主事件循环 ═══                      │
              │         for ts in all_timestamps:                   │
              │           for sym in symbols:                       │
              │                                                     │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ① 构造 BarEvent                                │ │
              │  │    从 active_data[sym].loc[ts] 取一行           │ │
              │  │    封装为 BarEvent(symbol, datetime,            │ │
              │  │                    open, high, low, close, vol) │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ② portfolio.update_price(sym, close)           │ │
              │  │    更新 _latest_prices[sym] = close             │ │
              │  │    用于后续计算下单数量和权益                      │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ③ strategy.on_bar(bar, positions)              │ │
              │  │    查表获取预计算指标和当前市场形态                │ │
              │  │                                                 │ │
              │  │    A. 检查止盈止损 (TradeManager)                │ │
              │  │       trade_mgr.check_exits(sym, low, high, cl) │ │
              │  │       · bar.low ≤ stop_loss → SL平仓            │ │
              │  │       · bar.high ≥ take_profit → TP平仓         │ │
              │  │       · 追踪止损触发 → TRAIL平仓                 │ │
              │  │       若触发 → 返回 SELL 信号                    │ │
              │  │                                                 │ │
              │  │    B. 更新追踪止损                                │ │
              │  │       盈利 > 1.5×ATR 时激活                      │ │
              │  │       trailing_stop = high - 1.5×ATR             │ │
              │  │       只升不降，锁定利润                          │ │
              │  │                                                 │ │
              │  │    C. 获取当前形态                                │ │
              │  │       regime = regimes[sym][ts]                  │ │
              │  │       UPTREND / DOWNTREND / RANGING / BREAKOUT   │ │
              │  │                                                 │ │
              │  │    D. 委托子策略 evaluate()                      │ │
              │  │       sub_strategies[regime].evaluate(bar, row)  │ │
              │  │       返回 (action, strength, sl, tp, trailing)  │ │
              │  │       · BUY → 注册到TradeManager + 返回BUY信号   │ │
              │  │       · SELL → 形态切换平仓                      │ │
              │  │       · None → 无操作                            │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ④ coin_filter.should_skip(sym, close, vol)     │ │
              │  │    三重检查:                                     │ │
              │  │    · 黑名单 → skip                              │ │
              │  │    · 成交量 < 滚动均值×0.10 → skip (流动性枯竭) │ │
              │  │    · |价格变动| > 15% → skip (极端行情)          │ │
              │  │    若skip=True:                                  │ │
              │  │      仅保留SELL信号（允许平仓，阻止开仓）         │ │
              │  │    更新滚动缓冲区和上一收盘价                     │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ⑤ portfolio.on_signal(signal) → OrderEvent     │ │
              │  │    BUY信号:                                     │ │
              │  │      检查: 该币种无持仓                          │ │
              │  │      quantity = cash × strength / close         │ │
              │  │      → OrderEvent(BUY, quantity)                │ │
              │  │    SELL信号:                                     │ │
              │  │      检查: 该币种有持仓                          │ │
              │  │      quantity = 全部持仓量                       │ │
              │  │      → OrderEvent(SELL, quantity)               │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ⑥ execution.execute(order, close) → FillEvent  │ │
              │  │    模拟真实成交:                                  │ │
              │  │    BUY:  fill_price = close × (1 + 0.05%)      │ │
              │  │    SELL: fill_price = close × (1 - 0.05%)      │ │
              │  │    commission = fill_price × qty × 0.1%         │ │
              │  │    → FillEvent(fill_price, commission, qty)     │ │
              │  └──────────────────┬─────────────────────────────┘ │
              │                     ▼                               │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ⑦ portfolio.on_fill(fill)                      │ │
              │  │    BUY:                                         │ │
              │  │      cash -= fill_price × qty + commission      │ │
              │  │      positions[sym] += qty                      │ │
              │  │    SELL:                                         │ │
              │  │      cash += fill_price × qty - commission      │ │
              │  │      positions[sym] -= qty                      │ │
              │  │    记录到 trade_log:                             │ │
              │  │      {datetime, symbol, direction, qty,          │ │
              │  │       price, commission, cash_after}             │ │
              │  └────────────────────────────────────────────────┘ │
              │                                                     │
              │  ┌────────────────────────────────────────────────┐ │
              │  │ ⑧ portfolio.update_equity(ts)                  │ │
              │  │    每个时间戳处理完所有币种后执行                  │ │
              │  │    position_value = Σ(qty × latest_price)       │ │
              │  │    total_equity = cash + position_value          │ │
              │  │    追加到 equity_curve:                          │ │
              │  │      {datetime, cash, position_value, equity}    │ │
              │  └────────────────────────────────────────────────┘ │
              │                                                     │
              └──────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
              ┌─────────────────────────────────────────────────────┐
              │  strategy.on_finish()                               │
              │  · 策略清理回调（可选）                                │
              └──────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
              ┌─────────────────────────────────────────────────────┐
              │  metrics.compute()                                  │
              │                                                     │
              │  输入: equity_curve, trade_log, initial_capital,     │
              │        bars_per_day (1h=24, 4h=6, 1d=1)            │
              │                                                     │
              │  ┌─ 收益指标 ─────────────────────────────────────┐ │
              │  │ total_return = (final / initial - 1) × 100     │ │
              │  │ annual_return = (final/initial)^(365/days) - 1  │ │
              │  └────────────────────────────────────────────────┘ │
              │  ┌─ 风险指标 ─────────────────────────────────────┐ │
              │  │ max_drawdown = max(peak - equity) / peak       │ │
              │  │ max_dd_duration = 峰值到恢复的最长bar数          │ │
              │  │ volatility = std(bar_returns) × √(365×bpd)     │ │
              │  └────────────────────────────────────────────────┘ │
              │  ┌─ 风险调整收益 ─────────────────────────────────┐ │
              │  │ sharpe  = annual_mean / annual_std              │ │
              │  │ sortino = annual_mean / downside_std            │ │
              │  │ calmar  = annual_return / max_drawdown          │ │
              │  └────────────────────────────────────────────────┘ │
              │  ┌─ 交易统计 (_compute_trade_stats) ──────────────┐ │
              │  │ · 配对买卖: 跟踪open_trades[sym]的买入成本      │ │
              │  │   卖出时 pnl = sell_revenue - buy_cost          │ │
              │  │ · total_trades = 已平仓交易对数                  │ │
              │  │ · win_rate = 盈利次数 / 总次数                   │ │
              │  │ · profit_factor = 总盈利 / 总亏损                │ │
              │  │ · avg_trade_return = 平均每笔盈亏                │ │
              │  │ · max_consecutive_losses = 最大连亏次数          │ │
              │  └────────────────────────────────────────────────┘ │
              └──────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
              ┌─────────────────────────────────────────────────────┐
              │  报告输出                                            │
              │                                                     │
              │  report.print_summary(metrics)                      │
              │  · 控制台打印: 初始资金、最终权益、收益率、回撤、      │
              │    Sharpe、Sortino、Calmar、胜率、盈亏比等            │
              │                                                     │
              │  report.export(equity_curve, trade_log, metrics)     │
              │  · {label}_equity.csv  → 每个时间戳的权益快照         │
              │  · {label}_trades.csv  → 每笔成交记录                │
              │  · {label}_metrics.json → 所有绩效指标               │
              │                                                     │
              │  report.plot_equity(train, test)                     │
              │  · 上图: 训练集(蓝)+测试集(橙)权益曲线               │
              │    红色虚线=分割点, 灰色虚线=初始资金                  │
              │    末端标注收益率, 副标题显示Sharpe和MaxDD对比         │
              │  · 下图: 回撤曲线 (peak-to-trough %)                 │
              │  · 保存为 equity_curve.png (150dpi)                  │
              └─────────────────────────────────────────────────────┘
```

---

## 技术指标计算 (indicators.compute_all)

`strategy.on_init()` 阶段对每个币种调用 `compute_all(df)` 一次性计算全部指标：

```
输入: DataFrame [open, high, low, close, volume]
  │
  ├─ EMA20        = close 的 20周期指数移动平均
  ├─ EMA50        = close 的 50周期指数移动平均
  ├─ EMA50_slope  = EMA50 的 5根K线变化率 (pct_change(5))
  │
  ├─ ADX(14)      平均趋向指标
  │   ├─ +DM / -DM  = 方向运动量
  │   ├─ ATR(14)     = 真实波幅 (max(H-L, |H-prevC|, |L-prevC|) 的EMA)
  │   ├─ +DI / -DI   = 方向指标 = 100 × DM_EMA / ATR
  │   ├─ DX          = 100 × |+DI - -DI| / (+DI + -DI)
  │   └─ ADX         = DX 的 14周期EMA
  │
  ├─ Bollinger Bands(20, 2σ)
  │   ├─ bb_upper = SMA20 + 2×std
  │   ├─ bb_mid   = SMA20
  │   ├─ bb_lower = SMA20 - 2×std
  │   ├─ bb_width = (2×2×std) / SMA20  (归一化宽度)
  │   └─ bb_width_ma = bb_width 的 20周期均值
  │
  ├─ RSI(14)      = 100 - 100/(1 + avg_gain/avg_loss)
  │
  ├─ ATR(14)      = 真实波幅的14周期EMA
  │
  └─ ROC(10)      = close.pct_change(10) × 100  (10周期变化率%)

追加辅助列 (regime_strategy.on_init):
  ├─ prev_ema20   = EMA20.shift(1)  (前一根K线值，用于交叉检测)
  ├─ prev_ema50   = EMA50.shift(1)
  └─ volume_ratio = volume / volume.rolling(20).mean()  (放量倍数)
```

---

## 市场形态分类 (MarketClassifier)

基于 ADX / EMA斜率 / BB宽度 / ROC 的决策树，将每根K线分类为4种形态。

```
                          ┌─────────────┐
                          │  ADX 值判断  │
                          └──────┬──────┘
                   ┌─────────────┼─────────────┐
                   ▼             ▼             ▼
              ADX > 25      20 ≤ ADX ≤ 25   ADX < 20
              (趋势市场)     (过渡区)        (无趋势)
                   │             │             │
              ┌────┴────┐   ┌───┴────┐    ┌───┴────┐
              ▼         ▼   ▼        ▼    ▼        ▼
          EMA50斜率  EMA50斜率  BB扩张   其余   BB扩张   其余
            > 0      ≤ 0    +ROC确认         +ROC确认
              │         │      │       │      │       │
              ▼         ▼      ▼       ▼      ▼       ▼
           UPTREND  DOWNTREND BREAKOUT RANGING BREAKOUT RANGING
           上升趋势  下降趋势   突破    震荡     突破    震荡

BB扩张条件: bb_width > bb_width_ma × 1.5
ROC确认:    |ROC| > 3%

确认过滤 (confirm_bars=3):
  形态切换需连续3根K线确认，防止频繁切换
  例: RANGING→UPTREND 需连续3根K线都判定为UPTREND才真正切换
```

---

## 子策略详解

形态分类后，每根K线委托给对应的子策略处理：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ UPTREND 上升趋势 (UptrendStrategy)                                      │
│                                                                         │
│ 入场条件 (全部满足):                                                     │
│   · EMA20 上穿 EMA50 (prev_ema20 ≤ prev_ema50 且 ema20 > ema50)        │
│   · ADX > 25 (趋势强度确认)                                             │
│   · RSI < 75 (未超买)                                                   │
│                                                                         │
│ 仓位: strength = 0.15 (15%资金)                                         │
│ 止损: close - 2.0 × ATR                                                │
│ 止盈: close + 3.0 × ATR                                                │
│ 追踪止损: 盈利 > 1.5×ATR 后激活, 距离 = 1.5×ATR, 只升不降              │
│                                                                         │
│ 持仓管理: 由 TradeManager 管理 SL/TP/Trailing                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ DOWNTREND 下降趋势 (DowntrendStrategy)                                  │
│                                                                         │
│ 现货只做多，下跌趋势中:                                                  │
│   · 有持仓 → 立即平仓 (SELL)                                            │
│   · 无持仓 → 不操作                                                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ RANGING 区间震荡 (RangingStrategy)                                      │
│                                                                         │
│ 入场条件 (全部满足):                                                     │
│   · 收盘价 ≤ BB下轨 (价格触及区间底部)                                   │
│   · RSI < 35 (超卖)                                                     │
│   · ADX < 20 (确认无趋势)                                               │
│                                                                         │
│ 仓位: strength = 0.10 (10%资金)                                         │
│ 止损: close - 1.5 × ATR                                                │
│ 止盈: BB中轨 (目标回归均值)                                              │
│ 追踪止损: 无                                                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ BREAKOUT 突破 (BreakoutStrategy)                                        │
│                                                                         │
│ 入场条件 (全部满足):                                                     │
│   · 收盘价 > BB上轨 (价格突破区间)                                       │
│   · BB宽度 > BB宽度均值 × 1.5 (波动率扩张)                              │
│   · ROC > 3% (动量确认)                                                 │
│   · volume_ratio ≥ 1.5 (成交量放大1.5倍)                                │
│                                                                         │
│ 仓位: strength = 0.12 (12%资金)                                         │
│ 止损: close - 1.5 × ATR                                                │
│ 止盈: close + 3.0 × ATR                                                │
│ 追踪止损: 无                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 止盈止损管理 (TradeManager)

策略层内部的交易跟踪器，每根K线检查是否触发出场：

```
每根K线执行:
  1. check_exits(symbol, bar.low, bar.high, bar.close)
     │
     ├─ 固定止损: bar.low ≤ stop_loss → 返回 "SL"
     ├─ 固定止盈: bar.high ≥ take_profit → 返回 "TP"
     └─ 追踪止损: bar.low ≤ trailing_stop → 返回 "SL"
         (trailing_stop = max(stop_loss, trailing_stop))

  2. update_trailing(symbol, bar.high, atr)
     │
     ├─ 激活条件: 浮盈 > 1.5 × ATR
     ├─ trailing_stop = bar.high - 1.5 × ATR
     └─ 只升不降: new_trail > old_trail 才更新

出场原因统计 (on_finish 打印):
  · SL    — 固定止损触发
  · TP    — 固定止盈触发
  · TRAIL — 追踪止损触发 (归入SL计数)
  · REGIME — 形态切换导致平仓 (如切入DOWNTREND)
```

---

## 币种分类与过滤

### 分类器 (CoinClassifier)

在回测前对币种进行波动率分组，用于后续给不同组配不同策略参数。

```
输入: {symbol: DataFrame}
  │
  ├─ 计算每个币种的 日收益率标准差 = df["close"].pct_change().std()
  ├─ 计算 日均成交量 = df["volume"].mean()
  ├─ 确定分组边界 (手动指定 或 自动取33/67百分位)
  │
  └─ 分组结果:
       low_vol  (≤ 下界)  → BTC, ETH, BNB, XRP, LTC, DOGE (6个)
       mid_vol  (中间)    → ADA, SOL, AVAX, DOT, LINK, UNI, ATOM (7个)
       high_vol (≥ 上界)  → FIL, APT, ARB, OP, NEAR, SUI (6个)
```

### 运行时过滤器 (CoinFilter)

在回测循环的每个Bar中实时检测异常，保护策略不在极端行情中开仓。

```
should_skip(symbol, close, volume) 三重检查:

  ① 黑名单检查
     symbol ∈ blacklist → skip

  ② 成交量异常检查
     volume < mean(最近48条volume) × 0.10 → skip
     含义: 当前成交量不到近期均值的10%，流动性枯竭

  ③ 价格异常检查
     |close - last_close| / last_close > 15% → skip
     含义: 单根K线涨跌超过15%，极端行情

  skip=True 时:
     · 阻止所有BUY信号（不开新仓）
     · 保留SELL信号（允许平掉已有仓位）
```

---

## 事件模型

系统采用事件驱动架构，四种事件按顺序级联：

```
BarEvent                    SignalEvent                 OrderEvent                  FillEvent
├ symbol: str               ├ symbol: str               ├ symbol: str               ├ symbol: str
├ datetime: datetime        ├ datetime: datetime        ├ datetime: datetime        ├ datetime: datetime
├ open: float               ├ signal_type: BUY/SELL     ├ direction: BUY/SELL       ├ direction: BUY/SELL
├ high: float               └ strength: 0~1             └ quantity: float           ├ quantity: float
├ low: float                  (仓位比例)                   (下单数量)                ├ fill_price: float
├ close: float                                                                      └ commission: float
└ volume: float

事件流: Bar → Signal → Order → Fill → 更新持仓/现金
```

---

## 回测参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_capital` | 10,000 USDT | 初始资金 |
| `commission_rate` | 0.1% | 币安Taker手续费 |
| `slippage_rate` | 0.05% | 滑点模拟 |
| `train_ratio` | 0.75 | 训练集占比 |
| `annual_trading_days` | 365 | 加密市场全年无休 |
| `bars_per_day` | 1h→24, 4h→6, 1d→1 | 用于年化计算 |

---

## 快速开始

```bash
# 下载数据
pyhton data_collector/run.py

# 运行 Regime-Based 策略（主策略）
python run_regime.py

# 运行 SMA交叉策略示例
python backtester/run_example.py
```

Regime 策略输出：
- 控制台打印训练集/测试集绩效对比 + 形态分布统计 + 出场原因统计
- `backtester/output/regime_train_equity.csv` — 训练集权益曲线
- `backtester/output/regime_test_equity.csv` — 测试集权益曲线
- `backtester/output/regime_*_trades.csv` — 交易日志
- `backtester/output/regime_*_metrics.json` — 绩效指标
- `backtester/output/equity_curve.png` — 权益曲线+回撤图

### 编写自定义策略

```python
from backtester.strategy_base import StrategyBase
from backtester.event import BarEvent, SignalEvent, SignalType

class MyStrategy(StrategyBase):
    def on_init(self, historical_bars):
        # 用完整历史数据预计算指标（向量化pandas操作）
        for sym, df in historical_bars.items():
            self.indicators[sym] = ...  # 你的指标

    def on_bar(self, bar, current_positions):
        # 每根K线调用，查表判断信号（不要在这里重新计算指标）
        if 买入条件:
            return [SignalEvent(bar.symbol, bar.datetime, SignalType.BUY, strength=0.1)]
        if 卖出条件:
            return [SignalEvent(bar.symbol, bar.datetime, SignalType.SELL, strength=1.0)]
        return None
```

`strength` 参数控制仓位大小：BUY时 `quantity = cash × strength / price`，SELL时全部平仓。

