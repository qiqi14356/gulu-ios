#!/usr/bin/env bash
# 把 flutter build ios --no-codesign 产出的 .app 打成未签名 .ipa
# 未签名 ipa 不能直接装，需要 Sideloadly / AltStore / TrollStore 用证书重签。
set -euo pipefail

APP_PATH="${1:-build/ios/iphoneos/Runner.app}"
OUT="${2:-build/ios/ipa/gulu-unsigned.ipa}"

[ -d "$APP_PATH" ] || { echo "找不到 $APP_PATH"; exit 1; }
mkdir -p "$(dirname "$OUT")"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/Payload"
cp -R "$APP_PATH" "$STAGE/Payload/"

# 清掉可能残留的签名，避免重签时报 bundle 已签名冲突
rm -rf "$STAGE/Payload/Runner.app/_CodeSignature" || true
rm -f  "$STAGE/Payload/Runner.app/embedded.mobileprovision" || true

( cd "$STAGE" && zip -qry "$OLDPWD/$OUT" Payload )
echo "OK: $OUT  ($(du -h "$OUT" | cut -f1))"
