# 漏报归因分析报告 — batch-01

> 生成时间：2026-06-22T11:31:55.713377

## 一、分析总览

| 指标 | 数值 |
|---|---|
| 总样本数 | 33 |
| 已分析样本 | 33 |
| 未运行样本 | 0 |

### 漏报类型分布

| 类型 | 数量 | 说明 |
|---|---|---|
| minor_gap | 12 | 轻微漏报 |
| high_risk_miss | 11 | 高风险漏报 |
| content_coverage_moderate | 5 | 中度覆盖不足 |
| content_coverage_severe | 2 | 严重覆盖不足 |
| no_gap | 2 | 无漏报 |
| timeout | 1 | 超时 |

## 二、高频漏报主题（Top 10）

| 主题 | 漏报次数 | 高风险漏报 | 影响样本 |
|---|---|---|---|
| 条款缺失 | 17 | ⚠️ 是 | contract-003-procurement-office, contract-006-techservice-maintenance, contract-007-techservice-data 等17个 |
| 保密义务 | 8 | ⚠️ 是 | contract-001-procurement-equipment, contract-003-procurement-office, contract-006-techservice-maintenance 等8个 |
| 交付条件 | 7 | ⚠️ 是 | contract-001-procurement-equipment, contract-013-custom-erp, contract-014-custom-app 等7个 |
| 管辖法院 | 6 | ⚠️ 是 | contract-002-procurement-materials, contract-025-agency-regional, contract-026-agency-product 等6个 |
| 合作范围 | 6 | ⚠️ 是 | contract-003-procurement-office, contract-010-saas-erp, contract-012-saas-bi 等6个 |
| 响应时间 | 5 | ⚠️ 是 | contract-006-techservice-maintenance, contract-009-saas-crm, contract-010-saas-erp 等5个 |
| 逻辑矛盾 | 3 | 否 | contract-001-procurement-equipment, contract-003-procurement-office, contract-011-saas-hr |
| 人员管理 | 3 | ⚠️ 是 | contract-004-procurement-it, contract-013-custom-erp, contract-030-strategic-tech |
| 数据安全 | 3 | ⚠️ 是 | contract-004-procurement-it, contract-010-saas-erp, contract-015-custom-ai |
| 解约条件 | 3 | 否 | contract-004-procurement-it, contract-010-saas-erp, contract-012-saas-bi |

## 三、风险数不低但关键风险没抓住

以下样本期望风险数 ≥ 8，但高风险 Recall < 30%：

- `contract-002-procurement-materials`
- `contract-003-procurement-office`
- `contract-004-procurement-it`
- `contract-005-techservice-platform`
- `contract-006-techservice-maintenance`
- `contract-008-techservice-cloud`
- `contract-010-saas-erp`
- `contract-014-custom-app`
- `contract-015-custom-ai`
- `contract-021-consultant-tech`
- `contract-025-agency-regional`
- `contract-026-agency-product`
- `contract-027-agency-online`
- `contract-028-strategic-joint`

## 四、法条依据弱但风险主题抓到了

以下样本主题 Recall ≥ 50%，但法条覆盖率 < 50%：

- `contract-001-procurement-equipment`
- `contract-019-nda-investor`

## 五、失败类型分析：格式问题 vs 内容覆盖问题

| 大类 | 数量 | 占比 |
|---|---|---|
| 输出格式/超时问题 | 1 | 5% |
| 内容覆盖问题 | 18 | 95% |
| 执行/基础设施问题 | 0 | 0% |

**结论**：
- 主要瓶颈在**内容覆盖**——模型未能识别出足够多的风险主题。
- 建议优先优化 prompt 模板和 RAG 召回策略。

## 六、推荐回归测试样本

以下样本覆盖不同类型，漏报最多，最适合作为回归测试基准：

- `contract-003-procurement-office`
- `contract-010-saas-erp`
- `contract-026-agency-product`
- `contract-027-agency-online`
- `contract-006-techservice-maintenance`
- `contract-012-saas-bi`
- `contract-015-custom-ai`
- `contract-033-consultant-marketing`
- `contract-008-techservice-cloud`
- `contract-014-custom-app`

## 七、修复优先级表

### P0：最影响质量基线的问题

- 2 个样本存在严重内容覆盖不足（Recall < 20%）
- 1 个样本超时
- 14 个样本风险数不低但关键高风险漏报严重

### P1：高频漏报主题（≥3次）

