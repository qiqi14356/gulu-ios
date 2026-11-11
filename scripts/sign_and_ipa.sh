#!/usr/bin/env bash
# 用自备证书给未签名 .app 重签，产出可装 .ipa（TrollStore / AltStore / 个人开发者证书通用）
#
# 前置：
#   1) 导出 p12 + .mobileprovision（开发者账号或企业证书）
#   2) keychain 已导入 p12（security import ... -k ~/Library/Keychains/login.keychain-db）
# 用法：
#   IDENTITY="Apple Distribution: XXXX (TEAMID)" \
#   PROVISION="$PWD/cert/profile.mobileprovision" \
#   BUNDLE_ID="com.gulugulu.gulu" \
#   ./scripts/sign_and_ipa.sh build/ios/iphoneos/Runner.app build/ios/ipa/gulu-signed.ipa
set -euo pipefail

APP="${1:-build/ios/iphoneos/Runner.app}"
OUT="${2:-build/ios/ipa/gulu-signed.ipa}"
IDENTITY="${IDENTITY:?需要 IDENTITY，例如 \"Apple Distribution: XXXX (TEAMID)\"}"
PROVISION="${PROVISION:?需要 PROVISION 指向 .mobileprovision}"
BUNDLE_ID="${BUNDLE_ID:-com.gulugulu.gulu}"

[ -d "$APP" ] || { echo "找不到 $APP"; exit 1; }
ENT="$(mktemp -t ent).plist"
security cms -D -i "$PROVISION" > /tmp/_prov.plist
/usr/libexec/PlistBuddy -x -c 'Print :Entitlements' /tmp/_prov.plist > "$ENT"

# 1) 嵌入式描述文件
cp "$PROVISION" "$APP/embedded.mobileprovision"

# 2) 清旧签名
rm -rf "$APP/_CodeSignature"
find "$APP" -name "*.dylib" -o -name "*.so" | while read -r f; do
  codesign --force --sign "$IDENTITY" --timestamp=none "$f" 2>/dev/null || true
done

# 3) 签主包（entitlements 必须和描述文件一致，否则装不上）
codesign --force --sign "$IDENTITY" \
  --entitlements "$ENT" \
  --timestamp=none \
  --generate-entitlement-der \
  "$APP"

codesign --verify --deep --strict --verbose=2 "$APP"

# 4) 打 ipa
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/Payload"
cp -R "$APP" "$STAGE/Payload/"
mkdir -p "$(dirname "$OUT")"
( cd "$STAGE" && zip -qry "$OLDPWD/$OUT" Payload )
echo "OK: $OUT"
