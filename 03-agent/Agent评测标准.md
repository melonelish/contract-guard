# Agent 评测标准

> 版本：v1.0 | 最后更新：2026-06-15

---

## 一、评测体系总览

```
                  ┌─────────────────────────┐
                  │    端到端评测 (E2E)       │
                  │   整份合同的审查结果 vs     │
                  │   律师标注的 Ground Truth  │
                  └───────────┬─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐   ┌────────▼───────┐   ┌────────▼───────┐
│ Parser 评测   │   │ Analyzer 评测   │   │ Report 评测    │
│ 结构化准确率   │   │ 风险识别准确率   │   │ 报告质量        │
└───────────────┘   └────────────────┘   └───────────────┘
```

---

## 二、评测数据集

### 2.1 数据来源

| 来源 | 数量 | 用途 |
|---|---|---|
| 公开裁判文书网合同纠纷案 | 500 份 | 训练/验证集 |
| 律所合作提供（脱敏） | 200 份 | 测试集 |
| 法务顾问人工构造 | 50 份 | 边界用例测试 |
| 用户真实上传（授权脱敏） | 持续增长 | 持续评测 |

### 2.2 标注标准

每份合同由 **2 名执业律师独立标注**，标注内容包括：
- 每条条款的风险等级（高/中/低）
- 关联法条编号
- 标准修改建议

标注一致性（Inter-Annotator Agreement, IAA）：≥ 85%（通过则取交集作为 Ground Truth）

---

## 三、Parser Agent 评测

| 指标 | 定义 | 目标值 |
|---|---|---|
| 条款切分准确率 | 正确识别的条款数 / 实际条款总数 | ≥ 98% |
| 表格还原准确率 | 正确还原的表格数 / 实际表格总数 | ≥ 95% |
| 签约主体识别率 | 正确识别甲乙方名称/角色的合同比例 | ≥ 99% |
| 页码定位准确率 | 条款页码定位偏差 ≤1 页的比例 | ≥ 95% |

---

## 四、Analyzer Agent 评测（核心）

### 4.1 定量指标

| 指标 | 定义 | 目标值 |
|---|---|---|
| **风险识别精确率 (Precision)** | TP / (TP + FP) | ≥ 88% |
| **风险识别召回率 (Recall)** | TP / (TP + FN) | ≥ 90% |
| **风险等级分类准确率** | 三级分类完全匹配的比例 | ≥ 85% |
| **法条引用准确率** | 引用的法条真实存在且相关的比例 | ≥ 98% |
| **判例相关性** | 检索到的判例与争议焦点相关的比例 | ≥ 80% |
| **修改建议可用率** | 律师评审认为"可直接使用或略改即用" | ≥ 70% |

### 4.2 定性评测

每 50 份测试样本，抽取 5 份由法务顾问深度评审：

| 维度 | 评分（1-5） | 目标 |
|---|---|---|
| 法律分析深度 | 是否只停留在表面 | ≥ 4.0 |
| 逻辑自洽性 | 分析过程和结论是否一致 | ≥ 4.5 |
| 商业实用度 | 给出的修改建议是否可落地 | ≥ 3.5 |

---

## 五、幻觉评测专项

### 5.1 幻觉分类

| 类型 | 定义 | 示例 |
|---|---|---|
| **A类：法条虚构** | 引用不存在的法条编号 | "《民法典》第999条"（民法典到1260条，但999条可能是虚构的） |
| **B类：原文篡改** | 修改了合同原文的措辞 | 合同写"可以"→AI写成"应当" |
| **C类：过度解读** | 从条款中推理出不存在的内容 | 合同没提"知识产权"，AI说"知识产权归属有问题" |
| **D类：确认偏差** | 受到上下文误导的误判 | 前一条是高风险→后一条也倾向于判高风险 |

### 5.2 评测方法

```python
# 对每条 Analyzer 输出进行幻觉检查
def hallucination_check(analysis, clause_text, law_db):
    checks = []
    
    # A类检测：法条编号是否在数据库中
    for law_ref in analysis["law_references"]:
        if not law_db.exists(law_ref["law"], law_ref["article"]):
            checks.append({"type": "A", "detail": f"法条{law_ref['article']}不存在"})
    
    # B类检测：原文引用与合同原文的相似度
    if analysis.get("original_quote"):
        similarity = semantic_similarity(analysis["original_quote"], clause_text)
        if similarity < 0.90:
            checks.append({"type": "B", "detail": f"原文相似度仅{similarity:.2f}"})
    
    return checks
```

### 5.3 目标

| 幻觉类型 | 可接受率 |
|---|---|
| A类（法条虚构） | **0%** — 零容忍 |
| B类（原文篡改） | < 1% |
| C类（过度解读） | < 5% |
| D类（确认偏差） | < 3% |

---

## 六、端到端评测

| 指标 | 定义 | 目标值 |
|---|---|---|
| 整体 F1 Score | 2 × Precision × Recall / (Precision + Recall) | ≥ 0.88 |
| 高危检出率 | 律师标注高危条款中AI也标为高危的比例 | ≥ 95% |
| 误报率 | AI标为高危但律师标为低危的比例 | < 10% |
| 平均审查耗时 | 从上传到报告返回的时间 | < 15 分钟 |
| 报告结构完整率 | 六大部分一个不少的合同占比 | 100% |

---

## 七、自动化检测落地方案

### 7.1 CI 门禁流程

