# 批跑结果汇总工具

## 用途

扫描 `07-testing/generated/batch-01/` 下各样本目录，读取已有的 `review_run_*.json` 结果文件，生成批次级汇总报告。

## 用法

```bash
python scripts/batch_summarize.py
```

## 输出文件

运行后会在 `07-testing/generated/batch-01/_summary/` 下生成：

| 文件 | 说明 |
|---|---|
| `batch_summary.json` | 结构化汇总数据，适合程序读取 |
| `batch_summary.csv` | 每样本明细表格，适合 Excel 打开 |
| `batch_report.md` | 中文可读报告，回答关键分析问题 |

## 报告内容

`batch_report.md` 回答以下问题：

1. **哪些合同最耗 token** — Top 5 排序
2. **哪些合同耗时最长** — Top 5 排序
3. **哪些合同最容易失败** — 失败样本列表
4. **哪些合同结果漂移最大** — 需要多次运行后才能判断
5. **哪些合同最值得做 3 次复审** — 基于高风险数、矛盾数、token 消耗综合排序
6. **哪些错误最常见** — 错误类型聚合计数

## 容错机制

- 样本目录没有 `review_run_*.json` → 标记为"待运行"，不报错
- `review_run_*.json` 解析失败 → 标记为"JSON 解析失败"
- `review_run_*.json` 中 `success=false` → 标记为"失败"
- `review_run_*.json` 中 `error` 字段非空 → 视为失败/错误
- 脚本可重复执行，每次覆盖生成

## 测试

```bash
python -m pytest scripts/tests/test_batch_summarize.py -v
```

## 依赖

无额外依赖，仅使用 Python 标准库（json、csv、pathlib）。
