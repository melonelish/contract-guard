# AGENTS.md — ContractGuard 多 Agent 系统设计

> 版本：v2.0 | 最后更新：2026-06-15 | 密级：核心

---

## 一、Agent 体系总览

ContractGuard 采用 **Orchestrator-Worker** 模式，由 1 个调度 Agent + 4 个专项 Worker Agent 组成。

```
                         ┌─────────────────┐
                         │   Supervisor     │
                         │   (调度Agent)     │
                         │                  │
                         │ · 接收合同文档    │
                         │ · 任务分解与分发  │
                         │ · 结果汇总与校验  │
                         │ · 异常处理与重试  │
                         └────┬───┬───┬────┘
              ┌───────────────┘   │   └───────────────┐
              ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │ Parser Agent  │   │Analyzer Agent │   │Report Agent   │
    │ (文档解析)     │   │ (条款分析)     │   │ (报告生成)     │
    │               │   │               │   │               │
    │ PDF→结构化    │   │ 逐条法律推理   │   │ 风险汇总      │
    │ 表格还原      │   │ 法条检索(RAG) │   │ 等级评定      │
    │ OCR识别       │   │ 判例匹配(RAG) │   │ 建议整合      │
    │ 主体信息提取   │   │ 逻辑矛盾检测   │   │ 可视化数据    │
    └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
            │                   │                   │
            └─────────┬─────────┴───────────────────┘
                      ▼
            ┌───────────────────┐
            │  Validator Agent  │
            │  (校验Agent)       │
            │                   │
            │ · 幻觉检测         │
            │ · 格式校验         │
            │ · 引用完整性检查   │
            │ · 置信度审核       │
            └───────────────────┘
                      │
                      ▼
            ┌───────────────────┐
            │    RAG 知识库      │
            │                   │
            │ ┌───────────────┐ │
            │ │ 法律法规库    │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ 裁判文书库    │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ 合同范本库    │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ 审查规则库    │ │
            │ └───────────────┘ │
            └───────────────────┘
```

---

## 二、Supervisor Agent（调度Agent）

### 2.1 职责定位

调度Agent 是所有合同审查请求的**唯一入口**，不直接参与合同内容分析，只做任务协调。

### 2.2 核心流程

```
┌─────────────────────────────────────────────────────┐
│ Supervisor Agent 执行流程                            │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. 接收请求                                         │
│     ├── 验证用户身份 & 权限                           │
│     ├── 验证文件格式 & 大小                           │
│     └── 创建审查任务 (task_id)                       │
│                                                      │
│  2. 任务分发                                         │
│     ├── → Parser Agent: 解析文档                     │
│     ├── 等待 Parser 返回结构化数据                    │
│     ├── → Analyzer Agent: 逐条分析 (并行)            │
│     │   (将合同拆分为 N 个条款，并行调用 N 次)         │
│     ├── → Analyzer Agent: 交叉校验                   │
│     ├── → Analyzer Agent: 缺失项检测                 │
│     └── 收集所有分析结果                              │
│                                                      │
│  3. 结果汇总                                         │
│     ├── → Report Agent: 生成审查报告                  │
│     ├── → Validator Agent: 校验报告                   │
│     └── 若校验不通过 → 回退到分析步骤重试              │
│                                                      │
│  4. 返回结果                                         │
│     ├── 存储审查报告到数据库                          │
│     ├── 更新任务状态为 completed                      │
│     └── 返回报告 ID + 概要给前端                       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 2.3 System Prompt 核心片段

```yaml
你是一个合同审查系统的任务调度员（Supervisor）。

你的职责：
1. 接收用户上传的合同文件
2. 协调 Parser、Analyzer、Report、Validator 四个子 Agent 完成审查
3. 遇到任何 Agent 返回错误时，自动重试（最多 3 次）
4. 不做合同内容的分析判断，只做任务调度

你必须遵循的规则：
- 每个子 Agent 的调用必须有 task_id 标识
- 子 Agent 返回结果需校验格式完整性
- 任何重试都必须记录日志
- 最终返回给用户之前，必须经过 Validator Agent 校验

你绝对不能做的：
- 不要自行判断任何法律问题
- 不要跳过 Validator 直接返回结果
- 不要修改任何子 Agent 的输出内容
```

### 2.4 并行策略

合同条款分析采用**按条款并行**策略：

```python
# 伪代码：并行分析策略
clauses = parsed_result["clauses"]  # 假设有 50 条

