# Phase 3 修复待办清单 — batch-01 质量问题收口

> 基于：自动评测报告、漏报归因分析、人工质量审阅三份结论整合
> 生成时间：2026-06-19
> 用途：指导下一轮修复，可直接派工

---

## 一、P0 — 必须在 Phase 4 前修完

### 1.1 长合同审查结果静默截断

| 维度 | 内容 |
|---|---|
| **问题类型** | 执行稳定性 |
| **现象** | contract-015-custom-ai（AI模型定制开发合同）只输出 1 条风险（期望 12 条），`finish_reason: max_tokens`，`completion_tokens: 4096` 触顶。`plain_explanation` 和 `suggested_revision` 为空。用户无法区分"合同没问题"和"系统没审完"。 |
| **影响样本** | contract-015-custom-ai（综合评分 0.150），所有 prompt_tokens > 3000 的长合同 |
| **影响面** | 所有超过约 30 页的合同都会被截断。当前 batch 中 2/5 成功样本 token 接近上限（7893、7877）。 |
| **修复方向** | 方案 A：将 `LLM_MAX_TOKENS` 从 4096 提升到 8192（review.py 第 27 行）。方案 B：实现分段审查——先提取条款列表，再逐条款调用 LLM，最后合并结果。方案 A 为最小改动，方案 B 为长期方案。 |
| **回归样本** | contract-015-custom-ai（必须通过）、contract-016-custom-blockchain（token 最高 7877） |
| **验收标准** | contract-015-custom-ai 输出 ≥ 8 条风险，finish_reason != max_tokens |

### 1.2 4 个样本审查执行失败

| 维度 | 内容 |
|---|---|
| **问题类型** | 执行稳定性 |
| **现象** | batch_report 中记录 3 个样本状态为"失败"（contract-010-saas-erp、contract-013-custom-erp、contract-021-consultant-tech），gap_analysis 中记录 4 个 execution_failure。错误信息均为 "Review not completed: failed"。 |
| **影响样本** | contract-010-saas-erp、contract-013-custom-erp、contract-021-consultant-tech + 1 个未明确 |
| **影响面** | 10 个已运行样本中有 4 个失败（40% 失败率），25 个样本未运行。 |
| **修复方向** | 排查失败根因：是 LLM 超时（300s）、JSON 解析失败、还是 schema 校验失败？review.py 中已有 fallback 和重试逻辑（第 316-343 行），需确认是否生效。增加失败详情日志。 |
| **回归样本** | contract-010-saas-erp、contract-013-custom-erp、contract-021-consultant-tech |
| **验收标准** | 上述 3 个样本审查成功完成，输出完整报告 |

### 1.3 数据安全法条语料空白

| 维度 | 内容 |
|---|---|
| **问题类型** | RAG / 法条语料 |
| **现象** | 数据安全是最常见漏报主题（3 次），且全部标注"依据不足，基于法理分析"。当前 law_corpus.json 只有 43 条（民法典合同编 33 条 + 劳动合同法 10 条），完全没有《个人信息保护法》《数据安全法》《网络安全法》。 |
| **影响样本** | contract-004-procurement-it、contract-015-custom-ai、contract-016-custom-blockchain |
| **影响面** | 所有涉及个人信息处理、数据跨境、网络安全的合同都无法获得法条支撑。 |
| **修复方向** | 在 `scripts/law_corpus.json` 中补充以下法条（至少 20 条核心条文）：《个人信息保护法》第 13/14/17/23/38/55 条；《数据安全法》第 21/27/31/33 条；《网络安全法》第 21/37/41/42 条。更新 `scripts/import_laws.py` 确保新语料可导入。 |
| **回归样本** | contract-011-saas-hr（数据安全法条覆盖率应从 37.5% 提升到 ≥ 60%） |
| **验收标准** | contract-011-saas-hr 中"数据安全与个人信息保护"类风险不再标注"依据不足" |

---

## 二、P1 — 高频问题，建议 Phase 4 初期修完

