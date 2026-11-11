# 咕噜咕噜 iOS 端重建工程

APK → IPA **没有转换器**。Android 包 = DEX 字节码 + Android NDK 的 `arm64-v8a/*.so` + SecShell 壳；iOS 包 = Mach-O/ARM64 可执行文件 + iOS 版 Dart AOT 快照 + `Info.plist` + 苹果签名链。两者是两套独立产物。

本工程给的是**重建路线**：用 Flutter 重写一个能在 iPhone 上跑的 iOS 客户端，在 Apple 的构建链上编出可安装的 `.ipa`。

> **想直接装上手机看效果 → 看 [INSTALL.md](INSTALL.md)**（从拿 GitHub token 到手机上信任证书，一步不缺）

---

## 已产出的安装包（现在就能下）

| 项 | 值 |
|---|---|
| 文件 | `gulu-2.2.5-playable.ipa` |
| 大小 | 23,383,297 B |
| SHA-256 | `a8fde25b244c07c0945c90f89914c7579e81e6cc86a78f532c5c1bc870981919` |
| 下载 | <https://github.com/qiqi14356/gulu-ios/releases/download/v2.2.5-playable/gulu-2.2.5-playable.ipa> |
| OTA 清单 | <https://github.com/qiqi14356/gulu-ios/releases/download/v2.2.5-playable/manifest.plist> |
| 安装页 | <https://github.com/qiqi14356/gulu-ios/releases/download/v2.2.5-playable/install.html> |
| bundle id | `com.gulugulu.gulu` |
| 状态 | **未签名**，需 Sideloadly / AltStore / TrollStore 重签后安装 |
| OTA 直装 | 只有**你自己用证书签过**之后，`install.html` 那条 `itms-services` 路径才通；未签名包走 OTA 必然失败 |

这个包里**内置了 3 集可播放内容**（嫁金钗 第 02 / 05 / 06 集），分片清单来自真机
`exo_video_cache` 的 `urlMap`，播放时由 `LocalHlsServer` 把 CDN 上伪装成 `.png` 的
MPEG-TS 分片反代成 `video/mp2t` 喂给 `AVPlayer`。**不需要登录、不需要破解片库接口**。

自检（本地，不需要 iPhone）：

```bash
dart run scripts/dyn/test_hls.dart
# playlist: 嫁金钗 第02集 segs=888 dur=2984.2s
# m3u8 status=200 bytes=46178
# seg 0/300/887 status=200 ct=video/mp2t head=47401110
```

---

## 现状（已核对的事实）

| 项 | 结论 |
|---|---|
| 原包 | `com.hehefankuai.app` v2.2.5，Flutter 3.x，仅 `arm64-v8a` |
| 加固 | SecShell（`libSecShell.so` + 加密 `classes.dex` + `assets/meta-data/` RSA 签名），静态脱壳成本高 |
| API 域名 | **`libapp.so` 内无业务域名**（67 处 `://` 全是框架/本地地址）。base URL 由壳内 dex 解密或 `/app/runtime-policy` 运行时下发 |
| 官方 iOS 通道 | 官网 `api/site.php` 的 ios 块：`description="苹果端商城版"`、`url="#"`（**未配置**）、教程「搜索框输入 `jz10130` → 确定 → 大退重启」 |
| App Store | 用「咕噜咕噜」在 iTunes Search API 查 22 条结果，**没有一条是本 App** → 马甲应用名未公开 |
| 图标 | APK 内 182 个方形 PNG 全是广告/占位素材；改用官网 `assets/media/app-logo.jpg` 裁出鲸鱼 |
| 本机 | Windows，无 `xcodebuild`/`codesign` → **本机无法产出 `.ipa`**，必须交给 macOS runner |

---

## 快速开始

```bash
cd D:\dsh-work\gulu_ios

# 1) 自检（14 项，2 秒）
python scripts/preflight.py

# 2) 一条命令：建仓库 → 推代码 → 触发构建 → 等完成 → 下载 ipa
echo ghp_你的token > .gh_token
python scripts/gh_build_ios.py --repo gulu-ios

# 3) 产物在 build/ios/ipa/gulu-unsigned.ipa
#    用 Sideloadly 重签装机，详见 INSTALL.md
```

---

## 三条路线

### 路线 A：官方 iOS 版（最省事，前提是拿到马甲应用名）

官网 ios 块就是**伪装上架**模式：App Store 里挂一个工具类应用当马甲，装好后在它内部的搜索框输入 `jz10130`，大退重开即「变身」成影视 App。

要做的事只有一件：**问出马甲应用的名字或 App Store 链接**。

1. 打开 `https://glgl.tv/` → 点「苹果」→ 弹窗里 `url` 现在是 `#`，说明官方没填，或只在群里/客服处发。
2. 去官方渠道要：备用入口 `https://link3.cc/glgl`、App 内「意见反馈」、官方群。
3. 拿到名字后：App Store 搜索 → 安装 → 打开马甲应用 → 找到输入框（通常在「意见反馈」「设置」「搜索」）→ 输入 `jz10130` → 确定 → **上滑杀掉进程** → 重开。
4. 若提示「App 不可用 / 所在国家地区不提供」= 已下架，等新马甲。

