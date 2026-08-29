# PhotoManager 原生 iOS Live Photo 动态杂志 App 需求

> 版本：v1.0-draft
>
> 状态：已确认切换为原生 iOS App；本地网站降为辅助验证工具
>
> 更新时间：2026-08-29
>
> 核心目标：直接选择原生 Live Photo，编辑后输出新的原生 Live Photo，用户不再手动“存储为视频”

## 1. 产品决定

PhotoManager 的首发产品正式切换为 Swift/SwiftUI 原生 iOS App。

用户的核心诉求不是把 Live Photo 转成普通视频或 GIF，而是：

```text
系统“照片”中的原生 Live Photo
        ↓
App 直接选择同一个 PHAsset
        ↓
自动读取静态原图 + pairedVideo
        ↓
逐帧加入杂志版式、文字和视觉元素
        ↓
生成匹配的静态照片 + 配对 MOV + Live Photo 元数据
        ↓
保存为系统“照片”中的一张新 Live Photo
```

用户不需要看见或手动处理 MOV。“跳过视频”指跳过用户手动转换环节；技术底层仍必须处理 pairedVideo，因为 Live Photo 本身就是成对的照片与视频资源。

本地网站已验证杂志版式与 MP4/GIF/JPG 渲染，但 Safari 无权获得 PhotoKit 成对资源。因此 `workspace/web/` 保留为辅助样片工具，不再决定主产品功能边界。网站阶段归档见 [v0.9 摘要](archive/LOCAL_WEB_MVP_V0.9.md)。

## 2. 一句话主张

> 不是把 Live Photo 转成视频，而是把它原生编成一张仍然会动的杂志封面。

## 3. 核心术语

| 名称 | 定义 |
| --- | --- |
| 原生 Live Photo | 同一系统照片资产中的静态照片、配对视频及匹配元数据 |
| `PHAsset` | PhotoKit 中代表用户选择照片资产的对象 |
| `.pairedVideo` | 与 Live Photo 静态照片配对的 MOV 资源 |
| content identifier | 同时写入静态照片和配对视频、用于把两者识别为同一 Live Photo 的标识 |
| still-image-time | 配对视频中的定时元数据，标记 Live Photo 使用的关键静态时刻 |
| 原生写回 | 使用 `.photo + .pairedVideo` 创建新的系统照片资产，并保持 Live 标记和按压播放 |
| 动态杂志封面 | 在静态帧和全部视频帧上使用一致杂志设计、最终仍以 Live Photo 交付的作品 |

## 4. P0：原生 Live Photo 闭环

P0 先证明原生输入和原生输出成立，再接入杂志渲染。任何只得到静态首帧或普通视频的方案都不算通过。

### 4.1 权限和选择

- 使用系统 `PHPickerViewController`，筛选器只显示 Live Photo。
- 请求 PhotoKit 读写权限时明确说明：读取用户主动选择的 Live Photo 静态照片和配对视频，并把新作品写回相册。
- 支持完整权限和有限照片权限；拒绝、撤销或仅允许新增时显示可理解状态，不循环弹窗。
- 每次只选择 1 张 Live Photo；不扫描、上传或分析用户未选择的其他相册内容。
- 选择器必须返回可追踪的 `assetIdentifier`，并解析为同一个 `PHAsset`。

### 4.2 成对资源读取

- 使用 `PHAssetResource.assetResources(for:)` 获取静态照片和 `.pairedVideo`。
- 静态资源优先读取 `.fullSizePhoto`，降级为 `.photo`。
- 动态资源优先读取 `.fullSizePairedVideo`，降级为 `.pairedVideo`。
- 两个资源写入同一个随机任务目录，记录原始文件名、UTType、字节数、像素、时长和校验和。
- iCloud 原件允许联网下载，显示真实进度并支持失败重试；不能把缩略图当作原件。
- 缺少任一资源、资源损坏或选择项不是 Live Photo 时立即失败，不能降级成静态照片后继续宣称成功。

### 4.3 原生预览

- 使用 `PHLivePhotoView` 预览系统返回的 `PHLivePhoto`。
- 支持自动播放一次、按住播放、静音状态说明和重新选择。
- 界面必须同时显示“照片已读取”和“pairedVideo 已读取”，而不是只显示一张缩略图。

### 4.4 原生写回验证

