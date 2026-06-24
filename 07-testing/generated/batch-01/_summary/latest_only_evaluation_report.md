# Latest-Only 黄金样例评测报告 — batch-01

> **口径说明：本报告仅基于每个样本最新一次成功运行，不含历史旧 run。**
> 生成时间：2026-06-22T11:31:06.631964

## 一、评测总览

| 指标 | 数值 |
|---|---|
| 样本数 | 33 |
| 成功评测 | 33 |
| 无成功 run | 0 |
| 平均主题 Recall | 58.2% |
| 平均主题 Precision | 55.1% |
| 平均高风险 Recall | 61.7% |
| 平均综合评分 | 0.676 |
| 平均法条依据覆盖率 | 64.5% |
| 矛盾命中率 | 96.0% |
| 缺失条款命中率 | 100.0% |

## 二、各样本最新 run 评测详情

| 样本 | Run | 主题Recall | 高风险Recall | 综合评分 | 法条覆盖 | 状态 |
|---|---|---|---|---|---|---|
| contract-001-procurement-equipment | review_run_01.json | 60.0% | 80.0% | 0.716 | 37.5% | ✅ |
| contract-002-procurement-materials | review_run_05.json | 22.2% | 20.0% | 0.459 | 54.5% | ✅ |
| contract-003-procurement-office | review_run_05.json | 33.3% | 20.0% | 0.529 | 75.0% | ✅ |
| contract-004-procurement-it | review_run_04.json | 38.5% | 60.0% | 0.591 | 37.5% | ✅ |
| contract-005-techservice-platform | review_run_03.json | 63.6% | 83.3% | 0.651 | 38.5% | ✅ |
| contract-006-techservice-maintenance | review_run_03.json | 44.4% | 60.0% | 0.532 | 62.5% | ✅ |
| contract-007-techservice-data | review_run_01.json | 77.8% | 66.7% | 0.710 | 62.5% | ✅ |
| contract-008-techservice-cloud | review_run_03.json | 50.0% | 50.0% | 0.520 | 60.0% | ✅ |
| contract-009-saas-crm | review_run_03.json | 57.1% | 66.7% | 0.598 | 54.5% | ✅ |
| contract-010-saas-erp | review_run_06.json | 55.6% | 80.0% | 0.626 | 50.0% | ✅ |
| contract-011-saas-hr | review_run_06.json | 80.0% | 100.0% | 0.723 | 8.3% | ✅ |
| contract-012-saas-bi | review_run_01.json | 25.0% | 50.0% | 0.408 | 62.5% | ✅ |
| contract-013-custom-erp | review_run_06.json | 44.4% | 50.0% | 0.662 | 87.5% | ✅ |
| contract-014-custom-app | review_run_05.json | 62.5% | 66.7% | 0.745 | 72.7% | ✅ |
| contract-015-custom-ai | review_run_04.json | 66.7% | 80.0% | 0.833 | 100.0% | ✅ |
| contract-016-custom-blockchain | review_run_06.json | 50.0% | 50.0% | 0.644 | 62.5% | ✅ |
| contract-017-nda-bilateral | review_run_01.json | 75.0% | 66.7% | 0.679 | 100.0% | ✅ |
| contract-018-nda-employee | review_run_01.json | 71.4% | 100.0% | 0.862 | 75.0% | ✅ |
| contract-019-nda-investor | review_run_05.json | 66.7% | 66.7% | 0.784 | 88.9% | ✅ |
| contract-020-nda-partner | review_run_04.json | 60.0% | 66.7% | 0.702 | 50.0% | ✅ |
| contract-021-consultant-tech | review_run_04.json | 83.3% | 75.0% | 0.860 | 87.5% | ✅ |
| contract-022-consultant-management | review_run_01.json | 100.0% | 100.0% | 0.962 | 75.0% | ✅ |
| contract-023-consultant-legal | review_run_05.json | 50.0% | 0.0% | 0.530 | 70.0% | ✅ |
| contract-024-consultant-financial | review_run_01.json | 100.0% | 66.7% | 0.917 | 100.0% | ✅ |
| contract-025-agency-regional | review_run_05.json | 71.4% | 100.0% | 0.862 | 75.0% | ✅ |
| contract-026-agency-product | review_run_11.json | 77.8% | 80.0% | 0.854 | 87.5% | ✅ |
| contract-027-agency-online | review_run_05.json | 22.2% | 25.0% | 0.472 | 54.5% | ✅ |
| contract-028-strategic-joint | review_run_03.json | 83.3% | 75.0% | 0.817 | 58.3% | ✅ |
| contract-029-strategic-supply | review_run_01.json | 55.6% | 80.0% | 0.738 | 62.5% | ✅ |
| contract-030-strategic-tech | review_run_01.json | 60.0% | 60.0% | 0.741 | 87.5% | ✅ |
| contract-031-procurement-medical | review_run_01.json | 44.4% | 50.0% | 0.605 | 50.0% | ✅ |
| contract-032-techservice-security | review_run_03.json | 40.0% | 20.0% | 0.503 | 41.7% | ✅ |
| contract-033-consultant-marketing | review_run_03.json | 30.0% | 20.0% | 0.465 | 40.0% | ✅ |