> 这条路拿到的是官方签名、官方功能、能长期用的版本。

### 路线 B：本工程自建 `.ipa`（GitHub Actions 的 macOS runner 编译）

```bash
python scripts/gh_build_ios.py --repo gulu-ios
```

它会做完：建仓库 → 推代码 → 触发 workflow → 轮询状态 → 下载 artifact → 落到 `build/ios/ipa/`。

也可以手动：仓库 → **Actions** → `build-ios-unsigned` → **Run workflow** → 等 8–12 分钟 → 底部 **Artifacts** 下载。

这个 ipa 是**未签名**的，iPhone 不认，必须重签（见 INSTALL.md 第 3 步）。

#### 本地 macOS 编译（有 Mac 更快）

```bash
brew install flutter cocoapods
cd gulu_ios
flutter pub get
ORG=com.gulugulu NAME=gulu ./scripts/gen_ios_container.sh
python3 scripts/patch_info_plist.py ios/Runner/Info.plist
flutter build ios --release --no-codesign
./scripts/package_ipa.sh
```

有正式证书就直接签：

```bash
IDENTITY="Apple Distribution: Your Name (TEAMID)" \
PROVISION=~/Downloads/gulu.mobileprovision \
BUNDLE_ID=com.gulugulu.gulu \
./scripts/sign_and_ipa.sh
```

### 路线 C：OTA 分发（有自己的 HTTPS 服务器时）

适合把 ipa 挂到自己域名上，让别人用 Safari 点一下装：

```bash
python scripts/gen_ota_manifest.py \
  --ipa "https://你的域名/ipa/gulu.ipa" \
  --bundle-id com.gulugulu.gulu \
  --version 2.2.5 \
  --title "咕噜咕噜" \
  --out dist
```

得到 `dist/manifest.plist` + `dist/install.html`。把 ipa 和这两个文件上传到同一目录，用 **Safari** 打开 `install.html` 点按钮。

> OTA 安装要求 ipa 用 **企业证书** 或 **UDID 已登记的描述文件** 签，否则点了会报「无法安装」。

---

## 工程结构

```
gulu_ios/
├── lib/
│   ├── main.dart              入口，MaterialApp + 底部两页
│   ├── config.dart            API base、10 条探测路径、暗号常量
│   ├── api.dart               Dio 客户端 + ProbeResult
│   └── pages/
│       ├── home_page.dart     官方通道说明 + 片库占位
│       └── probe_page.dart    一键打 10 个接口，显示状态码和返回体
├── ios_assets/
│   ├── icon_src_1024.png      1024 源图（官网 logo 裁出来的鲸鱼）
│   └── AppIcon.appiconset/    15 个尺寸 + Contents.json
├── scripts/
│   ├── preflight.py           推 GitHub 前的本地体检（14 项）
│   ├── gh_build_ios.py        建仓库/推码/触发/等待/下载，一条命令
│   ├── gen_ios_container.sh   flutter create 出 ios/，改 bundle id，塞图标
│   ├── patch_pbxproj.py       精确改 PRODUCT_BUNDLE_IDENTIFIER
│   ├── patch_info_plist.py    补权限文案 / 后台音频 / ATS
│   ├── make_appicon.py        源图 → 全套 AppIcon
│   ├── package_ipa.sh         Runner.app → Payload/ → ipa（保住 +x 位）
│   ├── sign_and_ipa.sh        有证书时用：codesign + 打 ipa
│   ├── gen_ota_manifest.py    生成 itms-services 用的 manifest.plist
│   └── lint_dart.py           本机没 Dart 时的源码预检（被 preflight 取代）
├── .github/workflows/
│   └── ios-unsigned.yml       macos-15 上编未签名 ipa（17 步，含产物校验）
├── dist/                      已生成的 OTA 清单样例
├── pubspec.yaml               只依赖 dio
├── .gitattributes             强制 .sh 用 LF（不然 macOS 上会报 $\r 错误）
└── INSTALL.md                 装机全流程手册
```

---

## 自检覆盖了什么

`python scripts/preflight.py` 会验 14 项：