- 第一技术里程碑直接把未修改的原始成对资源创建为一张新的 Live Photo，用于验证完整往返。
- 使用 `PHAssetCreationRequest` 分别以 `.photo` 与 `.pairedVideo` 添加资源。
- 不修改、覆盖或删除用户原件。
- 写回后必须在系统“照片”中显示 Live 标记，按住可以播放完整动作；重新读取仍能找到一张照片资源和一份 pairedVideo。
- 原生成对写回未通过真机验收前，不开始逐帧杂志合成。

## 5. P1：动态杂志合成

P0 通过后，同一设计必须同时应用于静态照片和配对视频的每一帧。

### 5.1 设计能力

- 首发结构：先锋动态封面、斜切破版、三时态切片。
- 首发编辑：标题、副标题、日期、刊号、颜色、文字显隐和主体焦点。
- 所有元素使用安全区，不能遮挡高置信度清晰人脸。
- 静态照片与视频关键帧的裁切、字体、换行、颜色和图层位置必须一致。
- 真实人物面容和动作不得被生成模型重绘或改变。

### 5.2 静态照片渲染

- 从原始静态照片解码，不使用视频抽帧替代原图。
- 保留方向、宽高比、色彩信息和尽可能多的原始像素。
- 生成新 JPEG/HEIC 时写入新的 Live Photo content identifier。
- 杂志封面所对应的静态时刻必须与视频的 still-image-time 一致。

### 5.3 配对视频渲染

- 使用 AVFoundation、Core Image、Core Animation 或 Metal 对全部视频帧应用同一设计。
- 不先转 GIF，不使用网页预览文件作为高清源，不做无意义的多次有损转码。
- 输出兼容 PhotoKit 的 MOV，并写入与静态照片相同的 `com.apple.quicktime.content.identifier`。
- 建立 `com.apple.quicktime.still-image-time` 定时元数据轨道。
- 保留原方向和合理音频；是否默认保留声音由真机测试后冻结。
- 写回前校验 content identifier 一致、still-image-time 存在、时长有效且视频可完整解码。

### 5.4 新 Live Photo 写回

- 把新静态照片和新 pairedVideo 写回为一个新资产。
- 写回成功后重新通过 PhotoKit 读取并核验资源对，而不是只依赖保存回调。
- 用户可以删除新作品，不影响原件。
- 同时允许可选导出 MP4/JPG 作为社交平台兼容副本，但不能用这些副本代替 Live Photo 主结果。

## 6. 用户流程

```text
首次说明与照片权限
        ↓
系统选择器只显示 Live Photo
        ↓
选择 1 张并下载原始成对资源
        ↓
原生 Live Photo 预览
        ↓
选择杂志结构与文字
        ↓
预览静态落版帧和按压动态
        ↓
生成新的照片 + pairedVideo + 匹配元数据
        ↓
原生写回并重新读取验证
        ↓
在系统“照片”中按住播放 / 可选导出 MP4 分享
```

## 7. 本地数据与隐私

- 首个原型完全在 iPhone 本机处理，不要求账号、云端上传或外部 AI 密钥。
- 每次导入使用随机任务目录；原始文件名只用于展示和保留写回名称，不能决定沙盒路径。
- 临时照片、pairedVideo、中间帧和输出资源在任务取消、保存完成或到期后清理。
- 不修改系统相册原件，不读取未选择资产，不保存人物身份特征。
- 后续如果引入云端渲染，必须另行审核加密、数据期限、删除、跨境和内容安全要求，不能默认沿用本地原型权限。

## 8. 技术架构

```text
SwiftUI 界面
  ├── PHPicker / PhotoKit 权限
  ├── LivePhotoImportService
  │     └── PHAssetResourceManager 写出原图 + pairedVideo
  ├── PHLivePhotoView 原生预览
  ├── LivePhotoCompositionService（P1）
  │     ├── 静态照片渲染
  │     ├── AVFoundation 视频逐帧合成
  │     └── content identifier + still-image-time 元数据
  └── LivePhotoExportService
        └── PHAssetCreationRequest(.photo + .pairedVideo)
```

首版最低系统建议 iOS 17，使用当前稳定版 Xcode 和 Swift。工程通过 XcodeGen 描述，真实构建、签名和 PhotoKit 验收必须在 macOS 与真实 iPhone 完成。

## 9. P0 真机验收标准

