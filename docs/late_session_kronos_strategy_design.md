# Kronos 尾盘买入（T+1）策略设计文档（更新版）

## 1. 背景与目标

本策略目标是将 Kronos 的短期预测能力转化为 A 股“尾盘买入、次日早盘卖出”的可执行 alpha。基于当前讨论结论，采用：

- **主口径**：分钟级执行仿真（优先）
- **保底口径**：日线代理（仅当分钟覆盖不足时启用）

关键约束：

- 持仓不超过 1 个交易日（严格 T+1）
- Go/No-Go 评审必须同时满足：
  - Test 集成本后超额与稳定性达标
  - Walk-forward 成本后超额与稳定性达标

## 2. 策略总览

### 2.1 信号层（Kronos + 规则过滤）

1) Kronos 原始信号（截面排序）

- `s_last`: 预测末点 close 相对当前 close 的收益
- `s_mean`: 预测窗口均值 close 相对当前 close 的收益
- `s_path`: 预测路径质量（如上行占比、波动惩罚）

2) 规则过滤（当前版，可调优）

- 趋势过滤：MA10 > MA20，MA10 斜率 > 0，close > MA30
- 回踩过滤：low 接近 MA10 且 close 未显著跌破 MA10
- 量能过滤：缩量（相对昨量/短均量）
- 交易过滤：非 ST、非停牌、流动性达标、非一字板

3) 融合打分（统一标准化）

- `score = w1*z(s_last) + w2*z(s_mean) + w3*z(s_path) + w4*z(tech_quality)`
- 通过硬过滤后做截面 Top-K 入池

> 说明：上述过滤与阈值不是固定真理，后续按回测结果滚动调整，不绑定历史经验模板。

### 2.2 交易执行层

- 买入：T 日 14:50~14:57
- 卖出：T+1 日 09:30~10:30，最晚 10:30 清仓
- 仓位：默认等权，可切换风险预算/波动率反比
- 约束：单票权重上限、组合总仓位上限、可交易性校验先于成交定价

### 2.3 风控层

- 个股风控：硬止损、异常流动性退出
- 组合风控：指数弱势降仓、日损阈值开关
- 模型风控：滚动 RankIC 退化触发权重下调或暂停

## 3. 数据口径与 blocker 处理

## 3.1 口径决策

- **主结论**：优先分钟级数据；日线仅作 fallback。
- **禁止主口径**：使用 T+1 的 `high` 作为卖出价（乐观偏差显著）。

## 3.2 分钟数据可用性检查（必须输出）

- `coverage_trade_window`（买入窗口覆盖率）
- `coverage_exit_window`（卖出窗口覆盖率）
- `joint_coverage`（买卖窗口联合覆盖率）
- 字段完整性与异常占比（NaN/负值/零成交）
- 时间连续性与交易日历一致性

建议门槛：`joint_coverage >= 0.85` 采用分钟主口径；否则触发日线 fallback。

## 3.3 日线 fallback 口径（仅保底）

- 买入价：T 日 close（或 close + 保守滑点）
- 卖出价：T+1 open 或 VWAP 近似
- 禁用：T+1 high 作为主卖价
- `assumption_version = daily_proxy`

## 3.4 涨跌停与成交失败建模（v1）

- 买入：封涨停且该分钟无有效成交量 => 买入失败
- 卖出：封跌停且无有效成交 => 顺延重试；10:30 仍失败则记录未成交残留
- 成本：双边手续费 + 卖出印花税 + 最低费用门槛
- 滑点：Low/Base/High 三档用于敏感性分析

## 4. 实验分层与里程碑

## 4.1 实验定义

- Exp-A：纯 Kronos 排序 + 基础可交易过滤
- Exp-B：Exp-A + 技术过滤（趋势/回踩/量能）

## 4.2 输出产物（统一）

- `signals.parquet`
- `trades.parquet`
- `metrics.json`
- 关键图表：净值、回撤、RankIC

## 4.3 透明化指标（必须入 `metrics.json`）

- `assumption_version`
- `assumption_diff_impact`
- `data_coverage_summary`
- `limit_hit_stats`
- `execution_degradation`

## 4.4 时间计划

- 2026-04-24：Exp-A/Exp-B 首版实验包
- 2026-04-26：Walk-forward + 成本敏感性 + Exp-A vs Exp-B 结论

## 5. 脚本化与复用要求

为保证后续可重复执行，数据清洗与覆盖率统计必须脚本化，建议拆分为：

- `scripts/clean_minute_csv.py`：字段标准化与黏连修复
- `scripts/check_minute_coverage.py`：覆盖率与连续性统计
- `scripts/build_backtest_dataset.py`：生成统一回测输入

产出建议附带 `reports/data_quality_summary.json`，供策略回测读取与审计。

## 6. 评审与结论标准

是否进入下一阶段（例如更高保真撮合/小资金仿真盘），仅依据以下同时满足：

1) Test：成本后超额 > 0 且稳定性指标达标（如 Sharpe/MDD/波动约束）
2) Walk-forward：同样达标

任一不达标，则继续在当前阶段迭代参数与执行假设，不升级阶段。

## 7. 后续调优原则

- 不锁死当前指标或阈值；以数据验证为准
- 优先处理“影响可交易性与偏差”的环节：数据质量、成交失败、成本建模
- 每次口径变更必须记录版本与影响范围，保证结果可比、可审计