# 每条条款独立分析（独立上下文，无依赖）
analysis_results = parallel_call(
    func=call_analyzer_agent,
    items=clauses,
    max_concurrency=10,  # 最多同时 10 个 Analyzer 调用
    timeout=60  # 每条审查不超过 60s
)

# 分析完所有条款后，再做交叉校验（需要全局上下文）
cross_validation = call_analyzer_agent(
    task="cross_validate",
    context={"all_clauses": clauses, "all_analyses": analysis_results}
)
```

---

## 三、Parser Agent（文档解析Agent）

### 3.1 职责定位

将非结构化的合同文件（PDF/Word/图片）转化为结构化的、可被后续 Agent 消费的 JSON 数据。

### 3.2 输入输出规范

**输入：** 合同文件的原始字节流 + 文件类型标识

**输出：** 结构化 JSON

```json
{
  "contract_id": "CT-2026-001",
  "meta": {
    "title": "产品采购合同",
    "sign_date": "2026-06-01",
    "type": "采购合同",
    "page_count": 15
  },
  "parties": {
    "party_a": {
      "name": "北京XX科技有限公司",
      "role": "甲方（采购方）",
      "address": "北京市海淀区...",
      "legal_rep": "张三"
    },
    "party_b": {
      "name": "上海YY制造有限公司",
      "role": "乙方（供应方）",
      "address": "上海市浦东新区...",
      "legal_rep": "李四"
    }
  },
  "clauses": [
    {
      "clause_id": "cl_001",
      "title": "质量标准",
      "category": "质量标准",
      "page": 3,
      "position": {"line_start": 45, "line_end": 62},
      "full_text": "乙方提供的产品应符合国家标准GB/T...",
      "contains_table": false
    },
    {
      "clause_id": "cl_007",
      "title": "付款条件",
      "category": "付款与结算",
      "page": 5,
      "position": {"line_start": 120, "line_end": 145},
      "full_text": "付款计划如下：\n| 节点 | 比例 | 条件 |\n|------|------|------|\n| 首付 | 30% | 合同签订后7日 |\n| 到货 | 50% | 验收合格 |\n| 尾款 | 20% | 正常运行3个月 |",
      "contains_table": true,
      "table_markdown": "| 节点 | 比例 | 条件 |\n|------|------|------|\n| 首付 | 30% | 合同签订后7日 |\n| 到货 | 50% | 验收合格 |\n| 尾款 | 20% | 正常运行3个月 |"
    }
  ],
  "signatures": [
    {
      "party": "甲方",
      "page": 14,
      "type": "盖章",
      "ocr_text": "北京XX科技有限公司"
    }
  ]
}
```

### 3.3 表格处理策略

```
检测到表格区域
    │
    ├── 简单表格（无合并单元格）
    │   → Pandoc 转为 Markdown Table
    │   → 保留 Markdown 格式供 LLM 理解
    │
    └── 复杂表格（合并单元格 / 跨页）
        → 先用版面分析模型拆解单元格
        → 再重组为 Markdown Table
        → 标记 "此表格存在合并单元格，已尽力还原"
