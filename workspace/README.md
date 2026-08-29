# 代码工作区

`workspace/` 只存放可运行的项目代码、配置样例和测试，不存放需求讨论或过程记录。

项目进入实现阶段后，建议采用以下结构：

```text
workspace/
├── demo/              # 当前可直接播放的三版动态杂志视觉样片
├── ios/               # 当前首发：原生 Live Photo 读取、编辑与写回
│   ├── project.yml    # XcodeGen 工程定义
│   └── PhotoManager/  # SwiftUI、PhotoKit、服务与资源
├── web/               # 辅助工具：手机局域网网站与 MP4/GIF/JPG 验证
│   ├── static/        # 移动端优先的上传、选项、状态、预览与下载页面
│   ├── server.py      # 本地 HTTP、上传隔离、任务队列、Range 与结果接口
│   ├── start.sh       # 创建隔离环境并监听本机/局域网地址
│   └── runtime/       # 本地素材、日志和结果，已由 Git 忽略
├── miniprogram/       # 后续作品管理/预览/分享入口，不负责 Live Photo 采集
├── backend/           # 异步队列、动态分析、AI 调度、内容安全与数据清理
├── renderer/          # FFmpeg 动态海报预览、MP4/GIF、封面与 AI 标识处理
├── tests/             # 自动化测试或可复现测试脚本
└── README.md          # 本地开发、配置和测试说明
```

## 实现原则

- 当前首发为原生 iOS App：使用 SwiftUI、PHPicker、PhotoKit 和 AVFoundation，用户直接选择原生 Live Photo，不手动“存储为视频”。
- P0 必须读取同一 `PHAsset` 的静态照片和 `.pairedVideo`，通过 `PHLivePhotoView` 预览，并以 `.photo + .pairedVideo` 写回新的系统 Live Photo。
- 原生写回副本通过真实 iPhone 验收后，才接入静态照片和全部视频帧的杂志合成、content identifier 与 still-image-time 元数据生成。
- `web/` 降为辅助工具：电脑运行 Python/FFmpeg，手机可验证版式和 MP4/GIF/JPG，但网站结果不代表原生 Live Photo 能力。
- 每个上传任务使用随机标识和独立的 Git 忽略目录；原文件名只作为展示信息，不能决定磁盘路径。
- 本地渲染使用单工作线程异步队列，页面刷新、手机锁屏或 Safari 进入后台时不终止电脑上的任务。
- 浏览器无法获得 PhotoKit 成对资源，不能再作为主产品输入方案；网站只保留真实能力提示，不能伪称原生 Live Photo 导入成功。
- 本地服务为手机访问监听局域网地址，但没有账号和访问密码；只允许在可信网络临时启动，不得暴露公网。
- 上传、输入审核、规范化、高光分析、主体跟踪、版式规划、预览、高清渲染和输出审核均有独立状态与重试策略。
- MP4、GIF 与 JPG 共享 `designVersion`、高光片段、落版帧、字体和渲染版本，旧异步结果不得覆盖新编辑。
- 同一设计先生成无损版式母版，再分别编码 MP4、GIF 与 JPG；视频输出不经过 GIF，GIF 输出不经过有损 MP4，预览代理不参与高清交付。
- 高级分割不可用时降级为安全动态封面，不能退化为视频矩形加边框。
- 当前原型不需要 AI 密钥、云存储凭据或生产环境配置，用户素材、日志和结果不得提交到 Git。
- 每一个功能都要能够对应 `goal/` 中的需求和 `mission/` 中的一次记录。

## 当前可验证成果

`demo/` 已用一段 4.10 秒夜间篮球视频和对应多帧 GIF 生成双输入双输出样片：

- 先锋全出血动态封面。
- 斜切破版基线。
- 三时态时间切片。
- 视频→MP4、视频→GIF、GIF→MP4、GIF→GIF 四条路径。
- CRF 19 标准档与 CRF 14 高清档像素对比。

打开 `demo/index.html` 可以并排循环比较。第二版尚未加入逐帧人物蒙版，因此只验证斜切动态区和图文层级，不代表完整主体破版。

`ios/` 已建立当前 P0 代码骨架：

- Live Photo 专用系统选择器和 PhotoKit 读写授权。
- `.fullSizePhoto/.photo` 与 `.fullSizePairedVideo/.pairedVideo` 成对分类。
- iCloud 原件下载进度、随机任务目录和非零资源信息。
- `PHLivePhotoView` 原生预览。
- `PHAssetCreationRequest` 原生写回副本，不修改原件。

`web/` 保留为辅助工具：

- 手机与电脑浏览器上传照片、GIF 或视频；照片可生成静态 JPG 杂志封面。
- 三种结构、MP4/GIF/两者和两档清晰度选择。
- 示例任务、异步进度、最近任务、浏览器预览与保存。
- 局域网手机地址、移动端布局、照片本机 JPEG 准备和 Live Photo 静态降级提示。

## 下一步

在 Mac 安装 XcodeGen，用 `workspace/ios/project.yml` 生成 Xcode 工程，选择开发 Team 和唯一 Bundle ID，并连接真实 iPhone 完成“原生选择 → 成对读取 → 原生预览 → 写回副本 → 相册重新读取”闭环。通过后实现逐帧杂志渲染和新的 Live Photo 元数据，而不是继续扩展网站桥接流程。
