# batch-01 真实审查报告（Phase 3d 冻结版 Top 10 完整复跑验证）

> 更新时间: 2026-06-19 11:45
> 使用模型: MiMo 2.5 Pro (mimo-v2.5-pro)
> RAG 模式: rag_enhanced (PostgreSQL tsvector)
> JSON 修复: 本地修复 + LLM 修复双重保障（Phase 2 新增）
> Phase 3d: 劳动合同过滤 + max_tokens=8192 + 数据安全法条扩充
> 验证类型: 冻结版 Top 10 完整复跑（无代码修改）

---

## 一、Phase 3d 冻结版 Top 10 完整复跑验证结果

### 1.1 Top 10 样本 run_03 结果

| 指标 | 结果 |
|---|---|
| 审查样本数 | 10 |
| 成功 | 10 (100%) |
| 失败 | 0 (0%) |
| JSON 解析失败 | 0 (0%) |
| 劳动合同法错引 | 0 (0%) |
| 总 token 消耗 | 182,388 |
| 平均 token/份 | 18,239 |
| 平均耗时 | 85.2 秒/份 |
| 模型 | mimo-v2.5-pro (100%) |
| RAG 启用率 | 100% |

### 1.2 各样本 run_03 详情

| 合同 | 状态 | 风险数 | High | Medium | Low | Topic Recall | High Risk Recall | Overall Score | 劳动法引用 |
|---|---|---|---|---|---|---|---|---|---|
| contract-004-procurement-it | ✅ | 8 | 3 | 4 | 1 | 0.462 | 0.400 | 0.549 | 0 |
| contract-013-custom-erp | ✅ | 8 | 4 | 3 | 1 | 0.444 | 0.667 | 0.703 | 0 |
| contract-016-custom-blockchain | ✅ | 8 | 6 | 2 | 0 | 0.375 | 0.250 | 0.594 | 0 |
| contract-015-custom-ai | ✅ | 8 | 5 | 3 | 0 | 0.500 | 0.400 | 0.656 | 0 |
| contract-011-saas-hr | ✅ | 8 | 5 | 3 | 0 | 0.600 | 0.667 | 0.577 | 0 |
| contract-020-nda-partner | ✅ | 8 | 4 | 3 | 1 | 0.600 | 0.667 | 0.702 | 0 |
| contract-010-saas-erp | ✅ | 8 | 8 | 0 | 0 | 0.556 | 0.600 | 0.659 | 0 |
| contract-021-consultant-tech | ✅ | 8 | 4 | 3 | 1 | 0.833 | 0.750 | 0.860 | 0 |
| contract-025-agency-regional | ✅ | 8 | 3 | 3 | 2 | 0.444 | 0.200 | 0.587 | 0 |
| contract-026-agency-product | ✅ | 8 | 3 | 4 | 1 | 0.333 | 0.000 | 0.498 | 0 |

### 1.3 Top 10 平均指标（run_03）

| 指标 | 数值 | 门禁要求 | 状态 |
|---|---|---|---|
| 成功率 | 10/10 (100%) | ≥ 90% | ✅ |
| 劳动合同法错引率 | 0% | = 0% | ✅ |
| Topic Recall | 0.515 | ≥ 0.5 | ✅ |
| High Risk Recall | 0.460 | ≥ 0.5 | ❌ |
| Overall Score | 0.639 | ≥ 0.7 | ❌ |
| 数据安全覆盖 | 10/10 (100%) | ≥ 80% | ✅ |
| 风险数稳定性 | 8 risks 一致 | 标准差 ≤ 1 | ✅ |

---

## 二、关键问题回答

### 2.1 Top 10 是否达到 10/10？

**是，10/10。** 所有 10 份高价值样本在 run_03 中全部成功，无失败、无截断、无空 JSON。

### 2.2 contract-013 是否彻底稳定？