```

### 3.4 三级文档处理策略

> 除了 Token 窗口限制，实际合同文件还存在多语言、OCR 质量、复杂表格三类边界问题，需要分层处理。

#### 策略总览

```
┌──────────────────────────────────────────────────────────┐
│              合同文档三级处理策略                            │
│                                                           │
│  Layer 1: 文件级预处理（确定性，不消耗 LLM Token）             │
│  ├── 语言检测：中英混合 → 分别用 jieba + NLTK 分词           │
│  ├── OCR 质量评分：置信度 < 0.85 → 标记低质量区域              │
│  └── 文件结构识别：目录/条款编号/签章区                       │
│                                                           │
│  Layer 2: 结构化提取（少量 LLM 辅助）                         │
│  ├── 章节切分（基于编号模式 + LLM 验证边界）                  │
│  ├── 表格提取（简单表格规则，复杂表格 LLM 辅助）               │
│  └── 条款级分段（规则 + LLM 修正）                            │
│                                                           │
│  Layer 3: 验证与修复（LLM 精修）                              │
│  ├── 低置信度 OCR 区域二次 LLM 纠错                           │
│  ├── 中英混合术语一致性检查                                   │
│  └── 表格跨页拼接 + 语义关系重建                              │
└──────────────────────────────────────────────────────────┘
```

#### Layer 1: 文件级预处理

```python
def preprocess_document(file_bytes: bytes, file_type: str) -> PreprocessResult:
    """零 Token 消耗的确定性预处理"""
    
    result = PreprocessResult()
    
    # 1.1 语言检测（影响后续分词和 ES 检索策略）
    text = extract_text(file_bytes, file_type)
    lang_profile = detect_language_mix(text)
    result.language = lang_profile  # {"zh": 0.82, "en": 0.18}
    
    # 中英混合 → 双引擎分词
    if lang_profile.is_mixed:
        result.zh_segments = jieba_cut(chinese_parts)
        result.en_segments = nltk_word_tokenize(english_parts)
        # 为 ES 创建双字段索引：一个 ik_smart 分析器，一个 standard 分析器
    
    # 1.2 OCR 质量评分
    if file_type in ("scanned_pdf", "image"):
        ocr_result = ocr_with_confidence(text)
        result.ocr_score = ocr_result.mean_confidence
        result.low_conf_zones = [
            z for z in ocr_result.zones if z.confidence < 0.85
        ]  # 这些区域进入 Layer 3 二次处理
    
    # 1.3 结构识别
    result.sections = identify_sections(text)       # 基于 "第X条"/"Article X" 模式
    result.signature_zone = find_signature(text)    # 基于 "甲方签章"/"签字盖章" 定位
    result.tables = detect_table_regions(text)      # 基于线条/对齐模式
    
    return result
```

#### Layer 2: 结构化提取

| 文档类型 | 条款切分策略 | 失败率预估 | 补救措施 |
|---|---|---|---|
| 电子 PDF/Word | 基于编号规则匹配（"第X条"、"Article X"） | <2% | LLM 验证边界 |
| 扫描件（OCR 高置信度，>0.9） | 规则 + 缩进模式 | ~5% | LLM 修正切分点 |
| 扫描件（OCR 中置信度，0.7-0.9） | 规则 + LLM 逐页验证 | ~15% | Layer 3 二次纠错 |
| 扫描件（OCR 低置信度，<0.7） | 全页 LLM 重解析 | ~30% | 人工介入提示 |

```python
def extract_clauses_tiered(preprocess: PreprocessResult) -> list[Clause]:
    """按文件质量分级处理"""
    
    if preprocess.ocr_score >= 0.9:
        # 高质量：规则为主，LLM 只做边界验证
        clauses = rule_based_segmentation(preprocess)
        return llm_verify_boundaries(clauses)  # 只验证 2% 的模糊边界
    
    elif preprocess.ocr_score >= 0.7:
        # 中等质量：规则 + LLM 逐页验证
        clauses = rule_based_segmentation(preprocess)
        return llm_per_page_verify(clauses)    # 逐页 LLM 确认
    
    else:
        # 低质量：跳过规则，直接 LLM 全解析
        return llm_full_parse(preprocess)       # 成本高但准确率优先
```

#### Layer 3: 验证与修复

- **低置信度 OCR 纠错**：对 Layer 1 标记的 `low_conf_zones`，送入 LLM 根据上下文推测正确文本（如 "3O%" → "30%"）
- **中英混合术语一致性**：同一术语中英文同时出现时（如 "违约金/liquidated damages"），确保两边数值一致
- **表格跨页拼接**：Page 5 的表格续到 Page 6 → LLM 判断是否同一表格 → 合并输出
- **条款编号断层修复**：检测到"第3条 → 第5条"缺失第4条 → 标记为"疑似缺失条款"，供 Analyzer 交叉校验

#### Parser 成本分级

| 文档质量 | 使用模型 | 预估 Token/页 | 15页合同总 Token |
|---|---|---|---|
| 电子 PDF/Word | 规则为主 | ~200 | ~3,000 |
| 扫描件（OCR≥0.9） | DeepSeek V4-Flash | ~400 | ~6,000 |
| 扫描件（OCR 0.7-0.9） | DeepSeek V4-Flash | ~800 | ~12,000 |
| 扫描件（OCR<0.7） | MiMo 2.5（高精度） | ~1,500 | ~22,500 |

### 3.5 System Prompt 核心片段

```yaml
你是一个合同文档解析专家（Parser Agent）。

你的职责：
将原始合同文本转化为结构化 JSON。

