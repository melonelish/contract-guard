# 黄金样例自动评测器

## 用途

对比 `batch-01` 真实审查结果与黄金预期，输出主题级评测报告。

## 用法

```bash
python scripts/batch_evaluate.py
```

## 评测方法

### 主题级评测

不依赖完全一致的自然语言表述，而是：
1. 将期望风险类别（`expected_risks.json` 的 `risk_type`）和检测风险类别（`review_run_01_raw.json` 的 `risk_category`）都归一到规范名
2. 支持同义归并：`回款条件` → `付款条件`，`质保条款` → `质量标准` 等
3. 英文标识符（如 `payment_terms_favor_service_provider`）自动映射到中文类别
4. 从风险标题推断类别（当 `risk_type` 为英文标识符时）

### 评测指标

| 指标 | 说明 |
|---|---|
| topic_recall | 期望风险主题被检出的比例 |
| topic_precision | 检出风险主题中属于期望的比例 |
| high_risk_recall | 高风险主题被检出的比例 |
| contradiction_hit | 是否检出矛盾（期望 > 0 时） |
| missing_clause_hit | 是否检出缺失条款（期望 > 0 时） |
| legal_basis_coverage | 检出风险中有法条依据的比例 |
| overall_score | 综合评分（加权平均） |

### 综合评分权重

- 主题 Recall: 35%
- 高风险 Recall: 25%
- 矛盾命中: 15%
- 缺失条款命中: 10%
- 法条依据覆盖: 15%

## 输出文件

### 每样本目录

| 文件 | 说明 |
|---|---|
| `evaluation_review_run_01.json` | 第 1 次运行的评测结果 |
| `evaluation_review_run_02.json` | 第 2 次运行的评测结果 |
| `evaluation_review_run_03.json` | 第 3 次运行的评测结果 |
| `evaluation_summary.md` | 该样本的评测汇总（中文） |

### 批次级（`_summary/`）

| 文件 | 说明 |
|---|---|
| `evaluation_summary.json` | 结构化评测汇总 |
| `evaluation_summary.csv` | 每样本评测明细（Excel 可打开） |
| `evaluation_report.md` | 中文可读评测报告 |

## 报告回答的问题

1. 哪些合同命中率最高
2. 哪些合同漏报最多
3. 哪些高风险最容易漏掉
4. 哪些风险类别最容易漂移
5. 哪些合同虽然风险数很多，但关键风险没抓住
6. 哪些合同法条依据覆盖最好/最差
7. 哪些样本最适合继续做 3 次复审
8. 当前批次是否具备做 Phase 3 质量基线的条件

## 容错

- 无结果文件 → 标记"跳过"
- 失败样本 → 不参与 Recall/Precision 计算，但计入汇总
- JSON 解析失败 → 多编码尝试（UTF-8 → GBK → Latin-1）
- 脚本可重复执行

## 测试

```bash
python -m pytest scripts/tests/test_batch_evaluate.py -v
```

## 依赖

无额外依赖，仅使用 Python 标准库。