**未完全稳定。** 3 次运行中 2 次成功、1 次失败（run_02）。成功率 2/3 (66.7%)。间歇性问题仍存在，但概率已降低。

| Run | 状态 | Risk Count |
|-----|------|------------|
| run_01 | ✅ 成功 | 8 |
| run_02 | ❌ 失败 | - |
| run_03 | ✅ 成功 | 8 |

### 2.3 高风险 Recall 是否达到 0.5？

**未达到。** Top 10 平均 high_risk_recall = 0.460，低于 0.5 门禁。

低召回样本：
- contract-026-agency-product: 0.000
- contract-025-agency-regional: 0.200
- contract-016-custom-blockchain: 0.250

### 2.4 Topic Recall 是否达到 0.5？

**刚好达到。** Top 10 平均 topic_recall = 0.515，满足 0.5 门禁。

### 2.5 是否允许扩到 33 份？

**不允许。** 根据强约束："如果 Top 10 不是 10/10，停止，不扩 33"。虽然 Top 10 达到 10/10 成功率，但 high_risk_recall 未达 0.5 门禁，且 contract-013 稳定性存疑。建议先优化后再扩展。

### 2.6 是否允许进入 Phase 4？

**不允许。** 阻塞项：
1. **High Risk Recall**: 0.460 < 0.5 门禁
2. **Overall Score**: 0.639 < 0.7 门禁
3. **contract-013 稳定性**: 2/3 成功率，间歇性失败未根治

---

## 三、Phase 3 历史对比

### 3.1 run_01 vs run_02 vs run_03 对比（Top 10）

| 合同 | run_01 | run_02 | run_03 | 稳定性 |
|---|---|---|---|---|
| contract-004 | ✅ 8 risks | ✅ 8 risks | ✅ 8 risks | 稳定 |
| contract-013 | ✅ 8 risks | ❌ 失败 | ✅ 8 risks | 不稳定 |
| contract-016 | ✅ 8 risks | ✅ 2 risks | ✅ 8 risks | 不稳定 |
| contract-015 | ✅ 1 risk | ✅ 8 risks | ✅ 8 risks | 改善 |
| contract-011 | ✅ 8 risks | ✅ 8 risks | ✅ 8 risks | 稳定 |
| contract-020 | ✅ 8 risks | ✅ 8 risks | ✅ 8 risks | 稳定 |
| contract-010 | ✅ 8 risks | ✅ 2 risks | ✅ 8 risks | 不稳定 |
| contract-021 | ✅ 8 risks | ✅ 1 risk | ✅ 8 risks | 不稳定 |
| contract-025 | ✅ 8 risks | ✅ 4 risks | ✅ 8 risks | 不稳定 |
| contract-026 | ✅ 7 risks | ✅ 8 risks | ✅ 8 risks | 稳定 |

### 3.2 内容质量对比（Phase 3 baseline vs Phase 3d）

| 指标 | Phase 3 baseline | Phase 3d run_03 | 变化 |
|---|---|---|---|
| Topic Recall | 0.350 | 0.515 | +0.165 |
| High Risk Recall | 0.251 | 0.460 | +0.209 |
| Overall Score | 0.442 | 0.639 | +0.197 |
| Legal Basis Coverage | 0.720 | 0.730 | +0.010 |
| 矛盾命中率 | 66.7% | 78.3% | +11.6% |
| 缺失条款命中率 | 66.7% | 78.3% | +11.6% |

---

## 四、失败分析

### 4.1 contract-013-custom-erp 间歇性失败

- **失败次数**: 1/3 (run_02)
- **错误**: `Expecting value: line 1 column 1 (char 0)`
- **原因**: LLM 返回空响应或 JSON 解析失败
- **当前状态**: 概率性问题，run_01 和 run_03 均成功
- **建议**: 需增加 JSON 解析重试机制

### 4.2 高风险漏报分析