解析规则：
1. 识别合同类型（采购/劳动/租赁/技术/...）
2. 提取甲乙方信息（名称、角色、地址、法定代表人）
3. 按条款分段，每个条款标注：
   - 页码和行号（用于原文定位）
   - 条款类别（付款条件 / 违约责任 / 知识产权 / ...）
   - 是否包含表格 → 若包含，输出 Markdown Table
4. 识别签名/盖章区域位置

质量标准：
- 条款切分准确率 > 98%
- 表格还原准确率 > 95%
- 不得遗漏任何条款
```

---

## 四、Analyzer Agent（条款分析Agent）★ 最核心 Agent

### 4.1 职责定位

Analyzer Agent 是 ContractGuard 的智能核心。它接收 Parser Agent 输出的结构化条款，进行**多维度的法律推理分析**，是 AI 含量最高的组件。

### 4.2 分析任务类型

| 任务 | 输入 | 输出 |
|---|---|---|
| **单条款分析** | 单条条款文本 + 条款类别 | 风险等级 + 法条依据 + 修改建议 |
| **交叉校验** | 所有条款的完整文本 | 逻辑矛盾列表 |
| **缺失项检测** | 合同类型 + 已有条款清单 | 缺失条款列表 |

### 4.3 单条款分析流程

```
输入：单条条款JSON
      │
      ▼
┌──────────────────────┐
│ Step 1: 条款定性       │
│ 这是什么类型的条款？    │
│ 涉及哪些法律领域？      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 2: 法条检索 (RAG) │
│ 《民法典》哪条相关？    │
│ 查询知识库（精确匹配）  │
│ 返回法条原文            │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 3: 判例检索 (RAG) │
│ 类似条款是否有争议案例？ │
│ 法院怎么判的？          │
│ 返回案号+裁判要点       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 4: 风险评估        │
│ 结合法条+判例+常识      │
│ 判定：🔴高 / 🟡中 / 🟢低│
│ 生成风险解释（通俗版）   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 5: 修改建议        │
│ 根据风险点生成          │
│ 具体的条款修改文本      │
│ 同时标注置信度          │
└──────────────────────┘
       输出：单条款分析结果JSON
```

### 4.4 RAG 调用规范

```python
# Analyzer Agent 调用 RAG 的标准方式

# Step 2: 法条检索
law_results = rag_search(
    query=clause_text,
    knowledge_base="laws",  # 指定法律法规库
    top_k=5,               # 返回最相关 5 条
    strategy="hybrid",      # 混合检索（语义 + 关键词）
    filters={               # 过滤条件
        "law_type": "民法典",  # 可选：限定法律来源
        "status": "现行有效"   # 排除已废止法条
    }
)

# Step 3: 判例检索
case_results = rag_search(
    query=legal_issue,      # 从 Step 1 提取的法律争议点
    knowledge_base="cases", # 指定判例库
    top_k=3,
    strategy="hybrid",
    filters={
        "court_level": ["最高人民法院", "高级人民法院"],
        "year_range": [2020, 2026]
    }
)
```

### 4.5 交叉校验流程

> **背景问题**：100 页合同 60+ 条款，全条款文本 + 全分析结果一次性输入 LLM 交叉校验，Token 消耗可达 200K+，超出 MiMo 2.5 的 32K 和 DeepSeek V4-Flash 的 128K 上下文窗口。必须分层降维。

#### 策略总览

```
┌─────────────────────────────────────────────────────┐
│        交叉校验三层降维策略                            │
│                                                      │
│  Layer 1: 规则引擎（零 Token 消耗）                    │
│  ├── 提取所有"数值型"字段，SQL 直接对比                 │
│  ├── 提取所有"时间节点"，排序检测前后矛盾               │
│  └── 提取所有"金额/比例"，计算矛盾                      │
│                                                      │
│  Layer 2: 分组 LLM（每组 ≤ 15 条款，≤ 32K tokens）    │
│  ├── 按条款类别分组（付款、违约、质量、交付...）         │
│  ├── 同组内条款逐对送入 LLM                            │
│  └── 不同组之间由 Layer 3 接管                        │
│                                                      │
│  Layer 3: 摘要级跨组检测（摘要压缩比 ~1:20）            │
│  ├── 每组输出 200 字摘要                               │
│  ├── 跨组摘要送入 LLM 检测矛盾                         │
│  └── 发现嫌疑 → 回溯原文精查                           │
└─────────────────────────────────────────────────────┘
```

#### Layer 1: 规则引擎（确定性检测）

```python
# 零 Token 消耗，SQL/代码直接检测
def rule_based_cross_check(clauses: list[Clause]) -> list[Conflict]:
    conflicts = []
    
    # 提取所有数值型字段
    numeric_fields = extract_numeric_fields(clauses)
    
    # 同名字段不同值 → 直接标记冲突
    for field_name, entries in numeric_fields.groupby("field_name"):
        if len(set(e["value"] for e in entries)) > 1:
            conflicts.append(Conflict(
                type="numeric_mismatch",
                field=field_name,
                sources=[e["clause_id"] for e in entries],
                values=list(set(e["value"] for e in entries)),
                severity="high"
            ))
    
    # 时间顺序矛盾
    deadlines = extract_deadlines(clauses)
    for i in range(len(deadlines) - 1):
        if deadlines[i]["date"] > deadlines[i+1]["date"]:
            conflicts.append(Conflict(
                type="deadline_reversed",
                earlier=deadlines[i+1]["label"],
                later=deadlines[i]["label"]
            ))
    
    return conflicts