| 检查 | 抓的是什么错 |
|---|---|
| 必需文件 | 少个脚本/图标，推上去 10 分钟后才炸 |
| AppIcon 完整性 | 少了 1024 marketing 图标 → App Store 校验拒 |
| AppIcon 无 alpha | iOS 图标带透明通道 → 校验拒 |
| pubspec / 依赖声明 | 源码 import 了 pubspec 没写的包 → `pub get` 失败 |
| workflow 结构 | 不是 macOS runner / 没 `--no-codesign` / 没 upload-artifact |
| shell 语法 | `bash -n` 全过一遍 |
| python 语法 | `py_compile` 全过一遍 |
| .gitignore 覆盖 | token 或 build/ 被误提交 |
| .gitattributes | `.sh` 没用 LF → macOS 上报 `$\r: command not found` |
| bundle id 替换 | RunnerTests 一并被改 → 两个 target 同 id，Xcode 报错 |
| Info.plist 补丁 | 用**真实 Flutter 模板**跑一遍，验中文名/权限文案/原有键没被破坏 |
| ipa 打包自测 | 造一个假 `Runner.app` 真跑打包，验 `Runner` 是 `0755` |
| dart analyze | 有 Dart SDK 就跑真分析 |

---

## 已知限制

- **能播的是抓下来的剧集，不是无限片库**。片库列表走 `/app/bn/v2`（会话密钥加密的
  protobuf，`libapp.so` 里 AES S-box 零命中），静态+动态都不可复现 → **没有片库浏览**。
  要加新剧，只能在原版 App 里播一遍，再把 `exo_video_cache/<id>/1.json` 抽出来做成
  `assets/demo/*.json`（流程见下）。
- **m3u8 的 token 会过期，分片不会**。`sourceUrl` 里的 `m.php?data=...` 是一次性 token
  （176 字节密文，前三集固定前缀 `f4936982396fc13cbfe98f2dec40e6f3`），取一次就烂；
  但 `urlMap` 里每个分片的 CDN 地址**永久有效**，所以本工程只用 `urlMap`，不碰 token。
- **7 天重签**。免费 Apple ID 签的证书 7 天失效。买 $99/年开发者账号可延长到 1 年。
- **上不了 App Store**。需要开发者账号 + 正式证书，且影视聚合类内容过不了审核。
- **iOS 上没实机验证过**。构建机是 GitHub 的 macOS runner，产物结构/权限/架构/Info.plist
  都已逐项核对（见 `scripts/preflight.py`），但**没有在真 iPhone 上跑过**。

### 加一集新剧的完整流程

```bash
# 1) 平板/模拟器上装原版 APK，把目标剧集播一遍（让它写缓存）
adb -s <serial> shell su -c 'cd /data/data/com.hehefankuai.app/app_flutter/exo_video_cache && ls -t | head'

# 2) 把最新那个目录的 1.json 拉下来
adb -s <serial> shell su -c 'cat /data/data/com.hehefankuai.app/app_flutter/exo_video_cache/<id>/1.json > /sdcard/1.json'
adb -s <serial> shell su -c 'chmod 644 /sdcard/1.json'
adb -s <serial> pull /sdcard/1.json D:/dsh-work/cap/1.json

# 3) 转成工程用的压缩格式（prefix + tails，524 KB -> 67 KB）
python scripts/mk_demo_asset.py D:/dsh-work/cap/1.json --title "剧名" --episode "第07集" --id <videoPathId> --out assets/demo/ep07.json

# 4) 把新文件加进 lib/pages/home_page.dart 的 _sources 列表
#    （pubspec 的 assets/demo/ 是目录通配，新文件自动打进包）
# 5) 提交 → 推 main → CI 自动重建出带新剧集的 ipa
```

**注意**：`1.json` 里的 `durs` 单位是**毫秒**，`DemoPlaylist` 内部统一 `/1000.0` 转秒；
写 `#EXTINF` 时忘了除会得到 `8050.000000` 这种 2 小时的分片时长，AVPlayer 会判列表非法。

### 为什么不再尝试破解片库

已经试过并排除的路线（都留了脚本在 `scripts/dyn/`，但没有一条走通）：

| 路线 | 结果 |
|---|---|
| Frida hook `libSecShell.so` | attach 立刻 `target terminated with signal 11`，壳自带反调试 |
| 内存 dump 找明文域名/响应 | 9 个 dump 70 MB，`vod_name`/`m3u8`/`main_url`/域名 的 UTF-8+UTF-16LE **双编码全 0 命中** |
| `iptables DNAT` + 透传代理抓解析请求 | 62,782 包零命中 `dsxt`/`api.php`；播放复用缓存 resolvedUrl，根本不重新解析 |
| 裸 socket 直接打 `172.247.189.48:80` | 恒 `400 Bad Request`（nginx 层拒绝，非应用层），换 UA/Host/签名头都无效 |
| WebSocket `103.45.132.22:17979` 解密 | 帧 `02 08 0N 12 <len> <密文>`，AEAD 全组合（AESGCM/ChaCha20 × key 派生 × nonce × tag 布局）全部 `InvalidTag` |
| isar `app_cache.sqlite` 直读 | 二进制格式，全库 URL 正则 0 命中，无公开解析器 |
| `tos.php?url=` 反查 | 需要另一套体系的视频 id，手上所有 id（videoId/videoPathId/history id）全部「未找到视频URL」 |

结论：**片库这条路投入产出不成立**。但播放链路是通的 —— 这就是本工程走缓存分片的原因。
