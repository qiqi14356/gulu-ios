#!/usr/bin/env python3
"""轻量 Dart 源码预检（本机没有 Dart SDK 时的最低保障）。

不做完整语义分析，只拦三类会让 `flutter build` 直接失败的低级错误：
  1. 圆括号/花括号/方括号不配对
  2. 把 `get` / `set` / `operator` 等内置标识符当成方法名
  3. import 了 pubspec 里没声明的包

真正的编译在 GitHub runner 上做，这里只是把明显的坑提前打掉。
用法: python scripts/lint_dart.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"

PAIRS = {"(": ")", "[": "]", "{": "}"}
CLOSERS = {v: k for k, v in PAIRS.items()}

# Dart 的 built-in identifier 不能当普通方法名用
BANNED_METHOD_NAMES = {"get", "set", "operator", "external", "abstract"}


def strip_noise(src: str) -> str:
    """去掉注释和字符串字面量，避免把里面的括号算进去。"""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        # 行注释
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        # 块注释（Dart 支持嵌套）
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            depth = 1
            i += 2
            while i < n and depth:
                if src.startswith("/*", i):
                    depth += 1
                    i += 2
                elif src.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        # 三种字符串：' " 三引号
        if c in "'\"":
            quote = c * 3 if src.startswith(c * 3, i) else c
            i += len(quote)
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src.startswith(quote, i):
                    i += len(quote)
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_balance(path: Path, src: str) -> list[str]:
    errs = []
    stack = []
    for lineno, line in enumerate(src.split("\n"), 1):
        for ch in line:
            if ch in PAIRS:
                stack.append((ch, lineno))
            elif ch in CLOSERS:
                if not stack:
                    errs.append(f"{path.name}:{lineno} 多余的 '{ch}'")
                elif stack[-1][0] != CLOSERS[ch]:
                    opener, oline = stack.pop()
                    errs.append(
                        f"{path.name}:{lineno} '{ch}' 与第 {oline} 行的 '{opener}' 不匹配"
                    )
                else:
                    stack.pop()
    for opener, oline in stack:
        errs.append(f"{path.name}:{oline} '{opener}' 未闭合")
    return errs


def check_method_names(path: Path, src: str) -> list[str]:
    errs = []
    for m in re.finditer(r"\bFuture<[^>]*>\s*(\w+)\s*\(|\b(?:void|int|String|Widget|bool)\s+(\w+)\s*\(", src):
        name = m.group(1) or m.group(2)
        if name in BANNED_METHOD_NAMES:
            errs.append(f"{path.name} 方法名用了保留字 '{name}'")
    return errs


def declared_packages() -> set[str]:
    pubspec = (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    pkgs = set()
    in_deps = False
    for raw in pubspec.split("\n"):
        if re.match(r"^(dependencies|dev_dependencies):", raw):
            in_deps = True
            continue
        if raw and not raw.startswith(" ") and raw.strip():
            in_deps = False
        if in_deps:
            m = re.match(r"^  ([a-z_][a-z0-9_]*):", raw)
            if m:
                pkgs.add(m.group(1))
    return pkgs | {"flutter", "dart"}


def check_imports(path: Path, src: str, pkgs: set[str]) -> list[str]:
    errs = []
    for m in re.finditer(r"^\s*import\s+['\"]package:([a-z_0-9]+)/", src, re.M):
        pkg = m.group(1)
        if pkg not in pkgs:
            errs.append(f"{path.name} import 了未声明的包 '{pkg}'")
    return errs


def main() -> int:
    if not LIB.exists():
        print(f"找不到 {LIB}", file=sys.stderr)
        return 1

    pkgs = declared_packages()
    print(f"pubspec 声明的包: {', '.join(sorted(pkgs))}\n")

    all_errs: list[str] = []
    files = sorted(LIB.rglob("*.dart"))
    for f in files:
        raw = f.read_text(encoding="utf-8")
        clean = strip_noise(raw)
        all_errs += check_balance(f, clean)
        all_errs += check_method_names(f, raw)
        all_errs += check_imports(f, raw, pkgs)
        print(f"  {f.relative_to(ROOT)}  {len(raw.splitlines())} 行")

    print()
    if all_errs:
        print("发现问题:")
        for e in all_errs:
            print("  -", e)
        return 1

    print(f"预检通过（{len(files)} 个文件，括号配对 / 保留字 / 依赖声明）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