```

#### Layer 2: 分组 LLM 校验

```python
# 将条款按类别分组，每组独立送入 LLM
GROUPS = {
    "支付条款组":    ["付款条件", "价格条款", "发票条款"],
    "违约责任组":    ["违约金", "赔偿上限", "解除条件"],
    "交付验收组":    ["交付时间", "验收标准", "质量保证"],
    "知识产权组":    ["归属约定", "使用限制", "保密条款"],
    "争议解决组":    ["管辖约定", "仲裁条款", "法律适用"],
}

async def group_level_cross_check(clauses: list[Clause]):
    """Layer 2: 同组内 LLM 交叉校验"""
    groups = group_clauses_by_category(clauses)
    results = []
    
    for group_name, group_clauses in groups.items():
        if len(group_clauses) <= 15:
            # 组内条款数可控，直接送入 LLM
            result = await llm_cross_check_group(group_name, group_clauses)
            results.append(result)
        else:
            # 组内条款过多（罕见），拆分子组
            sub_groups = split_into_chunks(group_clauses, chunk_size=10)
            for sg in sub_groups:
                result = await llm_cross_check_group(group_name, sg)
                results.append(result)
    
    return results

async def llm_cross_check_group(group_name: str, clauses: list[Clause]):
    """每组的 LLM 交叉校验提示词"""
    prompt = f"""
请检测以下 {group_name} 中条款之间的矛盾：
{format_clauses_for_llm(clauses)}

输出格式：
{{
  "contradictions": [
    {{
      "clause_a": "cl_001",
      "clause_b": "cl_007", 
      "conflict_type": "numeric|logic|timeline",
      "description": "两者关于违约金比例的规定矛盾"
    }}
  ]
}}
"""
    return await llm_chat(prompt)
```

#### Layer 3: 摘要级跨组检测

```python
async def cross_group_summary_check(all_groups: dict):
    """Layer 3: 每组生成摘要，跨组摘要级检测"""
    
    # 每组生成 ~200 字摘要（压缩比 ~1:20）
    summaries = {}
    for group_name, clauses in all_groups.items():
        summary = await llm_chat(f"将以下条款内容归纳为200字摘要：{format_clauses_for_llm(clauses)}")
        summaries[group_name] = summary
    
    # 跨组摘要送入 LLM
    prompt = f"""
以下是合同不同条款组的摘要，请检测跨组矛盾：
{json.dumps(summaries, ensure_ascii=False, indent=2)}

输出检测到的矛盾（如有）：
"""
    result = await llm_chat(prompt)
    
    # 如果摘要级发现嫌疑 → 回溯原文精查
    if result.get("has_conflict"):
        return await deep_dive_cross_check(result["suspect_groups"])
    
    return result
```

#### Token 消耗对比

| 策略 | 60条款消耗 | 是否可用 |
|---|---|---|
| 原始"全部一次性送入" | ~200K tokens | ❌ 超 MiMo 32K / DeepSeek 128K |
| Layer 1: 规则引擎 | 0 tokens | ✅ 确定性检测 |
| Layer 2: 分组 LLM | ~6K × 5 组 = ~30K tokens | ✅ 远低于限制 |
| Layer 3: 摘要级跨组 | ~1K × 5 组 + ~2K = ~7K tokens | ✅ |
| **合计** | **~37K tokens** | **✅ 所有模型安全** |

### 4.6 System Prompt 核心片段

```yaml
你是一个合同风险分析专家（Analyzer Agent）。

