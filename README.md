# PhotoManager（iOS AI 动态人生杂志）

以 iOS 原生 Live Photo 为核心输入的 AI 动态杂志封面生成项目。

当前阶段：首发平台已从纯微信小程序调整为“Swift/SwiftUI iOS App＋云端渲染”。原生 Live Photo 读取进入 P0，同时兼容 GIF 和普通视频输入；结果可选择 GIF、MP4 或两者，并附 JPG 封面。`goal/README.md` 为 v0.6 待审核稿；`workspace/demo/` 已提供视频/GIF 双输入双输出、三种结构和清晰度对比样片，下一步先实现 Live Photo 成对资源读取原型。

## 目录约定

```text
PhotoManager/
├── goal/       # 项目需求、功能范围、验收标准、上线说明
├── mission/    # 每一次优化的时间、内容、验证结果和提交记录
└── workspace/  # iOS App、后续小程序、后端、渲染器和测试代码
```

三个目录的职责不能混用：

- `goal/` 回答“要做什么、做到什么程度”。
- `mission/` 回答“何时做了什么、是否验证通过”。
- `workspace/` 存放“实际运行的代码”。

## 最底层工作方式

用户在 iOS App 中主动选择一张原生 Live Photo、一段短视频或一个 GIF。App 负责 PhotoKit 资源读取与配对、素材预览、高光确认、输出格式和轻量编辑；云端负责运动分析、主体分层、杂志版式、循环编排，以及 MP4/GIF/JPG 渲染。第一版采用以下数据流：

```text
用户选择原生 Live Photo、普通视频或 GIF
        ↓
App 读取并校验 Live Photo 静态照片＋pairedVideo，或其他原文件
        ↓
私有上传与输入内容安全检查
        ↓
AI 为视频推荐高光；短 GIF 默认保留完整动作
        ↓
AI 生成主体分层、杂志版式和短文案
        ↓
生成 3 个与素材兼容、具有结构性差异的动态候选
        ↓
用户调整片段、焦点、标题、速度和动态强度
        ↓
用户选择高清 MP4、GIF 动态图片或两者，并生成 JPG 封面
        ↓
保存到相册后发布朋友圈或其他社交平台
```

底层数据分为三部分：

1. 私有临时文件：Live Photo 静态照片与配对视频、普通视频/GIF、代理视频、主体蒙版和预览，按明确期限自动清理。
2. 动态海报计划：高光片段、落版帧、循环方式、主体轨迹、版式、文字、字体和颜色，可用于恢复任务和确定性重渲染。
3. 输出文件：服务端从同一高清母版生成首尾闭环 MP4、GIF 动态图片和 JPG 封面；用户选择需要的格式，是否自动重播由发布平台决定。

MVP 优先采用 Swift/SwiftUI、PhotoKit、私有对象存储、异步媒体任务、运动分析和 FFmpeg 确定性渲染。微信小程序后续只承担作品管理、预览和分享引导。AI 密钥只保存在服务端；高级分割不可用时仍可降级为受规则约束的动态封面，不能退化为视频矩形加边框。

## 每次成果的交付规则

每一轮修改都按以下顺序完成：

1. 在 `goal/` 确认或更新需求与验收标准。
2. 只在 `workspace/` 修改项目实现。
3. 完成与变更风险相匹配的检查或测试。
4. 在 `mission/` 追加日期、优化内容、验证结果和未解决问题。
5. 提交 Git，并推送到 `origin/main`：<https://github.com/zwj276765037-lab/PhotoManager>。

这里的“覆盖到 GitHub”定义为：GitHub 的 `main` 分支是最终成果基线，每次成果都提交并正常推送。默认不使用强制推送，以免误删远端历史；只有明确要求重写历史且确认备份后才会执行。

## 文档入口

- [项目需求与验收标准](goal/README.md)
- [iOS App 上线指南](goal/IOS_RELEASE.md)
- [后续微信小程序上线指南](goal/WECHAT_RELEASE.md)
- [已归档的 v0.4 三页静态人生杂志需求](goal/archive/AI_LIFE_MAGAZINE_V0.4.md)
- [已归档的 v0.3 AI 朋友圈拼图需求](goal/archive/AI_MOMENTS_COLLAGE_V0.3.md)
- [已归档的照片分类需求](goal/archive/PHOTO_CLASSIFICATION_V0.2.md)
- [优化记录](mission/README.md)
- [代码工作区说明](workspace/README.md)
- [首轮动态杂志视觉样片](workspace/demo/README.md)
