# Latest-Only 漏报归因分析报告 — batch-01

> **口径说明：本报告仅基于每个样本最新一次成功运行，不含历史旧 run。**

> 生成时间：2026-06-22T11:31:55.838291

## 一、分析总览

| 指标 | 数值 |
|---|---|
| 总样本数 | 33 |
| 已分析样本 | 33 |
| 未运行样本 | 0 |

### 漏报类型分布

| 类型 | 数量 | 说明 |
|---|---|---|
| minor_gap | 20 | 轻微漏报 |
| high_risk_miss | 6 | 高风险漏报 |
| content_coverage_moderate | 5 | 中度覆盖不足 |
| no_gap | 2 | 无漏报 |

## 二、高频漏报主题（Top 10）

| 主题 | 漏报次数 | 高风险漏报 | 影响样本 |
|---|---|---|---|
| 保密义务 | 10 | ⚠️ 是 | contract-001-procurement-equipment, contract-002-procurement-materials, contract-006-techservice-maintenance 等10个 |
| 条款缺失 | 9 | ⚠️ 是 | contract-006-techservice-maintenance, contract-007-techservice-data, contract-012-saas-bi 等9个 |
| 管辖法院 | 7 | ⚠️ 是 | contract-002-procurement-materials, contract-005-techservice-platform, contract-025-agency-regional 等7个 |
| 交付条件 | 6 | ⚠️ 是 | contract-001-procurement-equipment, contract-013-custom-erp, contract-029-strategic-supply 等6个 |
| 合作范围 | 6 | ⚠️ 是 | contract-003-procurement-office, contract-012-saas-bi, contract-014-custom-app 等6个 |
| 人员管理 | 4 | ⚠️ 是 | contract-004-procurement-it, contract-006-techservice-maintenance, contract-013-custom-erp 等4个 |
| 解约条件 | 4 | 否 | contract-004-procurement-it, contract-009-saas-crm, contract-010-saas-erp 等4个 |
| 响应时间 | 4 | ⚠️ 是 | contract-009-saas-crm, contract-010-saas-erp, contract-012-saas-bi 等4个 |
| 逻辑矛盾 | 3 | 否 | contract-001-procurement-equipment, contract-003-procurement-office, contract-011-saas-hr |
| 赔偿责任 | 3 | ⚠️ 是 | contract-003-procurement-office, contract-005-techservice-platform, contract-008-techservice-cloud |

## 三、风险数不低但关键风险没抓住

以下样本期望风险数 ≥ 8，但高风险 Recall < 30%：

- `contract-002-procurement-materials`
- `contract-003-procurement-office`
- `contract-023-consultant-legal`
- `contract-027-agency-online`
- `contract-032-techservice-security`
- `contract-033-consultant-marketing`

## 四、法条依据弱但风险主题抓到了

以下样本主题 Recall ≥ 50%，但法条覆盖率 < 50%：

- `contract-001-procurement-equipment`
- `contract-005-techservice-platform`
- `contract-011-saas-hr`

## 五、失败类型分析：格式问题 vs 内容覆盖问题

| 大类 | 数量 | 占比 |
|---|---|---|
| 输出格式/超时问题 | 0 | 0% |
| 内容覆盖问题 | 11 | 100% |
| 执行/基础设施问题 | 0 | 0% |

**结论**：
- 主要瓶颈在**内容覆盖**——模型未能识别出足够多的风险主题。
- 建议优先优化 prompt 模板和 RAG 召回策略。

## 六、推荐回归测试样本

以下样本覆盖不同类型，漏报最多，最适合作为回归测试基准：

- `contract-003-procurement-office`
- `contract-027-agency-online`
- `contract-033-consultant-marketing`
- `contract-012-saas-bi`
- `contract-032-techservice-security`
- `contract-006-techservice-maintenance`
- `contract-013-custom-erp`
- `contract-031-procurement-medical`
- `contract-005-techservice-platform`
- `contract-008-techservice-cloud`

## 七、修复优先级表

### P0：最影响质量基线的问题

- 6 个样本风险数不低但关键高风险漏报严重

### P1：高频漏报主题（≥3次）