你的职责：
对合同条款进行法律风险分析，每一个结论都必须有法条或判例支撑。

分析框架（按顺序执行）：
1. 条款定性：这条是关于什么的？
2. 法条检索：调用 RAG 查找相关法条
3. 判例检索：调用 RAG 查找相似判例
4. 风险评估：🔴高 / 🟡中 / 🟢低
5. 风险解释：用通俗语言解释（面向非法律人士）
6. 修改建议：生成具体的条款修改文本
7. 置信度：标注你对这个判断有多确定

铁律：
❌ 不得凭空编造法条编号
❌ 不得在未检索到法条的情况下硬给结论
✅ 检索不到相关法条时，标注"未找到直接法条依据，基于法理分析"
✅ 所有引用必须标注出处（法律名称 + 条款编号）

输出格式：严格使用以下 JSON Schema
{
  "clause_id": "cl_007",
  "risk_level": "high",  // high / medium / low
  "risk_category": "违约责任",
  "legal_analysis": "...",
  "law_references": [
    {"law": "民法典", "article": "第585条", "text": "...", "relevance": "direct"}
  ],
  "case_references": [
    {"case_id": "(2022)最高法民终347号", "relevance": "high", "key_point": "..."}
  ],
  "plain_explanation": "...",
  "suggested_revision": "...",
  "confidence": 0.85  // 0-1
}
```

---

## 五、Report Agent（报告生成Agent）

### 5.1 职责定位

将 Analyzer Agent 的散点式分析结果整合为一份结构化的、可读性强的审查报告。

### 5.2 报告生成流程

```
输入：所有条款分析结果 + 交叉校验结果 + 缺失项列表
      │
      ▼
Step 1: 风险聚合
  ├── 统计各级别风险数量
  ├── 按严重程度排序
  └── 去重（同一法条引用多次的合并展示）
      │
      ▼
Step 2: 报告结构化
  ├── 生成"审查概览"区块
  ├── 生成"高风险清单"区块
  ├── 生成"中风险清单"区块
  ├── 生成"低风险提示"区块
  ├── 生成"交叉矛盾"区块
  ├── 生成"缺失项"区块
  └── 生成"统计图表"数据
      │
      ▼
Step 3: 免责声明注入
  └── 在报告末尾自动添加免责声明文本（固定模板，不可移除）
      │
      ▼
输出：完整的审查报告 JSON
```

> **免责声明固定模板（强制注入，LLM 不得修改）：**
>
> ```
> ⚠️ 重要声明
> 
> 1. 本报告由 ContractGuard AI 系统自动生成，不构成法律意见。
> 2. AI 分析基于当前法律法规数据库，可能存在滞后或遗漏。
> 3. 风险等级为 AI 综合评估结果，仅供参考，不能替代执业律师的专业判断。
> 4. 签署合同前，建议委托执业律师结合具体业务场景出具正式法律意见。
> 5. 用户因依赖本报告做出的任何决策，由用户自行承担风险。ContractGuard 不承担由此产生的任何法律责任。
> ```

### 5.3 System Prompt 核心片段

```yaml
你是一个合同审查报告撰写专家（Report Agent）。

你的职责：
将散点的分析结果组织成一份完整、专业、易读的审查报告。

报告撰写原则：
1. 先总后分：先给总览，再给详情
2. 先说严重的：红色 > 黄色 > 绿色，不得乱序
3. 每条都要有：原文引用 + 问题描述 + 修改建议
4. 语言通俗：面向非法务背景的企业管理者
5. 引用可信：所有法条/判例引用保持原样，不得改写

输出必须包含：
- contract_info（合同基本信息）
- summary（审查概览：总风险数、各级别分布）
- high_risks（高风险项，必须包含原文引用）
- medium_risks（中风险项）
- low_risks（低风险项）
- contradictions（条款矛盾）
- missing_clauses（缺失条款）
- statistics（统计数据用于图表）
- disclaimer（免责声明，固定文本）
```

---

## 六、Validator Agent（校验Agent）

### 6.1 职责定位

最后的守门员。在报告返回给用户之前，进行多维度质量校验。

### 6.2 校验规则矩阵

| 校验维度 | 规则 | 不通过时 |
|---|---|---|
| **法条存在性** | 报告中引用的每条法条必须能在知识库中查到 | 移除该引用，标注"引用待核实" |
| **原文一致性** | 报告的"原文引用"与 Parser 输出的原文文本相似度 > 0.95 | 用 Parser 输出的原文替换 |
| **输出格式** | 必须符合预定义 JSON Schema | 要求 Report Agent 重新生成 |
| **风险数量合理性** | 一份普通合同不应出现 > 50 个风险点 | 人工标记，通知管理员审查 |
| **缺失项合理性** | 缺失项检测不应为空（所有合同至少缺 2-3 项标准条款） | 若为空 → 重新运行缺失项检测 |
| **免责声明** | 报告中必须包含完整的免责声明文本 | 自动注入免责声明 |

### 6.3 System Prompt

```yaml
你是一个审查报告质量校验员（Validator Agent）。