- 「条款缺失」漏报 17 次，影响样本: contract-003-procurement-office, contract-006-techservice-maintenance, contract-007-techservice-data
- 「保密义务」漏报 8 次，影响样本: contract-001-procurement-equipment, contract-003-procurement-office, contract-006-techservice-maintenance
- 「交付条件」漏报 7 次，影响样本: contract-001-procurement-equipment, contract-013-custom-erp, contract-014-custom-app
- 「管辖法院」漏报 6 次，影响样本: contract-002-procurement-materials, contract-025-agency-regional, contract-026-agency-product
- 「合作范围」漏报 6 次，影响样本: contract-003-procurement-office, contract-010-saas-erp, contract-012-saas-bi
- 「响应时间」漏报 5 次，影响样本: contract-006-techservice-maintenance, contract-009-saas-crm, contract-010-saas-erp
- 「逻辑矛盾」漏报 3 次，影响样本: contract-001-procurement-equipment, contract-003-procurement-office, contract-011-saas-hr
- 「人员管理」漏报 3 次，影响样本: contract-004-procurement-it, contract-013-custom-erp, contract-030-strategic-tech
- 「数据安全」漏报 3 次，影响样本: contract-004-procurement-it, contract-010-saas-erp, contract-015-custom-ai
- 「解约条件」漏报 3 次，影响样本: contract-004-procurement-it, contract-010-saas-erp, contract-012-saas-bi
- 「责任限制」漏报 3 次，影响样本: contract-004-procurement-it, contract-012-saas-bi, contract-015-custom-ai
- 「资质」漏报 3 次，影响样本: contract-006-techservice-maintenance, contract-014-custom-app, contract-032-techservice-security

### P2：中频漏报主题（2次），可能需要扩展同义归并

- 「培训」漏报 2 次
- 「赔偿责任」漏报 2 次
- 「供应链风险」漏报 2 次
- 「SLA」漏报 2 次
- 「业务连续性」漏报 2 次
- 「质量标准」漏报 2 次
- 「付款条件」漏报 2 次
- 「验收标准」漏报 2 次
- 「适用法律」漏报 2 次
- 「佣金计算」漏报 2 次
- 「区域保护」漏报 2 次
- 「销售指标」漏报 2 次

### P3：低频漏报（1次且非高风险），可暂缓

- 「合同续展风险」漏报 1 次
- 「库存风险」漏报 1 次
- 「权利失衡」漏报 1 次
- 「订单确认风险」漏报 1 次
- 「设备管理」漏报 1 次
- 「覆盖率」漏报 1 次
- 「云计算资源」漏报 1 次
- 「风险提示」漏报 1 次
- 「自动续约且涨价机制不清」漏报 1 次
- 「定制开发源代码不开放」漏报 1 次
- 「性能指标定义含糊」漏报 1 次
- 「协议效力优先条款可能损害劳动者权益」漏报 1 次
- 「脱密期条款不完整」漏报 1 次
- 「信息使用限制不清，未禁止投资竞争对手」漏报 1 次
- 「违约责任」漏报 1 次
- 「竞业限制」漏报 1 次
- 「品牌保护」漏报 1 次
- 「多平台管理」漏报 1 次
- 「退换货」漏报 1 次
- 「漏洞修复时限可能过短」漏报 1 次
- 「自动延长条款可能束缚双方」漏报 1 次
- 「危机公关配合条款不完整」漏报 1 次
- 「自动续展条款可能束缚双方」漏报 1 次
- 「营销效果承诺含糊」漏报 1 次

## 八、最值得优先提升的 10 个主题

| 排名 | 主题 | 漏报次数 | 高风险漏报 | 优先级分 |
|---|---|---|---|---|
| 1 | 条款缺失 | 17 | ⚠️ | 34.0 |
| 2 | 保密义务 | 8 | ⚠️ | 16.0 |
| 3 | 交付条件 | 7 | ⚠️ | 14.0 |
| 4 | 管辖法院 | 6 | ⚠️ | 12.0 |
| 5 | 合作范围 | 6 | ⚠️ | 12.0 |
| 6 | 响应时间 | 5 | ⚠️ | 10.0 |
| 7 | 人员管理 | 3 | ⚠️ | 6.0 |
| 8 | 数据安全 | 3 | ⚠️ | 6.0 |
| 9 | 资质 | 3 | ⚠️ | 6.0 |
| 10 | 培训 | 2 | ⚠️ | 4.0 |

---

*本报告由 `scripts/batch_gap_analyze.py` 自动生成。*