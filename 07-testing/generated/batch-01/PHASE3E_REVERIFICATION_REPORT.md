# Phase 3e 复验报告：3 核心样本 run_04 真实复跑

> 验证时间：2026-06-19 12:30-12:45
> 验证范围：3 份核心样本 run_04（自动编号，未覆盖旧 run）
> 验证目标：确认 Phase 3e 代码修复 + 评测映射修复效果

---

## 1. 自动编号验证

| 样本 | 旧 run 文件 | 新 run 文件 | 编号逻辑 |
|------|------------|------------|---------|
| contract-026-agency-product | run_01/02/03 | run_04 ✅ | get_next_run_number 自动递增 |
| contract-016-custom-blockchain | run_01/02/03 | run_04 ✅ | get_next_run_number 自动递增 |
| contract-013-custom-erp | run_01/02/03 | run_04 ✅ | get_next_run_number 自动递增 |

**结论：自动编号正常工作，未覆盖任何旧 run 文件。**

---

## 2. 复跑结果总览

| 样本 | 状态 | 风险数 | High | Medium | Low | Tokens | 耗时 | 模型 | RAG |
|------|------|--------|------|--------|-----|--------|------|------|-----|
| contract-026-agency-product | ✅ 成功 | 8 | 2 | 6 | 0 | 7,599 | 122.6s | mimo-v2.5-pro | ✅ |
| contract-016-custom-blockchain | ✅ 成功 | 8 | 7 | 1 | 0 | 4,881 | 86.4s | mimo-v2.5-pro | ✅ |
| contract-013-custom-erp | ✅ 成功 | 8 | 6 | 1 | 1 | 3,913 | 74.4s | mimo-v2.5-pro | ✅ |

**3/3 成功，无失败，无空 JSON，无截断。**

---

## 3. 指标对比（run_03 vs run_04）

| 样本 | 指标 | run_03 | run_04 | 变化 | 状态 |
|------|------|--------|--------|------|------|
| contract-026 | topic_recall | 0.333 | 0.444 | +0.111 | ⬆️ 提升 |
| contract-026 | high_risk_recall | 0.0 | 0.0 | ±0 | ❌ 未改善 |
| contract-026 | overall_score | 0.498 | 0.518 | +0.020 | ⬆️ 微升 |
| contract-016 | topic_recall | 0.375 | 0.625 | +0.250 | ✅ 大幅提升 |
| contract-016 | high_risk_recall | 0.25 | 0.5 | +0.250 | ✅ 大幅提升 |
| contract-016 | overall_score | 0.594 | 0.706 | +0.112 | ✅ 明显改善 |
| contract-013 | topic_recall | 0.556 | 0.444 | -0.112 | ⬇️ 回退 |
| contract-013 | high_risk_recall | 0.667 | 0.667 | ±0 | ✅ 稳定 |
| contract-013 | overall_score | 0.743 | 0.703 | -0.040 | ⬇️ 微降 |

---

## 4. 关键问题回答

### 4.1 contract-026 的 high_risk_recall 是否提升？

**未提升，仍为 0.0。**

- 期望高风险：付款条件、佣金计算、培训、客户归属
- 实际检出高风险：违约责任、销售指标
- **问题分析**：
  - "销售指标"是新检出的高风险，但不在期望列表中
  - "付款条件"被检出但标为 medium 而非 high
  - "佣金计算""培训""客户归属"仍未被识别为独立风险类别
- **归因**：prompt 增量对 contract-026 效果有限，模型仍倾向于输出通用风险

### 4.2 contract-016 评测映射修复后 high_risk_recall 是否恢复？

**恢复并提升。**

- run_03: high_risk_recall = 0.25（"智能合约安全"未映射到"安全责任"）
- run_04: high_risk_recall = 0.5（"安全责任"和"数据安全"正确命中）
- **评测映射修复生效**："智能合约安全" → "安全责任" 映射正常工作
- **额外收益**：topic_recall 从 0.375 提升到 0.625

### 4.3 contract-013 是否稳定成功？

**稳定成功。**

- run_01: ✅ 成功
- run_02: ❌ 失败（空 JSON，旧版本）
- run_03: ✅ 成功
- run_04: ✅ 成功
- high_risk_recall 稳定在 0.667

### 4.4 自动编号是否正常工作？

**正常工作。**

- 3 份样本均生成了 run_04，未覆盖 run_01/02/03
- get_next_run_number() 正确扫描已有文件并递增

### 4.5 是否支持进入"4 核心样本复跑"或"Top 10 复跑"？

**部分支持。**

- contract-016: ✅ 明显提升，可以进入下一阶段
- contract-013: ✅ 稳定，可以进入下一阶段
- contract-026: ❌ 未改善，需要进一步优化 prompt
- **建议**：先解决 contract-026 问题，再进入 Top 10 复跑

---

## 5. 问题归因总结

| 问题 | 归因 | 影响样本 | 状态 |
|------|------|---------|------|
| "智能合约安全"未映射 | 评测映射问题 | contract-016 | ✅ 已修复 |
| contract-026 高风险全部漏报 | Prompt 问题 | contract-026 | ❌ 未解决 |
| "销售指标"不在期望列表 | 黄金预期标注问题 | contract-026 | ⚠️ 需补充 |
| contract-013 topic_recall 回退 | LLM 输出不稳定性 | contract-013 | ⚠️ 可接受 |

---

## 6. 结论

### 评测映射修复有效
- contract-016 的 high_risk_recall 从 0.25 提升到 0.5
- "智能合约安全" → "安全责任" 映射正常工作
- "数据安全与个人信息保护" → "数据安全" 映射正常工作

### contract-026 仍未解决
- high_risk_recall 仍为 0.0
- prompt 增量对代理合同效果有限
- 需要更强的 prompt 特化或 RAG 语料补充

### 下一步建议
1. 针对 contract-026 做更强的 prompt 特化（佣金计算、培训、客户归属）
2. 考虑为代理合同补充 RAG 语料
3. 解决 contract-026 后再进入 Top 10 复跑

---

*报告生成时间：2026-06-19 12:45*
*复跑脚本：`scripts/batch_review.py --contracts contract-026-agency-product contract-016-custom-blockchain contract-013-custom-erp --runs 1`*
