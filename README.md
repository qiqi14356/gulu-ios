# 咕噜咕噜 iOS 端重建工程

APK → IPA **没有转换器**。Android 包 = DEX 字节码 + Android NDK 的 `arm64-v8a/*.so` + SecShell 壳；iOS 包 = Mach-O/ARM64 可执行文件 + iOS 版 Dart AOT 快照 + `Info.plist` + 苹果签名链。两者是两套独立产物，只能重新编译或向官方索取。

本工程给的是**第二条路**：用 Flutter 重建一个能在 iPhone 上跑的 iOS 客户端，产出可安装的 `.ipa`。

---

## 现状（已核对的事实）

| 项 | 结论 |
|---|---|
| 原包 | `com.hehefankuai.app` v2.2.5，Flutter 3.x，仅 `arm64-v8a` |
| 加固 | SecShell（`libSecShell.so` + 加密 `classes.dex` + `assets/meta-data/`），静态脱壳成本高 |
| API 域名 | **`libapp.so` 内无业务域名**（67 处 `://` 全是框架/本地地址）。base URL 由壳内 dex 解密或 `/app/runtime-policy` 运行时下发 |
| 官方 iOS 通道 | 官网 `api/site.php` 的 ios 块：`description="苹果端商城版"`、`url="#"`（**未配置**）、教程「搜索框输入 `jz10130` → 确定 → 大退重启」 |
| App Store | 用「咕噜咕噜」在 iTunes Search API 查 22 条结果，**没有一条是本 App** → 马甲应用名未公开 |
| 本机 | Windows，无 `xcodebuild`/`codesign`/`flutter` → **本机无法直接产出 `.ipa`** |

---

## 三条可执行路线

### 路线 A：官方 iOS 版（最省事，前提是拿到马甲应用名）

官网 ios 块就是**伪装上架**模式：App Store 里挂一个工具类应用当马甲，装好后在它内部的搜索框输入 `jz10130`，大退重开即「变身」成影视 App。这类模式在影视 App 圈是标准做法。

要做的事只有一件：**问出马甲应用的名字或 App Store 链接**。

1. 打开 `https://glgl.tv/` → 点「苹果」→ 弹窗里 `url` 现在是 `#`，说明官方还没填，或只在群里/客服处发。
2. 去官方渠道要：官网备用入口 `https://link3.cc/glgl`、App 内「意见反馈」、官方群。
3. 拿到名字后：App Store 搜索 → 安装 → 打开马甲应用 → 找到输入框（通常在「意见反馈」「设置」「搜索」）→ 输入 `jz10130` → 确定 → **后台大退**（上滑杀掉进程）→ 重新打开。
4. 若提示「App 不可用 / 所在国家地区不提供」= 已下架，等新马甲。

> 这条路拿到的是官方签名、官方功能、能长期用的版本，比自签稳。

### 路线 B：本工程自建 `.ipa`（现在就能跑，用 GitHub Actions 的 macOS 机器编译）

本机是 Windows 出不了 ipa，但 GitHub 免费提供 `macos-14` runner。工程里已经写好 workflow，推上去点一下就能下到 `.ipa`。

```bash
# 1. 建仓库并推上去（首次）
cd D:\dsh-work\gulu_ios
git init -b main
git add -A
git commit -m "gulu ios client"
git remote add origin https://github.com/<你的账号>/gulu_ios.git
git push -u origin main
```

2. GitHub 仓库 → **Actions** → 左侧 `build-ios-unsigned` → **Run workflow** → `api_base` 留默认 → Run。
3. 约 8–12 分钟，跑完在 run 页面底部 **Artifacts** 下载 `gulu-unsigned-ipa`，解压得到 `gulu-unsigned.ipa`。

这个 ipa 是**未签名**的，iPhone 不认。下一步必须重签，见路线 C。

#### 本地 macOS 编译（有 Mac 的话更快）

```bash
brew install flutter
cd gulu_ios
ORG=com.gulugulu NAME=gulu ./scripts/gen_ios_container.sh   # 只生成 ios/，不动 lib/
python3 scripts/patch_info_plist.py ios/Runner/Info.plist   # 显示名/权限文案/ATS
cd ios && pod install --repo-update && cd ..

flutter build ios --release --no-codesign \
  --dart-define=API_BASE=https://glgl.tv

./scripts/package_ipa.sh build/ios/iphoneos/Runner.app \
                        build/ios/ipa/gulu-unsigned.ipa
```

### 路线 C：把未签名 ipa 装到 iPhone

| 方式 | 需要 | 有效期 | 说明 |
|---|---|---|---|
| **Sideloadly**（Win/Mac） | Apple ID（免费） | 7 天 | 最省事，Windows 就能做。免费账号 7 天后重签 |
| **AltStore / SideStore** | Apple ID + 一台常开电脑或 StosVPN | 7 天自动续 | 装一次自动重签，适合长期用 |
| **TrollStore** | iOS 14.0–16.6.1（部分版本） | **永久** | 不需要 Apple ID，直接装，最理想 |
| **企业签名 / 超级签名** | 花钱买 | 3–12 个月 | 淘宝/服务商，几块到几十块，掉签要重装 |
| **付费开发者账号** | $99/年 | 1 年 | 自己签，可发给 100 台设备 |