- 「保密义务」漏报 10 次，影响样本: contract-001-procurement-equipment, contract-002-procurement-materials, contract-006-techservice-maintenance
- 「条款缺失」漏报 9 次，影响样本: contract-006-techservice-maintenance, contract-007-techservice-data, contract-012-saas-bi
- 「管辖法院」漏报 7 次，影响样本: contract-002-procurement-materials, contract-005-techservice-platform, contract-025-agency-regional
- 「交付条件」漏报 6 次，影响样本: contract-001-procurement-equipment, contract-013-custom-erp, contract-029-strategic-supply
- 「合作范围」漏报 6 次，影响样本: contract-003-procurement-office, contract-012-saas-bi, contract-014-custom-app
- 「人员管理」漏报 4 次，影响样本: contract-004-procurement-it, contract-006-techservice-maintenance, contract-013-custom-erp
- 「解约条件」漏报 4 次，影响样本: contract-004-procurement-it, contract-009-saas-crm, contract-010-saas-erp
- 「响应时间」漏报 4 次，影响样本: contract-009-saas-crm, contract-010-saas-erp, contract-012-saas-bi
- 「逻辑矛盾」漏报 3 次，影响样本: contract-001-procurement-equipment, contract-003-procurement-office, contract-011-saas-hr
- 「赔偿责任」漏报 3 次，影响样本: contract-003-procurement-office, contract-005-techservice-platform, contract-008-techservice-cloud
- 「资质」漏报 3 次，影响样本: contract-006-techservice-maintenance, contract-014-custom-app, contract-032-techservice-security
- 「付款条件」漏报 3 次，影响样本: contract-015-custom-ai, contract-016-custom-blockchain, contract-033-consultant-marketing

### P2：中频漏报主题（2次），可能需要扩展同义归并

- 「供应链风险」漏报 2 次
- 「责任限制」漏报 2 次
- 「质量标准」漏报 2 次
- 「SLA」漏报 2 次
- 「业务连续性」漏报 2 次
- 「适用法律」漏报 2 次

### P3：低频漏报（1次且非高风险），可暂缓

- 「培训」漏报 1 次
- 「合同续展风险」漏报 1 次
- 「库存风险」漏报 1 次
- 「权利失衡」漏报 1 次
- 「订单确认风险」漏报 1 次
- 「设备管理」漏报 1 次
- 「转让限制」漏报 1 次
- 「覆盖率」漏报 1 次
- 「云计算资源」漏报 1 次
- 「风险提示」漏报 1 次
- 「自动续约且涨价机制不清」漏报 1 次
- 「定制开发源代码不开放」漏报 1 次
- 「性能指标定义含糊」漏报 1 次
- 「数据安全」漏报 1 次
- 「协议效力优先条款可能损害劳动者权益」漏报 1 次
- 「脱密期条款不完整」漏报 1 次
- 「信息使用限制不清，未禁止投资竞争对手」漏报 1 次
- 「竞业限制」漏报 1 次
- 「品牌保护」漏报 1 次
- 「多平台管理」漏报 1 次
- 「退换货」漏报 1 次
- 「验收标准」漏报 1 次
- 「安全责任」漏报 1 次
- 「漏洞修复时限可能过短」漏报 1 次
- 「自动延长条款可能束缚双方」漏报 1 次
- 「危机公关配合条款不完整」漏报 1 次
- 「自动续展条款可能束缚双方」漏报 1 次
- 「营销效果承诺含糊」漏报 1 次

## 八、最值得优先提升的 10 个主题

| 排名 | 主题 | 漏报次数 | 高风险漏报 | 优先级分 |
|---|---|---|---|---|
| 1 | 保密义务 | 10 | ⚠️ | 20.0 |
| 2 | 条款缺失 | 9 | ⚠️ | 18.0 |
| 3 | 管辖法院 | 7 | ⚠️ | 14.0 |
| 4 | 交付条件 | 6 | ⚠️ | 12.0 |
| 5 | 合作范围 | 6 | ⚠️ | 12.0 |
| 6 | 人员管理 | 4 | ⚠️ | 8.0 |
| 7 | 响应时间 | 4 | ⚠️ | 8.0 |
| 8 | 赔偿责任 | 3 | ⚠️ | 6.0 |
| 9 | 资质 | 3 | ⚠️ | 6.0 |
| 10 | 付款条件 | 3 | ⚠️ | 6.0 |

---

*本报告由 `scripts/batch_gap_analyze.py` 自动生成。*