# P0 高价值样本 — 待创建

当前状态：目录骨架已建、manifest 已登记，样本源文件尚未制作。

创建步骤：
1. 编写一份真实采购合同（.docx），包含不低于 12 页 / 18 条条款
2. 由法务顾问标注 ground truth（风险等级、法条引用）
3. 将标注结果写入 expected_output.json
4. 运行 `python 07-testing/scripts/runner.py --mode mock` 验证通路