**Sideloadly 操作（Windows）**：

1. 下载 `Sideloadly`（sideloadly.io）和 `iTunes`（苹果官网版，不是 Microsoft Store 版，否则缺驱动）。
2. iPhone 用数据线连电脑 → 信任此电脑。
3. Sideloadly 里拖入 `gulu-unsigned.ipa` → Apple ID 填自己的 → Start。
4. 输入 Apple ID 密码（用于生成描述文件，会传给苹果服务器）→ 等进度条完成。
5. iPhone：`设置 → 通用 → VPN与设备管理 → 开发者应用 → 你的 Apple ID → 信任`。
6. 桌面出现「咕噜咕噜」图标，可打开。

7 天后过期：重跑 Sideloadly 覆盖安装即可，App 内数据（登录态）通常保留在钥匙串/沙盒里，但 Isar 数据库会重建。

---

## 工程结构

```
gulu_ios/
├── lib/
│   ├── main.dart                 入口 + 底部两页导航
│   ├── config.dart               API_BASE（--dart-define 注入）+ 10 条探测路径 + jz10130
│   ├── api.dart                  Dio 客户端 + 探测结果模型
│   └── pages/
│       ├── home_page.dart        官方 iOS 通道说明 + 片库占位
│       └── probe_page.dart       一键打 10 条 API 路径，显示状态码/耗时/返回体
├── ios_assets/
│   ├── icon_src_1024.png         从官网 app-logo.jpg 裁出的鲸鱼图标（1024×1024，无透明）
│   └── AppIcon.appiconset/       15 个尺寸 + Contents.json
├── scripts/
│   ├── gen_ios_container.sh      临时目录 flutter create → 只拷 ios/ 回来
│   ├── patch_info_plist.py       显示名/权限文案/后台音频/ATS
│   ├── make_appicon.py           源图 → 全套 AppIcon（去 alpha）
│   ├── package_ipa.sh            Runner.app → Payload/ → 未签名 ipa
│   ├── sign_and_ipa.sh           用开发者证书 + 描述文件签出可装 ipa
│   └── gen_ota_manifest.py       manifest.plist + install.html（itms-services 网页安装）
├── dist/                         OTA 安装页示例产物
└── .github/workflows/ios-unsigned.yml    macOS runner 一键出 ipa
```

### 图标

官网 `https://glgl.tv/assets/media/app-logo.jpg`（1024×1024）上半部分是「官网 glgl.tv」红字，不能直接用。处理方式：从 y=445 裁掉文字区，上方 445 px 用接缝处真实背景色 `(198,237,254)` 做淡渐变补满，交界处无硬边。

重新生成：

```bash
python3 scripts/make_appicon.py ios_assets/icon_src_1024.png ios_assets/AppIcon.appiconset
```

### Info.plist 关键项

`patch_info_plist.py` 会写入：

- `CFBundleDisplayName = 咕噜咕噜`
- `ITSAppUsesNonExemptEncryption = false`（避免每次上传都问出口合规）
- `UIBackgroundModes = ["audio","fetch"]`（后台播放 + 后台拉数据）
- `NSPhotoLibraryUsageDescription` / `NSCameraUsageDescription` / `NSMicrophoneUsageDescription` 中文文案
- `NSAppTransportSecurity.NSAllowsArbitraryLoads = true`（原 App 有 `usesCleartextTraffic`，探测时可能撞明文接口）

### OTA 无线安装（可选）

```bash
python3 scripts/gen_ota_manifest.py \
  --ipa https://your.host/ipa/gulu.ipa \
  --bundle-id com.gulugulu.gulu \
  --version 2.2.5 \
  --title "咕噜咕噜" \
  --icon https://your.host/ipa/icon-57.png \
  --out dist
```

产出 `dist/manifest.plist` + `dist/install.html`。把 dist 和 ipa 都传到同一个 HTTPS 站点（证书必须受信任，自签会被 iOS 拒），iPhone 用 **Safari** 打开 `install.html` 点安装。

---

## 关于 API 域名

`libapp.so` 静态扫过：67 处 `://`，没有一个是业务域名。`glgl.tv` 上除了 `api/site.php`（官网配置）其余业务接口全 404。所以：

- 这个重建版现在只能当**壳 + 探测工具**用，打不出片库。
- 想真正能用，得先拿到 base URL。三个办法：
  1. 安卓机装原 App，`mitmproxy` 挂代理抓包，看首屏请求的 Host（最直接）。App 有 `app_integrity` 挑战，可能要配 Frida 过 SSL pinning。
  2. 脱 SecShell 壳拿到 dex，搜 `BASE_URL` / `Retrofit` 注解。
  3. 抓 `/app/runtime-policy` 的返回，里面很可能直接给 base。

拿到后不用改代码，构建时注入即可：

```bash
flutter build ios --release --no-codesign --dart-define=API_BASE=https://真实域名
```

---

## 不做的事

- 不把 APK 改名成 IPA 冒充（iOS 认不出 ELF，安装必失败）。
- 不用别人的企业证书签（掉签 + 隐私风险）。
- 不猜 App Store 马甲名硬装一个同名无关应用。
