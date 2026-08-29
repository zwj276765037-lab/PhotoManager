# PhotoManager（原生 iOS Live Photo 动态杂志）

PhotoManager 的当前主线是原生 iOS App：直接选择系统相册中的 Live Photo，自动读取同一 `PHAsset` 的静态照片与 `.pairedVideo`，逐帧加入杂志设计后，再保存为一张新的原生 Live Photo。

用户不再需要手动“存储为视频”。视频仍是 Live Photo 的底层配对资源，但由 App 在后台自动处理。

## 当前阶段

第一里程碑先验证最底层闭环：

```text
选择原生 Live Photo
        ↓
PhotoKit 读取照片 + pairedVideo
        ↓
PHLivePhotoView 原生预览
        ↓
PHAssetCreationRequest 原生写回副本
        ↓
系统“照片”中保留 Live 标记和按压播放
```

`workspace/ios/` 已建立 SwiftUI、PHPicker、PhotoKit 成对读取、iCloud 原件进度、原生预览和原生写回代码骨架。当前运行环境是 Linux，不能调用 Xcode/iOS SDK；下一项外部验收是在 Mac 上生成工程并连接真实 iPhone。

原本的本地网站保留在 `workspace/web/`，只作为杂志版式、FFmpeg 动态样片和 MP4/GIF/JPG 兼容输出工具，不再是首发产品。

## 目录约定

```text
PhotoManager/
├── goal/               # 当前 iOS 产品需求、验收标准和上线说明
├── mission/            # 每次优化、验证结果和 Git 交付记录
└── workspace/
    ├── ios/            # 当前主线：原生 Live Photo iOS App
    ├── demo/           # 三种动态杂志视觉与 FFmpeg 样片
    ├── web/            # 辅助工具：本地网站与非 Live Photo 输出验证
    └── miniprogram/    # 后续预案，不承担原生 Live Photo 读取
```

## 交付规则

每轮成果均按以下顺序完成：

1. 在 `goal/` 更新需求与验收标准。
2. 在 `workspace/` 实现对应代码。
3. 完成与风险相匹配的静态检查、Xcode 构建或真机测试。
4. 在 `mission/` 记录时间、功能、验证和未解决问题。
5. 提交并推送到 [`origin/main`](https://github.com/zwj276765037-lab/PhotoManager)。

不会用强制推送覆盖远端历史。Xcode 构建、签名和真机结果必须如实区分，不能把 Linux 静态检查描述为 iOS 编译成功。

## 文档入口

- [iOS App 需求与验收标准](goal/README.md)
- [iOS 工程与真机验证说明](workspace/ios/README.md)
- [iOS App 上线指南](goal/IOS_RELEASE.md)
- [本地网站 v0.9 归档摘要](goal/archive/LOCAL_WEB_MVP_V0.9.md)
- [优化记录](mission/README.md)
- [代码工作区说明](workspace/README.md)
- [动态杂志视觉样片](workspace/demo/README.md)