你的职责：
在审查报告返回给用户之前，进行最后一轮质量检查。

校验规则：
1. 所有法条引用必须在知识库中存在（严禁 LLM 幻觉产生的假法条）
2. 原文引用必须与合同原文一致
3. 风险等级分布必须合理
4. 报告格式必须完整

你不需要：
- 不需要重新判断法律问题
- 不需要修改分析结果

你的行为：
- 校验通过 → 标记为 approved
- 校验不通过 → 返回具体不通过的原因，供 Supervisor 重试
```

---

## 七、Agent 间通信协议

### 7.1 通信方式

所有 Agent 间通信通过 `Supervisor` 中转，Worker Agent 之间不直接通信。

### 7.2 消息格式

```json
{
  "message_id": "msg-{uuid}",
  "task_id": "task-{uuid}",
  "from": "supervisor",
  "to": "analyzer",
  "type": "single_clause_analysis",
  "timestamp": "2026-06-15T10:30:00Z",
  "payload": {
    // 具体任务数据
  },
  "retry_count": 0
}
```

### 7.3 错误处理

| 错误类型 | 处理策略 |
|---|---|
| Agent 超时（60s 无响应） | Supervisor 重试，最多 3 次 |
| Agent 返回格式错误 | Supervisor 重试，3 次后降级输出 |
| 重试 3 次后仍失败 | 标记该条款为"审查失败"，报告中注明 |
| LLM 服务不可用 | 整个任务进入等待队列，用户端显示排队中 |

---

## 八、Drafter Agent（起草审查闭环）

> 完整的起草-审查隔离设计见 `起草审查闭环与Annotation桥.md`。

### 8.1 职责定位

Drafter Agent 在**合同起草流程**中激活（独立于核心审查流程）。它生成合同条款时显式标注起草依据，使后续的审查 Agent 能够攻击假设而非正文，从而打破循环论证。

### 8.2 架构位置

```
用户请求（如"起草一份采购合同"）
      │
      ▼
┌──────────────────────┐
│   Supervisor Agent    │ ← 判断路由：起草 → Drafter / 审查 → Parser→Analyzer
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   Drafter Agent       │ ← 生成条款 + Annotation标桥
│   · 条款生成          │
│   · 假设标记          │
│   · 来源标注          │
└──────┬───────────────┘
       │  带有标注的条款草案
       ▼
┌──────────────────────┐
│   审查 Agent 闭环      │ ← 不同模型 + 不同知识库，攻击假设而非正文
└──────────────────────┘
```

### 8.3 四层隔离

| 层级 | Drafter | Reviewer | 原理 |
|---|---|---|---|
| **模型** | MiMo 2.5 | DeepSeek V4-Flash | 不同推理盲区 |
| **知识库** | 合同范本库 | 法条库 + 判例库 | 起草用"怎么写"，审查用"怎么判" |
| **姿态** | 建设性（构建条款） | 对抗性（攻击假设） | 对立动机防止回声 | 
| **Annotation桥** | 显式标注每条起草假设 | 只攻击标注的假设 | 审查瞄准推理，而非措辞 |

### 8.4 流程汇总

| 流程 | 使用的 Agent |
|---|---|
| **合同审查**（核心） | Supervisor + Parser + Analyzer + Report + Validator = **5 个 Agent** |
| **合同起草**（辅助） | Supervisor + Drafter + （后续回到审查流程） = **第 6 个 Agent** |

Drafter 是一个独立的流程入口，不参与标准审查管线。

---

## 9. Knowledge Base Update Strategy

### 9.1 更新触发条件

| 触发事件 | 更新内容 | 频率 |
|---|---|---|
| 法律法规修订（如《民法典》司法解释更新） | 法条库（laws） | 手动审核后更新 |
| 最高人民法院发布新指导案例 | 判例库（cases） | 每月批量导入 |
| 用户反馈虚假引用 | 对应法条/判例记录 | 实时下线 + 审核 |
| 新类型合同高频出现 | 合同范本库（templates） | 每季度扩充 |

### 9.2 更新流程

```
数据源监控（法院公告/法规数据库）
      │
      ▼