### 2.1 非劳动合同场景错误引用《劳动合同法》第 23 条

| 维度 | 内容 |
|---|---|
| **问题类型** | RAG / 法条语料 |
| **现象** | 5/7 份样本存在此问题。《劳动合同法》第 23 条关键词（保密、竞业限制）过于宽泛，导致采购合同、代理合同、NDA 中的保密条款都被匹配到劳动合同法。 |
| **影响样本** | contract-004-procurement-it、contract-011-saas-hr、contract-016-custom-blockchain、contract-025-agency-regional、contract-026-agency-product |
| **影响面** | 所有非劳动合同场景的保密/竞业条款都会被错误引用。 |
| **修复方向** | 方案 A：在 `rag.py` 的 `format_law_basis_for_risk()` 中增加合同类型过滤逻辑——根据合同类型排除不适用的法条（如采购合同排除劳动合同法）。方案 B：在 law_corpus.json 中为每条法条增加 `applicable_contract_types` 元数据。方案 C：在 SYSTEM_PROMPT 中增加约束"根据合同类型选择适用法律，劳动合同法仅适用于劳动合同"。 |
| **回归样本** | contract-004-procurement-it（不应出现《劳动合同法》引用） |
| **验收标准** | 非劳动合同样本中不再出现《劳动合同法》第 23 条引用 |

### 2.2 高风险识别偏弱但总风险数不低

| 维度 | 内容 |
|---|---|
| **问题类型** | Prompt / 输出约束 |
| **现象** | 8 个样本期望风险数 ≥ 8 但高风险 Recall < 30%。模型倾向输出"通用风险清单"（违约、付款、验收），忽略"行业特有风险"（金融合规、数据安全、区块链技术风险）。 |
| **影响样本** | contract-004-procurement-it、contract-010-saas-erp、contract-013-custom-erp、contract-015-custom-ai、contract-016-custom-blockchain、contract-021-consultant-tech、contract-025-agency-regional、contract-026-agency-product |
| **影响面** | 所有行业特有合同（金融、科技、区块链、医疗）的核心风险被漏掉。 |
| **修复方向** | 在 SYSTEM_PROMPT（review.py 第 49-101 行）中增加：1）"先识别合同类型，再按类型审查"；2）"必须检查以下行业特有风险维度：金融→合规/数据安全；科技→知识产权/技术标准；区块链→数据权属/合规"；3）增加 USER_PROMPT_TEMPLATE 中的合同类型上下文注入。 |
| **回归样本** | contract-004-procurement-it（应检出数据安全、合规风险）、contract-016-custom-blockchain（应检出技术管理、运营管理） |
| **验收标准** | 高风险 Recall ≥ 50% |

### 2.3 法条"凑数"引用（违约金泛化）

| 维度 | 内容 |
|---|---|
| **问题类型** | Prompt / 输出约束 |
| **现象** | 与违约金无关的风险（争议解决、条款重复等）硬套《民法典》第 585 条。用户查法条会发现文不对题。 |
| **影响样本** | contract-020-nda-partner、contract-025-agency-regional |
| **影响面** | 所有包含"争议解决"类风险的报告。 |
| **修复方向** | 在 SYSTEM_PROMPT 中增加："如果检索不到相关法条，必须标注'依据不足，基于法理分析'，不得引用与风险主题无关的法条"。在 `rag.py` 的 `format_law_basis_for_risk()` 中增加相关性阈值过滤。 |
| **回归样本** | contract-020-nda-partner |
| **验收标准** | 争议解决类风险不再引用违约金条款 |

---

## 三、P2 — 中频问题，可在 Phase 4 中穿插修复

### 3.1 合规风险法条缺失