1. App 能在真实 iPhone 启动，且不依赖本地网站或电脑服务。
2. 首次进入时权限用途说明准确，不声称读取整个相册。
3. 系统选择器只显示 Live Photo，每次最多选择 1 张。
4. 用户不执行“存储为视频”也能进入导入流程。
5. 选择结果能解析为同一个 `PHAsset`，并确认 `.photoLive` subtype。
6. 每个成功任务同时得到静态照片和 pairedVideo，任一缺失时失败。
7. 本地原件与 iCloud 原件都能显示真实读取进度。
8. 导入状态显示两个资源的文件名、类型和非零字节数。
9. `PHLivePhotoView` 能播放完整动作，而不是只显示静态首帧。
10. 写回按钮创建新资产，不修改原件。
11. 新资产在系统“照片”中显示 Live 标记。
12. 按住新资产能播放动作并结束于正常画面，无黑帧或损坏。
13. 重新读取新资产仍能找到一份照片资源和一份 pairedVideo。
14. 原件与新资产均可独立删除，删除一个不影响另一个。
15. 拒绝读取权限时显示设置说明，App 不崩溃或循环请求。
16. 拒绝新增权限时仍保留已导入预览，并明确写回未完成。
17. iCloud 断网、资源缺失、空间不足和写回失败均显示真实错误。
18. App 进入后台再返回时不会把旧任务错误标记为成功。
19. 至少用 20 张真实 Live Photo 覆盖横竖屏、前后摄、明暗场景、不同动作和声音。
20. 20 张样本全部做到“无需手动转视频 → 原生读取 → 新 Live Photo 写回”，才允许 P0 通过。

## 10. P1 杂志合成验收标准

1. 静态照片与配对视频使用同一设计版本和 content identifier。
2. 新视频包含有效 still-image-time 定时元数据。
3. 写回前后 Live 标记、按压播放和声音策略符合设计。
4. 静态落版帧与按压播放关键时刻的版式像素对齐。
5. 文字在所有视频帧中位置稳定、清晰可读且不闪烁。
6. 输出不改变人物五官、真实动作含义或主体比例。
7. 高分辨率原图不被视频分辨率替代；视频不经过 GIF 回转。
8. 横竖屏、旋转元数据、HDR/SDR 和不同编码均有明确处理或安全降级。
9. 合成后视频完整解码，音画时长有效，无黑帧、断帧和损坏元数据。
10. 从系统“照片”重新读取 20 张合成结果，成对资源和设计均保持完整。

## 11. 当前代码里程碑

`workspace/ios/` 已建立 P0 工程骨架：

- SwiftUI 原生工作台。
- Live Photo 专用系统选择器。
- PhotoKit 成对资源分类与 iCloud 原件写出。
- `PHLivePhotoView` 原生预览。
- `.photo + .pairedVideo` 原生写回副本。
- 权限、进度、错误和不修改原件的状态提示。

当前 Linux 环境没有 Xcode/iOS SDK，以上代码尚未完成编译、签名和真机 PhotoKit 验收。生成 Xcode 工程和真机步骤见 [iOS 工作区说明](../workspace/ios/README.md)。

## 12. 暂不进入首个 P0

- Android Motion Photo。
- 微信小程序原生 Live Photo 读取。
- 云端账号、多人协作和公开作品社区。
- 自动发布朋友圈；社交平台不保证保留 Live Photo 资产结构。
- 多张 Live Photo 拼接、多轨专业时间线、音乐库和复杂关键帧。
- 生成或改变人物面容、身体和真实动作。

## 13. 上线

App Store、TestFlight、权限、隐私和审核流程见 [iOS App 上线指南](IOS_RELEASE.md)。首个可安装构建必须先通过 P0 真机闭环，再宣传“支持原生 Live Photo 输入和输出”。

## 14. 官方参考

- [PhotoKit](https://developer.apple.com/documentation/photokit)
- [`PHAsset`](https://developer.apple.com/documentation/photokit/phasset)
- [`PHAssetResource`](https://developer.apple.com/documentation/photokit/phassetresource)
- [`PHAssetResourceManager`](https://developer.apple.com/documentation/photokit/phassetresourcemanager)
- [`PHAssetCreationRequest`](https://developer.apple.com/documentation/photokit/phassetcreationrequest)
- [`PHPickerViewController`](https://developer.apple.com/documentation/photokit/phpickerviewcontroller)
- [`PHLivePhotoView`](https://developer.apple.com/documentation/photosui/phlivephotoview)
- [AVFoundation](https://developer.apple.com/documentation/avfoundation)
