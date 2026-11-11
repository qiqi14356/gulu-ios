# 装上 iOS 版：完整操作手册

从零到手机桌面上出现「咕噜咕噜」图标，全程在这份文档里。

---

## 目录

- [第 0 步：先说清楚这里发生了什么](#第-0-步先说清楚这里发生了什么)
- [第 1 步：拿一个 GitHub token（3 分钟）](#第-1-步拿一个-github-token3-分钟)
- [第 2 步：一条命令编出 ipa（等 10 分钟）](#第-2-步一条命令编出-ipa等-10-分钟)
- [第 3 步：用 Sideloadly 装到 iPhone](#第-3-步用-sideloadly-装到-iphone)
- [第 4 步：手机上信任证书](#第-4-步手机上信任证书)
- [备选：AltStore](#备选altstore)
- [备选：命令行手动跑](#备选命令行手动跑)
- [这条路的天花板在哪](#这条路的天花板在哪)
- [排错对照表](#排错对照表)

---

## 第 0 步：先说清楚这里发生了什么

你手上那个 `咕噜咕噜.apk.1` 是 **Android 专用产物**：

| 组成 | Android 的样子 | iOS 需要的样子 |
|---|---|---|
| 应用逻辑 | `classes.dex`（Dalvik 字节码，还被 SecShell 整体加密） | Mach-O ARM64 |
| Flutter 逻辑 | `lib/arm64-v8a/libapp.so`（**Android 版** Dart AOT 快照） | iOS 版 Dart AOT 快照 |
| 原生库 | Android NDK 编译的 `.so` | iOS 编译的 `.dylib` / static lib |
| 加固壳 | `libSecShell.so`（Android 版） | 根本不存在 iOS 版 |

**没有任何工具能把 APK 转成 IPA。** 这不是权限问题，是两种完全不同的二进制格式和运行时。

所以本工程做的是：**用同一份业务接口，重建一个 Flutter iOS 客户端**，再在 Apple 的构建链上编出 `.ipa`。

> 官方 iOS 版（App Store 上的马甲应用 + 暗号 `jz10130`）是另一条独立路线。本条路线产出的是**自制客户端**：界面和业务都是新的，接口指向你的服务端。

---

## 第 1 步：拿一个 GitHub token（3 分钟）

这一步只需要做一次。

1. 打开 <https://github.com/settings/tokens>
2. 点 **Generate new token** → **Generate new token (classic)**
3. Note 随便写，比如 `gulu-ios`
4. Expiration 选 **30 days** 就够
5. 勾权限：
   - ☑ **repo**（整组，展开后全勾）
   - ☑ **workflow**（在 `admin:org` 之外单独一项，往下翻）
6. 拉到底点 **Generate token**
7. 复制那串 `ghp_...`（**只显示一次**）

然后把它存到工程里（这个文件已被 `.gitignore` 排除，不会入库）：

```bash
cd D:\dsh-work\gulu_ios
echo ghp_你复制的那串 > .gh_token
```

> Windows 下用记事本存也行，注意别有 BOM、别有空格。

---

## 第 2 步：一条命令编出 ipa（等 10 分钟）

```bash
cd D:\dsh-work\gulu_ios
python scripts/gh_build_ios.py --repo gulu-ios
```

它会依次做完：

```
[12:50:01] token 账号: yourname
[12:50:02] 创建仓库 yourname/gulu-ios (private=False)
[12:50:05] 推送到 yourname 的 main 分支
[12:50:09] 推送完成
[12:50:10] 触发 workflow_dispatch
[12:50:14] run #1 id=1234567890 已启动
[12:50:29] 构建状态: in_progress/-
[12:55:41] 构建状态: completed/success
[12:55:42] 下载 artifact: gulu-unsigned-ipa (18874368 B)
[12:55:44]   -> D:\dsh-work\gulu_ios\build\ios\ipa\gulu-unsigned.ipa (18350080 B)
```

**产物：** `D:\dsh-work\gulu_ios\build\ios\ipa\gulu-unsigned.ipa`

想要私有仓库加 `--private`：

```bash
python scripts/gh_build_ios.py --repo gulu-ios --private
```

只想推代码、暂时不编：

```bash
python scripts/gh_build_ios.py --repo gulu-ios --skip-build
```

### 构建过程中 GitHub 上发生了什么

跑完可以去 `https://github.com/你的用户名/gulu-ios/actions` 看实时日志。macOS runner 会：

1. 装 Xcode 15.4
2. 装 Flutter 3.24.5
3. `flutter create --platforms=ios` 生成 `ios/` 容器
4. 改 bundle id 成 `com.gulugulu.gulu`
5. 塞进预生成的鲸鱼图标（15 个尺寸）
6. 补 Info.plist（中文权限文案、后台音频、ATS）
7. `flutter build ios --release --no-codesign`
8. 验产物结构（`Runner`、`App.framework/App`、`Flutter.framework`）
9. 打成 `Payload/Runner.app` 结构的 zip → 改名 `.ipa`
10. 上传 artifact

---

## 第 3 步：用 Sideloadly 装到 iPhone

未签名的 ipa **不能直接双击装**，要先用你自己的 Apple ID 重签。Windows 上最省事的是 Sideloadly。

### 3.1 装 Sideloadly

下载：<https://sideloadly.io/>

安装时会一起装 **iTunes**（或要求你装 Apple 的驱动包）。如果之前装过 Microsoft Store 版的 iTunes，Sideloadly 会提示找不到驱动——去装 **Apple 官网版的 iTunes**（不是 Store 版）：

<https://support.apple.com/zh-cn/106372>

### 3.2 手机连电脑

1. iPhone 用数据线插上
2. 手机上弹「要信任此电脑吗」→ **信任** → 输密码
3. 电脑上打开 Sideloadly，左上角 `iDevice` 里应该能看到你的手机

### 3.3 拖入 ipa

1. **IPA 框**：点开选 `D:\dsh-work\gulu_ios\build\ios\ipa\gulu-unsigned.ipa`
2. **Apple ID 框**：填你的 Apple ID 邮箱
3. 点 **Start**

会弹窗要 Apple ID 密码（给 Sideloadly 生成签名证书用）。

> 强烈建议用**小号 Apple ID**，不要用你的主账号。免费账号重签 7 天过期，反复签名有可能触发风控。

### 3.4 等签名完成

```
Sideloadly! 2.0
...
Signing...
Installing...
Done.
```

手机桌面上应该出现「咕噜咕噜」图标。

---

## 第 4 步：手机上信任证书

这一步不做，点图标会闪退并提示「不受信任的开发者」。

1. 手机 **设置** → **通用** → **VPN 与设备管理**
2. 在「开发者 App」下找到你的 Apple ID
3. 点进去 → **信任「你的 Apple ID」** → **信任**
4. 回桌面点图标，能起来就成功了

### 7 天到期怎么办

免费 Apple ID 签的证书 **7 天失效**，到期后 App 打不开。两个选择：

- 重新跑一遍第 3.3 步（Sideloadly 会重新签，数据保留）
- 装 **AltStore**，它会用同一台电脑做 AltServer 自动续签（手机和电脑同一个 Wi-Fi 时自动刷新）

---

## 备选：AltStore

<https://altstore.io/>

1. Windows 装 AltServer
2. 手机连电脑，AltServer 托盘图标 → Install AltStore → 选你的设备 → 输 Apple ID
3. 手机上会装好 AltStore
4. AltStore 里 **My Apps** → 左上 **+** → 选 `gulu-unsigned.ipa`
5. 同样要在「VPN 与设备管理」里信任

AltStore 的好处是后台自动续签，不用每 7 天手动重来。

---

## 备选：命令行手动跑

不想用那个 Python 脚本，就手动来：

```bash
cd D:\dsh-work\gulu_ios

# 1) 建仓库（网页上建也行，建成空的，别勾 README）
# 2) 推代码
git remote add origin https://github.com/你的用户名/gulu-ios.git
git push -u origin main

# 3) 去 Actions 页面点 Run workflow
#    https://github.com/你的用户名/gulu-ios/actions/workflows/ios-unsigned.yml

# 4) 跑完在页面底部下载 artifact
```

---

## 这条路的天花板在哪

说清楚，免得你白折腾：

### 能做成的

- ✅ 一个能装、能启动、有图标、有界面的 iOS App
- ✅ 能探测你服务端的 10 个接口路径，把返回体打在屏幕上
- ✅ 完全脱离 Android 那套壳和依赖

### 做不到的

- ❌ **不能自动变成原版咕噜咕噜的界面和片库**
  原版的业务逻辑全在 `libSecShell.so` 保护的加密 dex 里，API 域名也是运行时解密的。没有真实 base URL，就没有片单、没有播放、没有弹幕。

- ❌ **不能上架 App Store**
  没有开发者账号（$99/年）、没有正式签名证书、内容是影视聚合类，过不了审核。

- ❌ **7 天要重签一次**（免费 Apple ID 的硬限制）
  想免掉就买 Apple Developer Program（$99/年），签出来的证书 1 年有效。

### 想让它真能用，下一步该干什么

1. 拿一台**已 root 或能跑 Frida 的 Android 机**，装原版 APK
2. 用 Frida hook `libSecShell.so` 的 `JNI_OnLoad` 和 dex 解密函数，dump 出真实 `classes.dex`
3. 在 dump 出来的 dex 里搜 `BASE_URL` / `http` 常量，拿到真实 API 域名
4. 在安卓机上抓包（`mitmproxy` + 装系统证书），把 `/api.php`、`/movie.do` 的请求/响应结构记录下来
5. 把真实域名通过 `--dart-define=API_BASE=https://真实域名` 传进构建，然后按抓到的结构补 `lib/api.dart` 的模型层

这个流程的每一步都不在「转格式」范畴，是**重新实现**。

---

## 排错对照表

| 现象 | 原因 | 怎么修 |
|---|---|---|
| `gh_build_ios.py` 报 `HTTP 401` | token 错了或过期 | 重新生成，确认没有多余空格 |
| 报 `HTTP 403` 且提示 `workflow` 权限 | token 没勾 workflow | 重新生成，勾上 workflow |
| Actions 里看不到 workflow | `.github/workflows/` 没推上去 | `git ls-files .github` 确认，然后重推 |
| 构建卡在 `pod install` 超时 | CocoaPods 拉 spec 慢 | 重跑一次；runner 上偶发 |
| `xcodebuild` 报 `unable to find SDK` | Xcode 版本没选上 | 把 `xcode_version` 改 `16.2` 或 `latest-stable` 试 |
| `flutter build` 报 `Runner.app not found` | 编译失败但被吞了 | 看 Actions 里 `Build (release, no codesign)` 那步的完整日志 |
| Sideloadly 报 `Could not find AltServer` / 找不到设备 | 缺 Apple 驱动 | 装 Apple 官网版 iTunes |
| Sideloadly 报 `Provision.cpp:150` | Apple ID 二次验证 | 去 appleid.apple.com 生成一个 App 专用密码，用它代替主密码 |
| 装好了但点开闪退 | 证书没信任 | 设置 → 通用 → VPN 与设备管理 → 信任 |
| 装好了闪退且已信任 | `Runner.app` 缺 `App.framework` | 看 CI 的 `Verify Runner.app` 步骤有没有过 |
| 7 天后打不开 | 免费证书过期 | 重签，或用 AltStore 自动续签 |
| 图标是白底问号 | AppIcon 没塞进去 | 检查 `ios_assets/AppIcon.appiconset/` 有 15 个 PNG + Contents.json |

---

## 工程文件说明

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
│   ├── gen_ios_container.sh   flutter create 出 ios/，改 bundle id，塞图标
│   ├── patch_pbxproj.py       精确改 PRODUCT_BUNDLE_IDENTIFIER
│   ├── patch_info_plist.py    补权限文案 / 后台音频 / ATS
│   ├── make_appicon.py        源图 → 全套 AppIcon
│   ├── package_ipa.sh         Runner.app → Payload/ → zip → .ipa
│   ├── sign_and_ipa.sh        有证书时用：codesign + 打 ipa
│   ├── gen_ota_manifest.py    生成 itms-services 用的 manifest.plist
│   ├── gh_build_ios.py        建仓库/推码/触发/等待/下载，一条命令
│   └── lint_dart.py           本机没 Dart 时的源码预检
├── .github/workflows/
│   └── ios-unsigned.yml       macos-14 上编未签名 ipa
├── dist/                      已生成的 OTA 清单样例
├── pubspec.yaml               只依赖 dio
└── .gitattributes             强制 .sh 用 LF（不然 macOS 上会报 $\r 错误）
```

---

## 一句话总结

**APK 转不成 IPA。** 这份工程给你的是：一个能编出 `.ipa`、能装上手机、能跑的 Flutter iOS 客户端骨架 —— 界面是你自己的，接口要你自己拿真域名填。
