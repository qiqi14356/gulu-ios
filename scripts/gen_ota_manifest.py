#!/usr/bin/env python3
"""生成 OTA 安装用的 manifest.plist + install.html。

iOS 的无线安装（itms-services）必须满足：
  - manifest.plist 和 .ipa 都在 HTTPS 上
  - 证书必须是受信任 CA 签的（自签证书 iOS 会拒绝）
  - .ipa 里的 .app 必须已用符合描述文件的证书签名

用法:
  python scripts/gen_ota_manifest.py \
      --ipa https://example.com/gulu.ipa \
      --bundle-id com.gulugulu.gulu \
      --version 2.2.5 \
      --title "咕噜咕噜" \
      --icon https://example.com/icon-57.png \
      --out dist

产出: dist/manifest.plist, dist/install.html
"""
import argparse
import plistlib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--ipa", required=True)
p.add_argument("--bundle-id", required=True)
p.add_argument("--version", default="1.0.0")
p.add_argument("--title", default="咕噜咕噜")
p.add_argument("--icon", default="")
p.add_argument("--out", default="dist")
a = p.parse_args()

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)

manifest = {
    "items": [
        {
            "assets": [
                {"kind": "software-package", "url": a.ipa},
                *([{"kind": "display-image", "url": a.icon},
                   {"kind": "full-size-image", "url": a.icon}] if a.icon else []),
            ],
            "metadata": {
                "bundle-identifier": a.bundle_id,
                "bundle-version": a.version,
                "kind": "software",
                "title": a.title,
            },
        }
    ]
}

with (out / "manifest.plist").open("wb") as f:
    plistlib.dump(manifest, f)

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>安装 {a.title}</title>
<style>
  body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#0e0e12;color:#eee;
       display:flex;flex-direction:column;align-items:center;justify-content:center;
       min-height:100vh;margin:0;padding:24px;text-align:center}}
  .card{{background:#1b1b22;border-radius:18px;padding:28px 22px;max-width:360px;width:100%}}
  h1{{font-size:20px;margin:0 0 6px}}
  p{{color:#9aa; font-size:13px; line-height:1.7; margin:8px 0}}
  a.btn{{display:block;margin-top:20px;background:#7c4dff;color:#fff;text-decoration:none;
        padding:14px;border-radius:12px;font-weight:600}}
  code{{background:#000;padding:2px 6px;border-radius:4px;font-size:12px;color:#7c4dff}}
  a.alt{{display:block;margin-top:10px;color:#7c4dff;font-size:13px;text-decoration:none}}
  .warn{{background:#2a1f10;border:1px solid #6b4a12;border-radius:10px;padding:10px 12px;
        font-size:12px;color:#e0b060;margin-top:16px;text-align:left;line-height:1.6}}
</style>
</head>
<body>
<div class="card">
  <h1>{a.title}</h1>
  <p>版本 {a.version} · {a.bundle_id}</p>
  <a class="btn" href="itms-services://?action=download-manifest&url={a.ipa.rsplit('/',1)[0]}/manifest.plist">
    点击安装
  </a>
  <a class="alt" href="{a.ipa}">或者直接下载 ipa 文件（用 Sideloadly 重签）</a>
  <div class="warn">
    未签名的 ipa 走上面那个按钮一定会失败 —— iOS 只安装带有效签名的包。
    先用 Sideloadly / AltStore / TrollStore 重签，再回到这里安装。
  </div>
  <p style="margin-top:18px">若提示「无法安装」，请检查：<br>
     1. 用 <b>Safari</b> 打开本页（微信/QQ 内置浏览器不支持）<br>
     2. 描述文件里的 UDID 已包含这台设备<br>
     3. 安装后在 <code>设置 → 通用 → VPN与设备管理</code> 里信任证书</p>
</div>
</body>
</html>
"""
(out / "install.html").write_text(html, encoding="utf-8")
print(f"OK: {out/'manifest.plist'}")
print(f"OK: {out/'install.html'}")