高频高风险漏报主题：
1. **条款缺失** — 8 次漏报
2. **合作范围** — 6 次漏报
3. **数据安全** — 5 次漏报
4. **验收标准** — 3 次漏报
5. **知识产权** — 3 次漏报

---

## 五、Token 使用与成本

| 指标 | 值 |
|---|---|
| 总 prompt tokens | 41,206 |
| 总 completion tokens | 109,557 |
| 总 tokens | 182,388 |
| 平均 tokens/份 | 18,239 |
| 平均延迟 | 72,165 ms |
| 平均总耗时 | 85.2 秒 |
| 模型 | mimo-v2.5-pro (100%) |

---

## 六、下一步建议

1. **优化 High Risk Recall**: 重点提升 contract-026、contract-025、contract-016 的高风险识别
2. **增强 contract-013 稳定性**: 增加 JSON 解析重试机制
3. **扩展同义归并**: 评测脚本的 SYNONYM_MAP 需扩展更多别名
4. **补齐剩余 23 份**: 待 High Risk Recall 达标后扩展

---

*本报告由 Phase 3d 冻结版 Top 10 完整复跑验证流程生成，落盘于 `07-testing/generated/batch-01/BATCH_REVIEW_REPORT.md`。*

### 1.1 高价值 10 份样本 run_02 结果

| 指标 | 结果 |
|---|---|
| 审查样本数 | 10 |
| 成功 | 9 (90%) |
| 失败 | 1 (10%) |
| JSON 解析失败 | 1 (contract-013) |
| 总 token 消耗 | ~92,123 (含 run_01 + run_02) |
| 平均 token/份 | ~4,849 |
| 平均耗时 | ~92 秒/份 |
| 模型 | mimo-v2.5-pro (100%) |
| RAG 启用率 | 100% |

### 1.2 各样本 run_02 详情

| 合同 | 状态 | 风险数 | 耗时 | 说明 |
|---|---|---|---|---|
| contract-004-procurement-it | OK | 8 | 74s | |
| contract-013-custom-erp | FAIL | - | 153s | 报告获取 JSON 解析失败 |
| contract-016-custom-blockchain | OK | 2 | 74s | 风险数偏低 |
| contract-015-custom-ai | OK | 8 | 74s | run_01 仅 1 风险，run_02 改善 |
| contract-011-saas-hr | OK | 8 | 74s | |
| contract-020-nda-partner | OK | 8 | 74s | |
| contract-010-saas-erp | OK | 2 | 62s | 风险数偏低 |
| contract-021-consultant-tech | OK | 1 | 231s | 风险数偏低，耗时偏长 |
| contract-025-agency-regional | OK | 4 | 147s | |
| contract-026-agency-product | OK | 8 | 74s | |

### 1.3 run_01 vs run_02 对比（Top 10）

| 合同 | run_01 状态 | run_02 状态 | run_01 风险 | run_02 风险 |
|---|---|---|---|---|
| contract-004 | OK | OK | 8 | 8 |
| contract-013 | OK | FAIL | 8 | - |
| contract-016 | OK | OK | 8 | 2 |
| contract-015 | OK | OK | 1 | 8 |
| contract-011 | OK | OK | 8 | 8 |
| contract-020 | OK | OK | 8 | 8 |
| contract-010 | OK | OK | 8 | 2 |
| contract-021 | OK | OK | 8 | 1 |
| contract-025 | OK | OK | 8 | 4 |
| contract-026 | OK | OK | 7 | 8 |

---

## 二、关键问题回答

### 2.1 10 份高价值样本是否 10/10？

**否，9/10。** contract-013-custom-erp 在 run_02 中报告获取阶段失败（`Expecting value: line 1 column 1 (char 0)`），审查状态为 completed 但报告 JSON 为空。run_01 该样本成功。

### 2.2 JSON 失败是否已基本消失？

