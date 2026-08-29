# 本地网站 MVP v0.9 归档摘要

> 归档日期：2026-08-29
>
> 对应主线末次提交：`2b2dcea`

本地网站阶段验证了手机局域网访问、照片/GIF/视频上传、三种动态杂志版式、FFmpeg 异步渲染、MP4/GIF/JPG 输出、移动端预览与保存指引。

该方案无法通过 Safari PhotoKit 读取同一 `PHAsset` 的静态原图和 `.pairedVideo`，也无法无损地把编辑结果写回为系统原生 Live Photo。用户确认核心体验必须是“直接选择 Live Photo → 输出新的 Live Photo”，因此本地网站不再是首发产品，只保留在 `workspace/web/` 作为视觉样片、FFmpeg 版式和非 Live Photo 输出验证工具。

完整 v0.9 需求和 40 条网站验收标准保留在 Git 历史的 `2b2dcea:goal/README.md`。