| 维度 | 内容 |
|---|---|
| **问题类型** | RAG / 法条语料 |
| **现象** | 合规风险漏报 2 次（contract-004-procurement-it、contract-016-custom-blockchain）。 |
| **影响样本** | contract-004-procurement-it、contract-016-custom-blockchain |
| **影响面** | 金融、医疗、科技行业的合规类风险无法获得法条支撑。 |
| **修复方向** | 按行业补充合规法规：《银行业监督管理法》《证券法》《医疗器械监督管理条例》等。优先补充与合同审查最相关的条文。 |
| **回归样本** | contract-004-procurement-it |
| **验收标准** | 合规风险类不再标注"依据不足" |

### 3.2 责任限制识别不足

| 维度 | 内容 |
|---|---|
| **问题类型** | Prompt / 输出约束 |
| **现象** | 责任限制漏报 2 次（contract-004-procurement-it、contract-015-custom-ai）。 |
| **影响样本** | contract-004-procurement-it、contract-015-custom-ai |
| **影响面** | 免责条款、责任上限是合同审查核心维度，漏报会直接影响用户信任。 |
| **修复方向** | 在 SYSTEM_PROMPT 中增加审查维度："必须检查责任限制条款：免责条款是否过于宽泛、赔偿上限是否合理、是否排除法定责任"。 |
| **回归样本** | contract-004-procurement-it |
| **验收标准** | 责任限制类风险检出率 ≥ 80% |

### 3.3 评测脚本同义归并不足

| 维度 | 内容 |
|---|---|
| **问题类型** | 评测资产 |
| **现象** | "退换货" vs "退换货政策"、"合同终止与清算" vs "协议终止"未归并，导致评测偏差。 |
| **影响样本** | contract-025-agency-regional |
| **影响面** | 评测结果准确性，不影响实际审查质量。 |
| **修复方向** | 扩充 `batch_evaluate.py` 中的同义词映射表。 |
| **回归样本** | contract-025-agency-regional |
| **验收标准** | 评测 recall 与人工判断偏差 < 10% |

---

## 四、P3 — 可暂缓，不拦 Phase 4

### 4.1 contract-026-agency-product 评测数据不完整

| 维度 | 内容 |
|---|---|
| **问题类型** | 评测资产 |
| **现象** | expected_manifest.json 中 expected_risk_topics 为空列表，导致评测系统显示 0 分。实际审查质量中等。 |
| **影响样本** | contract-026-agency-product |
| **影响面** | 仅影响评测数据完整性，不影响审查质量。 |
| **修复方向** | 补充 contract-026-agency-product 的 expected_manifest.json。 |
| **回归样本** | contract-026-agency-product |
| **验收标准** | 评测分数从 0.000 恢复到合理值 |

### 4.2 低频漏报主题（1 次且非高风险）

| 维度 | 内容 |
|---|---|
| **问题类型** | Prompt / 输出约束 |
| **现象** | 人员管理、供应链风险、解约条件、设备管理、逻辑矛盾、业务连续性、协议终止、市场推广、库存管理、退换货 各漏报 1 次。 |
| **影响面** | 单次漏报，不构成系统性问题。 |
| **修复方向** | 不单独修复。随 P1 prompt 优化一并覆盖。 |
| **回归样本** | 无专门回归样本 |
| **验收标准** | 下一轮全量评测时观察是否收敛 |

---

## 五、建议执行顺序

### 第一步：修 max_tokens 截断（P0，1 小时）

1. 修改 `backend/app/services/review.py` 第 27 行：`LLM_MAX_TOKENS = 4096` → `LLM_MAX_TOKENS = 8192`
2. 运行 contract-015-custom-ai 回归测试
3. 确认 finish_reason != max_tokens，输出风险数 ≥ 8

### 第二步：补充数据安全法条语料（P0，2 小时）

1. 在 `scripts/law_corpus.json` 中补充《个人信息保护法》《数据安全法》《网络安全法》核心条文（≥ 20 条）
2. 运行 `python scripts/import_laws.py` 导入
3. 运行 contract-011-saas-hr 回归测试
4. 确认"数据安全与个人信息保护"类风险不再标注"依据不足"

### 第三步：排查 3 个执行失败样本（P0，2 小时）

