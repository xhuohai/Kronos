# Kronos A股微调开发文档（v1）

> 本文档是实实在在用于研发落地的微调开发文档。`finetune_csv/README_CN.md` 仅作为示例与约束参考，不作为开发主文档。

## 1. 目标与边界

- 目标：在当前机器完成 A 股微调链路落地，优先保证口径一致、可逆映射、可评估。
- 训练口径：后复权/归一化口径训练 + 预测后处理还原真实价格。
- 固定起始日：`2023-01-01`（全链路强校验，不允许漂移）。
- 数据接入：工程直连数据处理，不强依赖 Qlib 格式。
- 成交特征：必须支持 `vol/amount`（数据源可为 `a_stock_data`）。

## 2. 数据契约（Data Contract）

### 2.1 输入字段（必选）

- 标识：`ts_code`, `trade_date`
- 价格：`open`, `high`, `low`, `close`
- 成交：`vol`, `amount`
- 还原锚点：`adj_factor`, `latest_adj_factor`

### 2.2 强约束

1. 任意样本可回溯至 `raw + factor`。
2. 禁止仅保留不可逆归一化值。
3. 缺失 `vol/amount/adj_factor` 任一关键字段，数据构建失败。

### 2.3 变换定义

- 训练：窗口归一化（z-score），保存 `x_mean/x_std`。
- 推理后处理：先反归一化，再映射到真实价格空间。
- clip 边界：发生截断时必须打标 `clip_flag=1`，并纳入评估报告。

## 3. 数据集产物与目录规范

输出目录建议：`outputs/finetune_v1/`

- `dataset_train.parquet`
- `dataset_val.parquet`
- `dataset_test.parquet`
- `mapping_meta.parquet`
- `metrics_norm.json`
- `metrics_real.json`
- `metrics_summary.json`
- `mapping_validation_report.json`

## 4. `mapping_meta.parquet` 最小字段规范

- 主键：`ts_code`, `trade_date`, `window_id`, `row_idx`
- 原始值：`raw_open`, `raw_high`, `raw_low`, `raw_close`, `raw_vol`, `raw_amount`
- 因子值：`adj_factor`, `latest_adj_factor`
- 归一化统计：`x_mean_*`, `x_std_*`
- 审计字段：`clip_flag`, `clip_lower`, `clip_upper`, `transform_version`, `restore_version`, `build_id`

要求：每条预测结果必须可通过 `mapping_meta` 唯一回放还原链路。

## 5. 时间切分与样本构建

- 全链路起点：`start_date=2023-01-01`
- 切分方式：train/val/test 时间连续切分，禁止穿越。
- 特殊样本：停牌/缺失/极值需标记，并在评估报告单独统计。

## 6. 脚本职责（工程直连）

### 6.1 `scripts/build_dataset.py`

- 输入：raw OHLC + factor
- 输出：三份数据集 + `mapping_meta`
- 强校验：`--start-date` 默认 `2023-01-01`，且与配置一致

### 6.2 `scripts/train_cpu.py`

- CPU 微调入口，支持断点续跑
- 推荐：`batch_size=4~8`，`epochs` 分阶段增加
- checkpoint：每 N step 保存，支持恢复

### 6.3 `scripts/predict_and_restore.py`

- 负责预测、反归一化、真实价格还原
- 输出 `pred_norm.parquet` 与 `pred_restored.parquet`

### 6.4 `scripts/eval_dual_metrics.py`

- 归一化空间指标：MSE/MAE/RankIC
- 真实价格空间指标：MSE/MAE/MAPE、方向准确率、分位误差
- 若有策略回放：补充最大回撤、Sharpe

### 6.5 `scripts/validate_mapping.py`

- 抽样执行 `raw→norm→pred→restore` 闭环核验
- 输出映射完整性与误差统计

## 7. 配置与运行约束

- 单一配置源：`configs/finetune_v1.yaml`
- 脚本不得隐式覆盖关键参数。
- 最小日志集：loss、lr、耗时、checkpoint 恢复点、clip 比例。

## 8. 验收标准（DoD）

- [ ] 全链路 `start_date=2023-01-01` 校验生效
- [ ] 成功产出 `dataset_train/val/test` 与 `mapping_meta`
- [ ] 双空间指标文件完整
- [ ] 映射校验报告可复现（固定随机种子）
- [ ] `clip_flag` 样本可追踪且在报告中单列

## 9. 与 README 的关系

- `finetune_csv/README_CN.md`：示例、快速入门、命令参考。
- `docs/finetune_model_dev_v1.md`（本文）：研发执行标准、数据契约、验收依据。
