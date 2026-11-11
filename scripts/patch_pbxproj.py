#!/usr/bin/env python3
"""把 Xcode 工程里 Runner 主 target 的 bundle id 改成指定值。

为什么不用 sed：
  - macOS 的 `sed -i.bak` 和 GNU sed 行为有差异，MSYS 下还会撞跨设备 rename 错误
  - 需要精确锚定完整值，否则 `com.x.y` 的替换会把 `com.x.y.RunnerTests` 一起吞掉，
    造成两个 target 同 id，Xcode 直接报错

用法:
  python scripts/patch_pbxproj.py ios/Runner.xcodeproj/project.pbxproj com.gulugulu.gulu
"""
import re
import sys
from pathlib import Path

pbx = Path(sys.argv[1] if len(sys.argv) > 1 else "ios/Runner.xcodeproj/project.pbxproj")
new_id = sys.argv[2] if len(sys.argv) > 2 else "com.gulugulu.gulu"

if not pbx.exists():
    print(f"找不到 {pbx}", file=sys.stderr)
    raise SystemExit(1)

text = pbx.read_text(encoding="utf-8")

# 先把所有 PRODUCT_BUNDLE_IDENTIFIER 值收集出来，看清原本有哪几个
before = re.findall(r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([^;]+);", text)
print("原有 bundle id:", sorted(set(v.strip() for v in before)))

# flutter create 生成的是 com.<org>.<name> 与 com.<org>.<name>.RunnerTests
# 判定规则：值与 new_id 相同、或等于 new_id + ".RunnerTests"，即为目标 target。
# 其余（例如 RunnerTests 后缀）保留后缀、只替换前缀。
def repl(m: re.Match) -> str:
    prefix, value, suffix = m.group(1), m.group(2).strip(), m.group(3)
    if value == new_id or value.endswith(".RunnerTests") or value == new_id + ".RunnerTests":
        # 保留 .RunnerTests 之类的后缀，但去掉重复叠加
        tail = value[len(value) - len(".RunnerTests"):] if value.endswith(".RunnerTests") else ""
        return f"{prefix}{new_id}{tail};"
    return m.group(0)


# 先算出旧前缀：取出现次数最多、且不以 .RunnerTests 结尾的那个值
candidates = [v.strip() for v in before if not v.strip().endswith(".RunnerTests")]
old_id = candidates[0] if candidates else None
if old_id and old_id != new_id:
    text = re.sub(
        rf"(PRODUCT_BUNDLE_IDENTIFIER\s*=\s*){re.escape(old_id)}(\.RunnerTests)?;",
        lambda m: f"{m.group(1)}{new_id}{m.group(2) or ''};",
        text,
    )

pbx.write_text(text, encoding="utf-8")

after = re.findall(r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([^;]+);", text)
print("改后 bundle id:", sorted(set(v.strip() for v in after)))

dupes = [v for v in set(v.strip() for v in after)]
if len(dupes) < len(set(v.strip() for v in after)):
    print("警告: 出现重复 bundle id", file=sys.stderr)