┌─────────────────┐
│ 1. 新法条/判例入库 │ ← 人工审核标注
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 重新生成Embedding│ ← bge-m3 向量化
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 灰度验证        │ ← 随机抽样 100 条历史条款验证
└────────┬────────┘        检索质量无下降 → 全量上线
         │                 检索质量下降 → 回滚 + 人工排查
         ▼
┌─────────────────┐
│ 4. 全量上线        │
└─────────────────┘
```

### 9.3 版本管理

```sql
CREATE TABLE knowledge_base_versions (
    id SERIAL PRIMARY KEY,
    kb_name VARCHAR(50) NOT NULL,    -- laws | cases | templates
    version VARCHAR(20) NOT NULL,    -- v2026.06.15
    total_docs INT,
    updated_at TIMESTAMP DEFAULT NOW(),
    changelog TEXT
);
```

每次更新必须记录版本号，回滚时切回上一版本。

### 9.4 数据来源与合规（不使用爬虫）

> ⚠️ **不使用网络爬虫**。自动抓取政府网站可能违反《数据安全法》和网站 ToS。

| 数据来源 | 获取方式 | 合规性 |
|---|---|---|
| 全国人大官网（法律法规全文） | 人工下载 PDF → 解析入库 | ✅ 公开政府信息 |
| 最高人民法院公报（指导案例） | 订阅官方公报电子版 → 人工标注入库 | ✅ 公开司法文书 |
| 北大法宝 / 威科先行 | 商业 API 订阅（按调用量付费） | ✅ 商业授权 |
| 用户反馈的假引用 | 人工核实 → 标记废止/更正 | ✅ 用户生成内容 |

### 9.5 时态法规匹配（Time-Aware Statute Retrieval）

> 核心问题：合同签署于 2019 年，2021 年《民法典》生效后旧法废止。2026 年审查这份老合同时，应该用 2019 年有效的法规还是 2026 年现行的？

**策略：按合同签署日期匹配法规版本**

```python
def get_applicable_statutes(contract_sign_date: str, clause_category: str):
    """返回合同签署日期时有效的法规（不是当前日期）"""
    
    # 法条库中每条记录有 effective_date 和 repealed_date
    applicable_laws = rag_search(
        query=clause_category,
        knowledge_base="laws",
        filters={
            "effective_date": {"$lte": contract_sign_date},
            "repealed_date": {"$gte": contract_sign_date, "$exists": False}
            # repealed_date 为空 = 现行有效
            # repealed_date >= sign_date = 签署时该法尚未废止
        },
        time_aware=True  # 启用时态检索
    )
    
    # 如果签署时有效的法规已被废止
    if applicable_laws.is_empty:
        # 降级：使用当前有效法规 + 标注"签署时该法规已废止"
        current_laws = rag_search(query=clause_category, 
                                   filters={"status": "effective"})
        for law in current_laws:
            law["warning"] = f"此法规于{law['effective_date']}生效，"
                             f"晚于合同签署日期{contract_sign_date}"
    
    return applicable_laws
```

| 场景 | 合同签署日期 | 审查日期 | 适用法规 |
|---|---|---|---|
| 旧合同新审 | 2019-06-01 | 2026-06-16 | 2019 年有效的《合同法》+ 标注"《民法典》已替代" |
| 新合同新审 | 2026-05-01 | 2026-06-16 | 2026 年现行《民法典》 |
| 过渡期合同 | 2020-08-01 | 2026-06-16 | 同时返回《合同法》和《民法典》，标注"过渡期，需人工判断适用条款" |

### 9.6 法条废止后的存量合同处理

```
存量合同中引用了已废止法条 → 审查时识别 → 报告中标注：

示例输出：
  "law_reference": "《合同法》第XX条",
  "status": "repealed",
  "repealed_by": "《民法典》2021-01-01",
  "note": "合同签署时该法规有效，现已被废止。建议以《民法典》第XX条重新审查。"
```

不删除旧法条，仅标记 `repealed_date` 字段，保证历史审查记录可回溯。