## 三、命中率最高的合同（Top 5）

| 排名 | 样本 | Run | 综合评分 |
|---|---|---|---|
| 1 | contract-022-consultant-management | review_run_01.json | 0.962 |
| 2 | contract-024-consultant-financial | review_run_01.json | 0.917 |
| 3 | contract-018-nda-employee | review_run_01.json | 0.862 |
| 4 | contract-025-agency-regional | review_run_05.json | 0.862 |
| 5 | contract-021-consultant-tech | review_run_04.json | 0.860 |

## 四、命中率最低的合同（Bottom 5）

| 排名 | 样本 | Run | 综合评分 |
|---|---|---|---|
| 1 | contract-032-techservice-security | review_run_03.json | 0.503 |
| 2 | contract-027-agency-online | review_run_05.json | 0.472 |
| 3 | contract-033-consultant-marketing | review_run_03.json | 0.465 |
| 4 | contract-002-procurement-materials | review_run_05.json | 0.459 |
| 5 | contract-012-saas-bi | review_run_01.json | 0.408 |

## 五、高风险类别漏报

| 风险类别 | 漏报次数 |
|---|---|
| 保密义务 | 4 |
| 交付条件 | 4 |
| 合作范围 | 3 |
| 条款缺失 | 3 |
| 响应时间 | 2 |
| 资质 | 2 |
| 不可抗力 | 1 |
| 数量风险 | 1 |
| 管辖法院 | 1 |
| 质量风险 | 1 |
| 自动续约陷阱 | 1 |
| 退换货限制 | 1 |
| 金额超支风险 | 1 |
| 合同完整性 | 1 |
| 合规风险 | 1 |
| SLA | 1 |
| 业务连续性 | 1 |
| 赔偿责任 | 1 |
| 自动续约且涨价机制不清 | 1 |
| 责任限制 | 1 |
| 源代码 | 1 |
| 违约责任 | 1 |
| 技术管理 | 1 |
| 运营管理 | 1 |
| 信息使用限制不清，未禁止投资竞争对手 | 1 |
| 适用法律 | 1 |
| 平台规则 | 1 |
| 库存管理 | 1 |
| 数据归属 | 1 |
| 人员管理 | 1 |
| 安全责任 | 1 |
| 付款条件 | 1 |
| 排他性 | 1 |
| 营销效果承诺含糊 | 1 |

## 六、Phase 3 质量基线判断（latest-only 口径）

**结论：latest-only 口径下，当前批次评测结果接近质量基线，但仍有改进空间。**

---

*本报告由 `scripts/batch_evaluate.py --latest-only` 自动生成。*