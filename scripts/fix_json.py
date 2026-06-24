"""修复 batch-01 中非法 JSON 文件的未转义双引号问题。"""

import json
import sys
import os


def fix_unescaped_quotes(filepath):
    """尝试修复 JSON 字符串值内的未转义双引号。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 先试一下是否已经合法
    try:
        json.loads(content)
        print(f"  Already valid: {filepath}")
        return True
    except json.JSONDecodeError:
        pass

    # 逐行处理：找到 description/suggestion/legal_basis 等值中的未转义双引号
    # 策略：把 \u201c \u201d (中文左右双引号) 替换成单引号或书名号
    # 同时处理裸露的 ASCII 双引号
    fixed = content
    # 替换中文左右双引号为「」
    fixed = fixed.replace("\u201c", "「").replace("\u201d", "」")
    # 替换全角双引号
    fixed = fixed.replace("\uff02", "「")

    try:
        data = json.loads(fixed)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Fixed (quote replacement): {filepath}")
        return True
    except json.JSONDecodeError:
        pass

    # 更激进的修复：用状态机逐字符扫描
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(content):
        ch = content[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == "\\":
            result.append(ch)
            escape_next = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                in_string = True
                result.append(ch)
            else:
                # 判断这个引号是字符串结束还是内部引号
                # 向后看：跳过空白后应该是 : , } ] 才是合法结束
                j = i + 1
                while j < len(content) and content[j] in " \t\r\n":
                    j += 1
                if j < len(content) and content[j] in ":,}]":
                    # 这是字符串结束
                    in_string = False
                    result.append(ch)
                else:
                    # 这是内部未转义引号，转义它
                    result.append('\\"')
        else:
            result.append(ch)
        i += 1

    fixed = "".join(result)
    try:
        data = json.loads(fixed)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Fixed (state machine): {filepath}")
        return True
    except json.JSONDecodeError as e:
        print(f"  FAILED: {filepath} -> {e}")
        return False


if __name__ == "__main__":
    base = "D:/FaLvXM/07-testing/generated/batch-01"
    files = [
        os.path.join(base, "contract-001-procurement-equipment", "expected_risks.json"),
        os.path.join(base, "contract-004-procurement-it", "expected_risks.json"),
        os.path.join(base, "contract-004-procurement-it", "expected_contradictions.json"),
    ]
    ok = 0
    for f in files:
        if fix_unescaped_quotes(f):
            ok += 1
    print(f"\n修复结果: {ok}/{len(files)}")
