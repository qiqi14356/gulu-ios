#!/usr/bin/env python3
"""CI 之前的本地体检：把 Windows 上能验的全验一遍。

跑 `python scripts/preflight.py`，全绿再去推 GitHub。
这样就把「推上去跑 10 分钟才发现少个文件」的成本压成 2 秒。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def add(level: str, name: str, detail: str = "") -> None:
    results.append((level, name, detail))


def check_required_files() -> None:
    files = [
        "pubspec.yaml",
        "analysis_options.yaml",
        ".gitattributes",
        ".gitignore",
        "lib/main.dart",
        "lib/config.dart",
        "lib/api.dart",
        "lib/pages/home_page.dart",
        "lib/pages/probe_page.dart",
        "lib/local_hls.dart",
        "lib/pages/player_page.dart",
        "assets/demo/ep02.json",
        "assets/demo/ep05.json",
        "assets/demo/ep06.json",
        "scripts/mk_demo_asset.py",
        "scripts/gen_ios_container.sh",
        "scripts/package_ipa.sh",
        "scripts/patch_pbxproj.py",
        "scripts/patch_info_plist.py",
        "scripts/make_appicon.py",
        "scripts/gh_build_ios.py",
        ".github/workflows/ios-unsigned.yml",
        "ios_assets/icon_src_1024.png",
        "ios_assets/AppIcon.appiconset/Contents.json",
    ]
    missing = [f for f in files if not (ROOT / f).exists()]
    add(FAIL if missing else OK, "必需文件", f"缺 {missing}" if missing else f"{len(files)} 个齐备")


def check_appicon() -> None:
    d = ROOT / "ios_assets" / "AppIcon.appiconset"
    try:
        spec = json.loads((d / "Contents.json").read_text(encoding="utf-8"))
    except Exception as e:
        add(FAIL, "AppIcon Contents.json", str(e))
        return
    imgs = spec.get("images", [])
    missing = [i["filename"] for i in imgs if not (d / i["filename"]).exists()]
    has_1024 = any(i.get("size") == "1024x1024" for i in imgs)
    bad = []
    if missing:
        bad.append(f"缺图 {missing}")
    if not has_1024:
        bad.append("缺 1024 marketing 图标")
    if len(imgs) != 15:
        bad.append(f"条目数 {len(imgs)}（应为 15）")
    add(FAIL if bad else OK, "AppIcon 完整性", "; ".join(bad) or f"{len(imgs)} 张图全在")

    # iOS 禁止 alpha
    try:
        from PIL import Image

        alpha = [
            i["filename"]
            for i in imgs
            if (d / i["filename"]).exists()
            and Image.open(d / i["filename"]).mode not in ("RGB", "L")
        ]
        add(FAIL if alpha else OK, "AppIcon 无 alpha", f"有 alpha: {alpha}" if alpha else "全部 RGB")
    except ImportError:
        add(WARN, "AppIcon 无 alpha", "本机没装 Pillow，跳过")


def check_pubspec() -> None:
    txt = (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    pkg = re.search(r"^name:\s*(\S+)", txt, re.M)
    ver = re.search(r"^version:\s*(\S+)", txt, re.M)
    add(OK if pkg and ver else FAIL, "pubspec", f"name={pkg.group(1) if pkg else '?'} version={ver.group(1) if ver else '?'}")

    # 源码里 import 的包必须在 pubspec 里
    deps = set(re.findall(r"^  ([a-z_][a-z0-9_]*):", txt, re.M))
    used = set()
    for f in (ROOT / "lib").rglob("*.dart"):
        used |= set(re.findall(r"package:([a-z_0-9]+)/", f.read_text(encoding="utf-8")))
    undeclared = used - deps - {"flutter"}
    add(FAIL if undeclared else OK, "依赖声明", f"未声明: {undeclared}" if undeclared else f"用到 {sorted(used)}")


def check_workflow() -> None:
    try:
        import yaml
    except ImportError:
        add(WARN, "workflow YAML", "本机没装 PyYAML，跳过")
        return
    p = ROOT / ".github" / "workflows" / "ios-unsigned.yml"
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        add(FAIL, "workflow YAML", str(e))
        return
    job = d["jobs"]["build"]
    steps = job["steps"]
    names = [s.get("name") or s.get("uses") for s in steps]
    problems = []
    if not any("macos" in str(job.get("runs-on", "")) for _ in [1]):
        problems.append("不是 macOS runner")
    if not any("upload-artifact" in str(n) for n in names):
        problems.append("没有 upload-artifact")
    if not any("--no-codesign" in str(s.get("run", "")) for s in steps):
        problems.append("build 步骤没有 --no-codesign")
    add(FAIL if problems else OK, "workflow 结构",
        "; ".join(problems) or f"{len(steps)} 步, runner={job['runs-on']}")


def check_shell_scripts() -> None:
    bad = []
    for f in (ROOT / "scripts").glob("*.sh"):
        r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            bad.append(f"{f.name}: {r.stderr.strip()[:80]}")
    add(FAIL if bad else OK, "shell 语法", "; ".join(bad) or f"{len(list((ROOT/'scripts').glob('*.sh')))} 个脚本")


def check_python_scripts() -> None:
    bad = []
    for f in (ROOT / "scripts").glob("*.py"):
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)], capture_output=True, text=True
        )
        if r.returncode != 0:
            bad.append(f"{f.name}: {r.stderr.strip()[:80]}")
    add(FAIL if bad else OK, "python 语法", "; ".join(bad) or f"{len(list((ROOT/'scripts').glob('*.py')))} 个脚本")


def check_gitignore() -> None:
    txt = (ROOT / ".gitignore").read_text(encoding="utf-8")
    must = ["ios/", ".dart_tool/", "build/", ".gh_token"]
    missing = [m for m in must if m not in txt]
    add(FAIL if missing else OK, ".gitignore 覆盖", f"缺 {missing}" if missing else "关键项都在")


def check_gitattributes() -> None:
    txt = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    if "*.sh" in txt and "eol=lf" in txt:
        add(OK, ".gitattributes", "sh 强制 LF")
    else:
        add(FAIL, ".gitattributes", "没给 .sh 指定 eol=lf → macOS 上会报 $\\r 错误")


def check_dart_analyze() -> None:
    dart = None
    for cand in [
        ROOT.parent / "tools" / "flutter" / "bin" / "cache" / "dart-sdk" / "bin" / "dart.exe",
        ROOT.parent / "tools" / "flutter" / "bin" / "cache" / "dart-sdk" / "bin" / "dart",
    ]:
        if cand.exists():
            dart = cand
            break
    if dart is None:
        which = subprocess.run(["bash", "-lc", "command -v dart"], capture_output=True, text=True)
        if which.returncode == 0 and which.stdout.strip():
            dart = Path(which.stdout.strip())
    if dart is None:
        add(WARN, "dart analyze", "没找到 Dart SDK，跳过（CI 上会跑）")
        return
    r = subprocess.run(
        [str(dart), "analyze", "lib"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    out = (r.stdout or "") + (r.stderr or "")
    if "No issues found" in out:
        add(OK, "dart analyze", "零问题")
    elif r.returncode == 0:
        add(OK, "dart analyze", out.strip().splitlines()[-1][:100])
    else:
        add(FAIL, "dart analyze", out.strip()[:200].replace("\n", " | "))


def check_ipa_packaging() -> None:
    """造一个假 Runner.app，真跑一遍 package_ipa.sh。"""
    vdir = ROOT / ".verify" / "preflight"
    app = vdir / "Runner.app"
    import shutil

    shutil.rmtree(vdir, ignore_errors=True)
    (app / "Frameworks" / "App.framework").mkdir(parents=True)
    (app / "Frameworks" / "Flutter.framework").mkdir(parents=True)
    (app / "Runner").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (app / "Info.plist").write_text("<plist/>", encoding="utf-8")
    (app / "Frameworks" / "App.framework" / "App").write_bytes(b"DART_AOT")
    (app / "Frameworks" / "Flutter.framework" / "Flutter").write_bytes(b"FLUTTER")

    out = vdir / "test.ipa"
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "package_ipa.sh"), str(app), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        add(FAIL, "ipa 打包自测", ((r.stdout or "") + (r.stderr or "")).strip()[:200])
        return

    import stat
    import zipfile

    with zipfile.ZipFile(out) as z:
        info = z.getinfo("Payload/Runner.app/Runner")
        mode = (info.external_attr >> 16) & 0o777
    if not mode & 0o111:
        add(FAIL, "ipa 可执行位", f"Runner 权限 {mode:04o}，缺 +x，装上会闪退")
    else:
        add(OK, "ipa 打包自测", f"结构正确，Runner 权限 {mode:04o}")
    del stat
    shutil.rmtree(vdir, ignore_errors=True)


def check_plist_patch() -> None:
    """用真实 Flutter 模板验证 Info.plist 补丁。"""
    tpl = ROOT.parent / "tools" / "flutter" / "packages" / "flutter_tools" / "templates" / \
        "app_shared" / "ios.tmpl" / "Runner" / "Info.plist.tmpl"
    if not tpl.exists():
        add(WARN, "Info.plist 补丁", "没找到 Flutter 模板，跳过")
        return
    vdir = ROOT / ".verify"
    vdir.mkdir(exist_ok=True)
    tmp = vdir / "preflight_Info.plist"
    txt = tpl.read_text(encoding="utf-8")
    txt = txt.replace("{{titleCaseProjectName}}", "Gulu").replace("{{projectName}}", "gulu")
    tmp.write_text(txt, encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "patch_info_plist.py"), str(tmp)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode != 0:
        add(FAIL, "Info.plist 补丁", (r.stderr or r.stdout).strip()[:200])
        return

    import plistlib

    pl = plistlib.loads(tmp.read_bytes())
    need = [
        "CFBundleDisplayName", "UIBackgroundModes", "ITSAppUsesNonExemptEncryption",
        "NSAppTransportSecurity", "NSCameraUsageDescription",
    ]
    missing = [k for k in need if k not in pl]
    broken = [k for k in ("CFBundleExecutable", "CFBundleIdentifier", "UILaunchStoryboardName") if k not in pl]
    if missing:
        add(FAIL, "Info.plist 补丁", f"没写上 {missing}")
    elif broken:
        add(FAIL, "Info.plist 补丁", f"破坏了原有键 {broken}")
    else:
        add(OK, "Info.plist 补丁", f"{len(pl)} 个键，中文名={pl['CFBundleDisplayName']}")
    tmp.unlink(missing_ok=True)


def check_bundle_id_patch() -> None:
    vdir = ROOT / ".verify"
    vdir.mkdir(exist_ok=True)
    tmp = vdir / "preflight_pbxproj"
    tmp.write_text(
        "PRODUCT_BUNDLE_IDENTIFIER = com.gulugulu.gulu;\n"
        "PRODUCT_BUNDLE_IDENTIFIER = com.gulugulu.gulu.RunnerTests;\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "patch_pbxproj.py"), str(tmp), "com.hehefankuai.ios"],
        capture_output=True, text=True, encoding="utf-8",
    )
    got = tmp.read_text(encoding="utf-8") if tmp.exists() else ""
    ok = (
        "com.hehefankuai.ios;" in got
        and "com.hehefankuai.ios.RunnerTests;" in got
    )
    add(OK if ok else FAIL, "bundle id 替换",
        "主 target 与 RunnerTests 都正确" if ok else f"结果不对:\n{got}")
    tmp.unlink(missing_ok=True)


def check_demo_assets() -> None:
    """播放源清单的结构与真实性：段数/时长/前缀/tails 一致，且能拼出可分片的 URL。"""
    d = ROOT / "assets" / "demo"
    files = sorted(d.glob("*.json"))
    if not files:
        add(FAIL, "播放清单", "assets/demo 里没有 json")
        return
    problems: list[str] = []
    total = 0.0
    for f in files:
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"{f.name}: 解析失败 {e}")
            continue
        tails = j.get("tails") or []
        durs = j.get("durs") or []
        prefix = j.get("prefix") or ""
        if not tails or not prefix:
            problems.append(f"{f.name}: 缺 tails/prefix")
            continue
        if len(tails) != len(durs):
            problems.append(f"{f.name}: tails={len(tails)} durs={len(durs)}")
            continue
        # durs 必须是毫秒量级；如果最大值 < 100 说明已经被当成秒存进去了
        mx = max(durs)
        if mx < 100:
            problems.append(f"{f.name}: durs 像秒不像毫秒（max={mx}）")
        total += sum(durs) / 1000.0
        if not (prefix + tails[0]).startswith("https://"):
            problems.append(f"{f.name}: 拼出来的 URL 不是 https")
    add(FAIL if problems else OK, "播放清单",
        "; ".join(problems) if problems else
        f"{len(files)} 集，共 {total/60:.0f} 分钟，段数/时长/前缀一致")


def main() -> int:
    print(f"工程根目录: {ROOT}\n")
    checks = [
        check_required_files, check_appicon, check_pubspec, check_workflow,
        check_shell_scripts, check_python_scripts, check_gitignore,
        check_gitattributes, check_bundle_id_patch, check_plist_patch,
        check_ipa_packaging, check_dart_analyze, check_demo_assets,
    ]
    for c in checks:
        try:
            c()
        except Exception as e:
            add(FAIL, c.__name__, f"{type(e).__name__}: {e}")

    width = max(len(n) for _, n, _ in results)
    for level, name, detail in results:
        mark = {"PASS": "✓", "FAIL": "✗", "WARN": "!"}[level]
        print(f"  {mark} {name.ljust(width)}  {detail}")

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    print()
    if fails:
        print(f"✗ {len(fails)} 项失败 —— 修完再推 GitHub")
        return 1
    print(f"✓ 全部通过（{len(results) - len(warns)} 项，{len(warns)} 项跳过）")
    print("  下一步: python scripts/gh_build_ios.py --repo gulu-ios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
