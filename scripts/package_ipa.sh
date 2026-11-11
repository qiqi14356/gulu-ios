#!/usr/bin/env bash
# 把 flutter build ios --no-codesign 产出的 .app 打成未签名 .ipa
#
# 未签名 ipa 不能直接装，需要 Sideloadly / AltStore / TrollStore 用证书重签。
#
# 用法: ./scripts/package_ipa.sh [Runner.app 路径] [输出 ipa 路径]
set -euo pipefail

APP_PATH="${1:-build/ios/iphoneos/Runner.app}"
OUT="${2:-build/ios/ipa/gulu-unsigned.ipa}"

[ -d "$APP_PATH" ] || { echo "ERROR: not found: $APP_PATH"; exit 1; }

# macOS runner 上是 python3，Windows 上是 python，两个都接受
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "ERROR: python3/python not in PATH"; exit 1; }

mkdir -p "$(dirname "$OUT")"

"$PY" - "$APP_PATH" "$OUT" <<'PYEOF'
import os
import shutil
import sys
import zipfile
from pathlib import Path

app = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
app_name = app.name          # Runner.app
exe_name = app.stem          # Runner

# 这些必须是可执行文件，否则装上去点开会闪退
def needs_exec(rel: Path) -> bool:
    if str(rel) == exe_name:                     # 主可执行文件
        return True
    # Foo.framework/Foo —— framework 的同名二进制
    parts = rel.parts
    for i, p in enumerate(parts):
        if p.endswith(".framework") and i + 1 == len(parts) - 1:
            return parts[-1] == p[: -len(".framework")]
    # 散落的 dylib
    if rel.suffix == ".dylib":
        return True
    return False

# 打包前清掉残留签名，避免重签时报「bundle 已签名」冲突
for junk in ("_CodeSignature", "embedded.mobileprovision", "SC_Info"):
    p = app / junk
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists():
        p.unlink()

DIR_MODE = 0o755
count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk(app):
        dirs.sort()
        rel = Path(root).relative_to(app)
        if str(rel) != ".":
            info = zipfile.ZipInfo(f"Payload/{app_name}/{rel.as_posix()}/")
            info.external_attr = (0o040000 | DIR_MODE) << 16
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, b"")
        for f in sorted(files):
            src = Path(root) / f
            relf = rel / f
            arc = f"Payload/{app_name}/{relf.as_posix()}"
            info = zipfile.ZipInfo.from_file(src, arc)
            info.compress_type = zipfile.ZIP_DEFLATED
            # 关键：不看源文件在 Windows 上的 st_mode（那里恒为 0666），
            # 按 ipa 规范自己定权限位。
            mode = 0o755 if needs_exec(relf) else 0o644
            info.external_attr = (0o100000 | mode) << 16
            z.writestr(info, src.read_bytes())
            count += 1

print(f"packed: {out}  ({out.stat().st_size:,} B, {count} files)")

# 结构自检：这三个缺一个就装不上
# 注意 App.framework 落在 Frameworks/ 下（xcode_backend 里 embedFlutterFrameworks
# 用 FRAMEWORKS_FOLDER_PATH 做目标目录），不是 app 根目录。
need = [
    f"Payload/{app_name}/{exe_name}",
    f"Payload/{app_name}/Info.plist",
    f"Payload/{app_name}/Frameworks/App.framework/App",
]
with zipfile.ZipFile(out) as z:
    names = set(z.namelist())
    missing = [n for n in need if n not in names]
    if missing:
        print("ERROR: bad ipa structure, missing:")
        for m in missing:
            print("  -", m)
        sys.exit(1)
    # 复查可执行位
    info = z.getinfo(f"Payload/{app_name}/{exe_name}")
    mode = (info.external_attr >> 16) & 0o777
    if not mode & 0o111:
        print(f"ERROR: main executable has no +x (mode {mode:04o})")
        sys.exit(1)
    print(f"structure OK ({len(names)} entries, exe mode {mode:04o})")
PYEOF