1. 查看 contract-010-saas-erp、contract-013-custom-erp、contract-021-consultant-tech 的 review 日志
2. 确认失败根因（超时/JSON解析/schema校验）
3. 针对性修复
4. 重新运行 3 个样本确认成功

### 第四步：优化 SYSTEM_PROMPT 行业特有风险识别（P1，1 小时）

1. 在 SYSTEM_PROMPT 中增加合同类型识别 + 行业特有风险维度
2. 运行 contract-004-procurement-it、contract-016-custom-blockchain 回归测试
3. 确认高风险 Recall ≥ 50%

### 第五步：修正法条引用逻辑（P1，2 小时）

1. 在 SYSTEM_PROMPT 中增加法条引用约束
2. 在 `rag.py` 的 `format_law_basis_for_risk()` 中增加合同类型过滤
3. 运行 contract-004-procurement-it 回归测试
4. 确认非劳动合同中不再出现《劳动合同法》第 23 条

### 第六步：补充合规法规 + 优化责任限制识别（P2，2 小时）

1. 补充行业合规法规语料
2. 优化 prompt 中的责任限制审查维度
3. 运行 contract-004-procurement-it 回归测试

### 第七步：评测脚本修复 + 数据补全（P2-P3，1 小时）

1. 扩充同义词映射表
2. 补充 contract-026-agency-product 的 expected_manifest.json

---

## 六、Phase 4 推进条件

**必须满足（否则不进 Phase 4）：**
- [ ] contract-015-custom-ai 输出风险数 ≥ 8（max_tokens 截断修复）
- [ ] 3 个执行失败样本全部成功
- [ ] 数据安全法条语料已入库且可检索
- [ ] 非劳动合同场景不再出现《劳动合同法》第 23 条错误引用

**建议满足（强烈建议，但不硬拦）：**
- [ ] 高风险 Recall ≥ 50%（当前 23.3%）
- [ ] 综合评分 ≥ 0.6（当前 0.467）
- [ ] 全量 33 个样本至少运行 1 次

---

## 七、回归样本清单（固定）

| 样本 | 用途 | 验收标准 |
|---|---|---|
| contract-020-nda-partner | 最佳基线回归 | 综合评分 ≥ 0.7 |
| contract-015-custom-ai | max_tokens 截断回归 | 风险数 ≥ 8 |
| contract-004-procurement-it | 通用 vs 行业风险回归 | 高风险 Recall ≥ 50% |
| contract-011-saas-hr | 法条覆盖回归 | 数据安全法条覆盖率 ≥ 60% |
| contract-016-custom-blockchain | 新兴技术合同回归 | 行业特有风险检出 ≥ 1 |
| contract-010-saas-erp | 执行失败回归 | 审查成功完成 |
| contract-013-custom-erp | 执行失败回归 | 审查成功完成 |
| contract-021-consultant-tech | 执行失败回归 | 审查成功完成 |

---

## 八、改动影响范围预估

| 修改项 | 涉及文件 | 是否改代码 | 是否改数据 |
|---|---|---|---|
| max_tokens 提升 | `backend/app/services/review.py` | ✅ 改 1 行 | ❌ |
| 数据安全法条补充 | `scripts/law_corpus.json`、`scripts/import_laws.py` | ❌ | ✅ 新增语料 |
| SYSTEM_PROMPT 优化 | `backend/app/services/review.py` | ✅ 改 prompt 文本 | ❌ |
| RAG 法条过滤逻辑 | `backend/app/services/rag.py` | ✅ 改匹配逻辑 | ❌ |
| 评测脚本修复 | `scripts/batch_evaluate.py` | ✅ 改同义词表 | ❌ |
| expected_manifest 补充 | `07-testing/generated/batch-01/contract-026-*/expected_manifest.json` | ❌ | ✅ 补充数据 |

**总估算：代码改动约 50 行，数据补充约 40 条法条 + 1 个 manifest 文件。**
