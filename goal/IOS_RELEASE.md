# iOS App 上线指南

> 当前定位：后续预案。项目先用手机可访问的本地网站验证上传、动态杂志渲染、输出与分享效果；验证通过后再启动本方案。

本预案目标是：真实 iPhone 可从系统照片资料库选择原生 Live Photo，完成动态杂志封面生成，并通过 App Store 安装正式版本。

## 一、上线前准备

1. 准备一台能够运行当前稳定版 Xcode 的 Mac，并使用真实 iPhone 完成 Live Photo 调试。
2. 注册 [Apple Developer Program](https://developer.apple.com/programs/)。个人或组织均可发布；主体名称、银行、税务和联系方式按实际运营者填写。
3. 在 Apple Developer 后台创建唯一 Bundle ID，例如 `com.yourcompany.photomanager`，不要在代码中使用临时测试标识。
4. 在 [App Store Connect](https://appstoreconnect.apple.com/) 创建 App 记录，确定不可随意更换的名称、主语言、Bundle ID 和 SKU。
5. 准备支持网站、隐私政策网址、客服邮箱、App 图标、截图、简介、关键词、年龄分级和审核说明。
6. 确定云端部署区域、对象存储、AI 服务、内容安全、删除期限和服务协议。密钥只保存在服务端，不能写入 App 或提交到 GitHub。
7. 面向中国大陆运营时，按实际上线地区和服务内容核验 ICP/APP 备案、算法或生成式 AI 服务要求、生成合成内容标识、个人信息保护和跨境传输要求。

Apple 计划费用、可用能力和审核政策会调整，提交时以 Apple 后台和最新审核指南为准。

## 二、iOS 工程与权限配置

- 首发建议使用 Swift、SwiftUI、PhotoKit、AVFoundation/AVKit 和 URLSession 后台传输。
- `Info.plist` 必须按实际能力配置 `NSPhotoLibraryUsageDescription` 和 `NSPhotoLibraryAddUsageDescription`；文案明确解释读取 Live Photo 是为了取得静态照片和配对视频并生成动态封面。
- 优先使用系统照片选择器和有限照片权限，只读取用户明确选择的资产；拒绝权限后仍能查看示例和已下载作品。
- PhotoKit 读取同一 `PHAsset` 的静态照片资源和 `.pairedVideo`，iCloud 资源显示真实下载进度并允许取消。
- 保存 MP4/GIF/JPG 时只请求必要的写入能力。用户撤销权限后，App 不崩溃、不循环弹窗，并提供系统设置入口。
- 生产、预发布和开发环境分离；生产接口只允许 HTTPS，证书校验、用户隔离、短期签名下载和服务端鉴权必须启用。
- 崩溃日志、分析统计和第三方 SDK 必须进入隐私清单与 App Store 隐私问卷，未使用的数据不得勾选或采集。

## 三、提交前真机验收

至少覆盖：

- 不同受支持 iPhone 型号、本地 Live Photo、仅在 iCloud 的 Live Photo、横竖屏和不同原始编码。
- 完整照片＋配对 MOV、资源缺失/损坏、iCloud 断网、下载取消、本机空间不足和低电量模式。
- 完整照片权限、有限照片权限、拒绝权限、授权后撤销权限、只允许新增照片。
- Live Photo→MP4/GIF/JPG、视频→MP4/GIF/JPG、GIF→MP4/GIF/JPG。
- App 前后台切换、进程被系统终止、上传中断、重复点击、任务恢复和旧结果不覆盖新编辑。
- 导出前后分辨率、帧率、码率、色彩、方向、首尾帧、GIF 多帧和文件大小。
- 从系统相册重新打开导出文件，并用测试微信账号实际发布到测试朋友圈后回看平台压缩和裁切。
- 删除账号、删除任务、云端原素材到期清理、结果到期清理和跨用户越权测试。

## 四、TestFlight 测试

1. 在 Xcode 中选择正式 Team、Bundle ID 和发布签名，使用 Release 配置归档。
2. 通过 Xcode Organizer 上传构建到 App Store Connect。
3. 填写出口合规、隐私清单等构建信息，先添加内部测试员。
4. 内部测试稳定后创建外部测试组；外部 TestFlight 首个构建需要 Beta App Review。
5. 给测试员提供明确任务：导入真实 Live Photo、生成三版候选、导出三种格式、保存相册、实际发布和删除数据。
6. 把崩溃率、生成成功率、清晰度、耗时、失败原因和测试设备写入发布验收记录。

## 五、提交 App Store 审核

1. 在 App Store Connect 选择已上传构建并填写版本说明。
2. 完成 App Privacy 问卷，申报照片/视频、用户内容、标识符、诊断数据及第三方 SDK 的真实处理方式。
3. 上传符合设备要求的真实截图和可选预览视频，不能把尚未实现的 Live Photo 输出或自动发朋友圈写进宣传材料。
4. 在审核说明中写清：如何选择 Live Photo、为何需要照片权限、如何触发生成、预计等待时间、如何删除素材；需要登录时提供长期有效的审核账号。
5. 若 App 支持创建账号，必须在 App 内提供账号删除入口。若出售数字功能或订阅，按 Apple 规则接入 In-App Purchase。
6. 提交审核。被拒后根据具体条款修改功能、元数据、权限说明或审核路径，重新上传更高构建号。
7. 审核通过后选择手动、自动或分阶段发布；首版建议手动发布，便于先确认生产后端和客服值守。

## 六、常见审核风险

- 照片权限说明模糊，或申请整个相册权限却只需要系统选择器。
- 审核人员无法获得真实可用结果，生成任务一直等待、测试账号失效或服务端地区不可达。
- 宣称“支持 Live Photo”，实际只上传静态首帧或已导出普通视频。
- 隐私政策、App Privacy 问卷、第三方 SDK 和实际网络请求不一致。
- AI 生成或合成内容缺少适用的内容审核、举报处理和标识。
- 宣称可以自动发布朋友圈，或把系统分享面板误称为发布成功。
- 使用无商业授权字体、杂志 Logo、图片、音乐或模板资产。
- 账号体系没有 App 内删除入口，或订阅/数字功能绕开 In-App Purchase。

## 七、发布后

- 先做线上冒烟测试：Live Photo 导入、iCloud 下载、上传、生成、三种输出、保存、分享、恢复和删除。
- 监控崩溃、卡死、任务失败率、渲染耗时、存储清理和内容安全告警。
- 首版保留可远程关闭高成本或故障模板的功能开关，但不能远程下发绕过审核的新功能代码。
- 每次提交、TestFlight 和正式发布都在 `mission/README.md` 记录版本号、构建号、Git 提交、审核结果与发布时间。

## 八、官方入口

- [Apple Developer Program](https://developer.apple.com/programs/)
- [App Store Connect](https://appstoreconnect.apple.com/)
- [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Submitting apps to the App Store](https://developer.apple.com/app-store/submitting/)
- [TestFlight](https://developer.apple.com/testflight/)
- [PhotoKit](https://developer.apple.com/documentation/photokit)
- [App privacy details](https://developer.apple.com/app-store/app-privacy-details/)