```
PR Push 或 Prompt 变更
      │
      ▼
┌─────────────────────┐
│ 1. 规则引擎检测（<5s）│  ← 零 Token 消耗
│    法条编号正则 + DB比对 │
└────────┬────────────┘
         │
    ┌────▼────┐
    │ 任何失败？│──→ ❌ 直接拒绝合并
    └────┬────┘
         │ 通过
         ▼
┌─────────────────────┐
│ 2. 测试集验证（~2min）│  ← 需要 LLM 调用
│    50条标注用例跑一遍  │
└────────┬────────────┘
         │
    ┌────▼──────────┐
    │ Type A > 0% ? │──→ ❌ 拒绝
    │ Type B > 1% ? │──→ ❌ 拒绝
    │ F1 < 0.85 ?   │──→ ⚠️ 警告但允许通过
    └───────────────┘
```

### 7.2 规则引擎实现（Type A 零 Token 检测）

```python
# backend/tests/hallucination_rules.py
import re
from db import law_db

def check_type_a_fake_statute(analysis: dict) -> list[dict]:
    """规则引擎：检测虚假法条引用（零 LLM Token 消耗）"""
    violations = []
    
    for ref in analysis.get("law_references", []):
        # 规则 1: 格式校验
        if not re.match(r'^[\u4e00-\u9fff]+条$|^Art(icle)?\.?\s*\d+', ref.get("article", "")):
            violations.append({
                "type": "A",
                "subtype": "format_invalid",
                "detail": f"法条编号格式异常: {ref['article']}"
            })
            continue
        
        # 规则 2: 数据库比对
        db_record = law_db.query(
            law_name=ref.get("law", ""),
            article=ref.get("article", "")
        )
        
        if not db_record:
            violations.append({
                "type": "A", 
                "subtype": "not_found",
                "detail": f"{ref['law']} {ref['article']} 在数据库中不存在"
            })
            continue
        
        # 规则 3: 有效日期检查
        if db_record.get("status") == "repealed":
            violations.append({
                "type": "A",
                "subtype": "repealed", 
                "detail": f"{ref['law']} {ref['article']} 已于 {db_record['repealed_date']} 废止"
            })
    
    return violations
```

### 7.3 最小测试集格式

> 不要求 500+200 份完整标注（Phase 2），MVP 阶段先构建 50 条高质量标注用例作为 CI 门禁。

```json
{
  "test_cases": [
    {
      "id": "tc_001",
      "contract_type": "采购合同",
      "clause_text": "逾期交货超过15日，甲方有权解除合同。",
      "ground_truth": {
        "risk_level": "medium",
        "law_references": [
          {"law": "民法典", "article": "第563条", "relevance": "direct"}
        ],
        "no_hallucination": true
      },
      "category": "regular"
    },
    {
      "id": "tc_050",
      "contract_type": "租赁合同",
      "clause_text": "租金按照市场调节价执行。",
      "ground_truth": {
        "risk_level": "low",
        "law_references": [],
        "no_hallucination": true
      },
      "category": "edge_case_no_statute"
    }
  ],
  "negative_cases": [
    {
      "id": "nc_001",
      "purpose": "验证 Type A 检测——故意注入虚假法条",
      "malformed_output": {
        "law_references": [
          {"law": "民法典", "article": "第9999条"}
        ]
      },
      "expected_detection": {"type": "A", "subtype": "not_found"}
    }
  ]
}
```

### 7.4 回归测试触发条件

| 触发事件 | 跑哪些测试 | 阻塞合并？ |
|---|---|---|
| Prompt 微调（analyzer_system_prompt 变更） | 50 条测试集 | ✅ 是 |
| LLM 模型切换（mimo2.5 → deepseek-v4-flash） | 50 条测试集 | ✅ 是 |
| 代码级重构（无逻辑变更） | 规则引擎 5s 检测 | ✅ 是 |
| Prompt 完全重写 | 50 条测试集 + 人工抽查 10 条 | ✅ 是 |
| 新合同类型加入 | 扩充测试集 + 全量回归 | ⚠️ 允许通过但需记录 |

### 7.5 CI 配置文件

```yaml
# .github/workflows/agent-hallucination-check.yml
name: Agent Hallucination Gate

on:
  pull_request:
    paths:
      - 'backend/app/agents/**'
      - 'backend/app/prompts/**'
  push:
    branches: [master, main]

jobs:
  rule_check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run hallucination rule engine
        run: python backend/tests/hallucination_rules.py --ci-mode
      - name: Assert zero Type A violations
        run: |
          violations=$(cat test_output.json | jq '.type_a_count')
          if [ "$violations" != "0" ]; then
            echo "❌ Type A hallucination detected: $violations"
            exit 1
          fi
        # Type A 零容忍，直接阻断
  
  regression_test:
    needs: rule_check
    runs-on: ubuntu-latest
    steps:
      - name: Run 50-case regression suite
        run: python backend/tests/regression_suite.py --dataset=minimal_50.json
      - name: Validate metrics
        run: python backend/tests/validate_metrics.py --min-f1=0.85
```

## 七、持续评测机制

```
每次模型更新 / Prompt 变更：
  
  1. 运行 200 份固定测试集
  2. 自动生成评测报告（Precision/Recall/F1）
  3. 与上一版本对比（Degradation Check）
     ├── 若指标下降 > 2% → 阻塞发布，人工排查
     └── 若指标上升/持平 → 自动通过
  4. 每周抽取 20 份实时用户数据（脱敏）补充评测
  5. 每月由法务顾问抽查 10 份，输出定性评审意见
```
