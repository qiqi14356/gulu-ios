#!/usr/bin/env bash
# 只生成 ios/ 容器，绝不碰已有的 lib/ 与 pubspec.yaml。
#
# 做法：在临时目录里 flutter create --platforms=ios，然后把 ios/ 拷回来，
# 用 Python 修正 bundle id（不用 sed，避免 macOS/GNU 差异与过度替换），
# 最后把预生成的 AppIcon 塞进去。
set -euo pipefail

ORG="${ORG:-com.gulugulu}"
NAME="${NAME:-gulu}"
BUNDLE_ID="${ORG}.${NAME}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

command -v flutter >/dev/null 2>&1 || { echo "ERROR: flutter 不在 PATH"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> flutter create --platforms=ios"
(
  cd "$TMP"
  flutter create \
    --platforms=ios \
    --org "$ORG" \
    --project-name "$NAME" \
    --no-pub \
    "$NAME" >/dev/null
)

[ -d "$TMP/$NAME/ios" ] || { echo "ERROR: flutter create 没有产出 ios/"; exit 1; }

echo "==> 拷贝 ios/ 到 $ROOT/ios"
rm -rf "$ROOT/ios"
cp -a "$TMP/$NAME/ios" "$ROOT/ios"

echo "==> 设置 bundle id = $BUNDLE_ID"
python3 "$ROOT/scripts/patch_pbxproj.py" \
  "$ROOT/ios/Runner.xcodeproj/project.pbxproj" \
  "$BUNDLE_ID"

if [ -d "$ROOT/ios_assets/AppIcon.appiconset" ]; then
  echo "==> 覆盖 AppIcon"
  rm -rf "$ROOT/ios/Runner/Assets.xcassets/AppIcon.appiconset"
  cp -a "$ROOT/ios_assets/AppIcon.appiconset" "$ROOT/ios/Runner/Assets.xcassets/"
fi

cd "$ROOT"
flutter pub get

echo "==> 完成：ios/ ready (bundle id: $BUNDLE_ID)"
echo "    下一步: flutter build ios --release --no-codesign"
