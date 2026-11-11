#!/usr/bin/env python3
"""给 flutter create 生成的 ios/Runner/Info.plist 打补丁：
- 允许 http 明文（业务接口可能是 http 反代）
- 允许 App Transport Security 的任意加载（自行替换为具体域名更稳）
- 后台音频、画中画
- 相册/相机权限文案（image_picker）
- ITSAppUsesNonExemptEncryption=false（避免上传时问加密）
用法: python scripts/patch_info_plist.py ios/Runner/Info.plist
"""
import plistlib
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "ios/Runner/Info.plist")
with path.open("rb") as f:
    pl = plistlib.load(f)

pl["CFBundleDisplayName"] = "咕噜咕噜"
pl["CFBundleName"] = "gulu"
pl["ITSAppUsesNonExemptEncryption"] = False
pl["UIBackgroundModes"] = ["audio", "fetch"]
pl["NSPhotoLibraryUsageDescription"] = "选择图片用于头像与反馈附图"
pl["NSPhotoLibraryAddUsageDescription"] = "保存截图与缓存视频"
pl["NSCameraUsageDescription"] = "拍摄头像与反馈附图"
pl["NSMicrophoneUsageDescription"] = "语音搜索与弹幕语音输入"
pl["NSAppTransportSecurity"] = {
    "NSAllowsArbitraryLoads": True,
    "NSAllowsArbitraryLoadsInWebContent": True,
    "NSAllowsLocalNetworking": True,
}
pl.setdefault("UISupportedInterfaceOrientations", [
    "UIInterfaceOrientationPortrait",
    "UIInterfaceOrientationLandscapeLeft",
    "UIInterfaceOrientationLandscapeRight",
])
pl["UIViewControllerBasedStatusBarAppearance"] = False

with path.open("wb") as f:
    plistlib.dump(pl, f)
print(f"patched: {path}")
