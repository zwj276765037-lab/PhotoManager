# PhotoManager iOS App

当前主线是原生 iOS App。首个 P0 技术闭环直接从系统照片资料库读取同一 `PHAsset` 的静态照片与 `.pairedVideo`，原生预览后把这对资源重新写回为一张新的 Live Photo；用户不需要先“存储为视频”。

## 当前实现

- SwiftUI 移动端工作台。
- `PHPickerViewController` 只显示 Live Photo。
- PhotoKit 读取 `.fullSizePhoto`/`.photo` 与 `.fullSizePairedVideo`/`.pairedVideo`。
- iCloud 原件允许联网下载并显示读取进度。
- `PHLivePhotoView` 原生预览。
- 使用 `PHAssetCreationRequest` 以 `.photo + .pairedVideo` 写回新的 Live Photo，不修改原件；保存后重新读取并验证 Live subtype 与完整资源对。
- 输入、临时资源和状态只保存在 App 沙盒；当前闭环没有云端依赖。

本里程碑写回的是原始画面的副本，用于证明“原生输入 → 原生成对读取 → 原生输出”成立。下一阶段才给静态照片和配对视频逐帧增加杂志元素，并重新生成匹配的 asset identifier 与 still-image-time 元数据。

## 在 Mac 上生成工程

需要 macOS、Xcode 15.4 或更新版本、XcodeGen，以及一台装有真实 Live Photo 的 iPhone。模拟器不能替代这项验收。

```bash
brew install xcodegen
cd workspace/ios
xcodegen generate
open PhotoManager.xcodeproj
```

在 Xcode 中：

1. 选择 `PhotoManager` Target → Signing & Capabilities。
2. 选择自己的 Apple Developer Team。
3. 将 `com.zwjlab.PhotoManager` 改为自己账号下唯一的 Bundle ID。
4. 连接真实 iPhone，允许开发者模式并运行。

## 首次真机验证

1. 点“选择原生 Live Photo”，授权读取照片。
2. 系统选择器应只显示 Live Photo；选择一张本地或 iCloud 素材。
3. 页面显示“原生 Live Photo 已就绪”，并能自动播放预览。
4. 确认状态中同时出现照片和配对视频的字节数。
5. 点“验证原生 Live Photo 写回”，授权添加照片。
6. 打开系统“照片”的最近项目，按住新照片；它应保持动作、声音和 Live 标记，原件不变。

任何一步只得到静态照片、缺少 `.pairedVideo`、iCloud 下载失败或写回后丢失 Live 标记，都视为 P0 未通过，不能开始杂志合成。

## 当前环境限制

仓库当前运行环境是 Linux，没有 Xcode、iOS SDK 和代码签名能力，因此这里只能完成工程结构、Swift 源码和配置静态检查。必须在 Mac 的 Xcode 中生成工程并用真实 iPhone 完成编译与 PhotoKit 验收。