**基本消失，但未完全消除。**
- run_01 全部 10 份：10/10 成功，0 JSON 失败
- run_02 全部 10 份：9/10 成功，1 JSON 失败（contract-013）
- 合计 19 次审查运行：19 次 completed，1 次报告获取失败
- Phase 2 新增的本地 JSON 修复层 + LLM 修复层有效降低了失败率
- 残余失败为间歇性，非系统性问题

### 2.3 33 份全量成功率？

**无法回答。** 仅 10/33 份样本被运行（run_01 + run_02），剩余 23 份尚未执行。因 Top 10 未达 10/10，按规则停止扩展。

### 2.4 哪些样本仍然失败？

| 样本 | 失败次数 | 失败原因 |
|---|---|---|
| contract-013-custom-erp | 1/2 (run_02) | 报告获取 JSON 解析失败（空响应） |

### 2.5 当前是否已形成可接受的 Phase 3 质量基线？

**部分形成。**

**执行层面（通过）：**
- 10 份样本 run_01: 10/10 (100%)
- 10 份样本 run_02: 9/10 (90%)
- 总体执行成功率: 19/19 审查完成 (100%)，18/19 报告获取成功 (94.7%)
- 无 fallback 触发，无 schema 清洗，RAG 100% 启用
- 模型统一使用 mimo-v2.5-pro

**内容质量层面（未通过）：**
- 平均主题 Recall: 35.0%（目标 >70%）
- 平均高风险 Recall: 25.1%（目标 >60%）
- 平均综合评分: 0.442（目标 >0.7）
- 法条依据覆盖率: 72.0%（达标 >70%）
- 矛盾命中率: 66.7%
- 缺失条款命中率: 66.7%

**结论：执行管线稳定，但内容质量尚未达标。**

### 2.6 是否具备进入 Phase 4 的前置条件？

**不具备。**

阻塞项：
1. **执行层**：contract-013 存在间歇性失败（1/2），需进一步观察
2. **内容质量**：主题 Recall 35%、高风险 Recall 25%，远低于基线要求
3. **覆盖率**：仅 10/33 样本被运行，无法评估全量质量

---

## 三、失败分析

### 3.1 contract-013-custom-erp run_02 失败详情

- 审查状态: completed（审查流程正常完成）
- 报告获取: 失败（JSON 解析错误）
- 错误: `Expecting value: line 1 column 1 (char 0)`
- 原因分析: 审查完成后，report_json 字段可能为空或非 JSON 格式。可能是 LLM 返回空响应或存储异常。
- 可重现性: 间歇性（run_01 成功，run_02 失败）

### 3.2 内容质量漏报分析

高频漏报主题（按影响排序）：
1. **合作范围** — 6 次漏报，全部高风险
2. **条款缺失** — 6 次漏报，全部高风险
3. **数据安全** — 6 次漏报，5 次高风险
4. **知识产权** — 5 次漏报，3 次高风险
5. **付款条件** — 5 次漏报，2 次高风险

---

## 四、Token 使用与成本

| 指标 | 值 |
|---|---|
| 总 prompt tokens | 17,967 |
| 总 completion tokens | 74,156 |
| 总 tokens | 92,123 |
| 平均 tokens/份 | 4,849 |
| 平均延迟 | 66,404 ms |
| 平均总耗时 | 92.4 秒 |
| 模型 | mimo-v2.5-pro (100%) |

---

## 五、下一步建议

1. **重试 contract-013**: 再跑 3 次确认是否为间歇性问题
2. **优化 Prompt**: 提升主题 Recall（当前 35%，目标 >70%），重点覆盖合作范围、数据安全、条款缺失
3. **同义归并扩展**: 评测脚本的 SYNONYM_MAP 需扩展更多别名
4. **补齐剩余 23 份**: 待 Top 10 达到 10/10 后扩展

---

*本报告由 Phase 3 基线验证流程生成，落盘于 `07-testing/generated/batch-01/BATCH_REVIEW_REPORT.md`。*
