# 动态杂志视觉样片

本目录使用用户提供的 4.10 秒夜间篮球视频，验证同一真实动作能否被编辑成三种明显不同的动态杂志结构。

## 直接查看

用浏览器打开 `index.html`，可以同时循环查看三版 H.264 样片。若浏览器限制本地媒体，进入本目录后启动：

```bash
python3 -m http.server 8000
```

然后访问 <http://127.0.0.1:8000/>。

三版分别为：

1. `01_motion_cover.mp4`：先锋全出血动态封面。
2. `02_break_frame.mp4`：斜切破版基线；当前只验证非矩形切面和图文层级，尚未进行人物分割。
3. `03_time_slices.mp4`：启动、突破、出手三个时间相位共同构图。

封面与并排对比图位于 `outputs/`。

## GIF 动态图片输入验证

`inputs/basketball_motion_test.gif` 是从原视频制作的真实 49 帧 GIF，不是改后缀的 MP4。它用于验证：

```text
GIF 原文件 → 多帧解码 → 保持原尺寸的无损 4:4:4 / 30 fps 时间轴
→ 各版式从源尺寸直接完成一次目标裁切/缩放 → 无损 4:4:4 版式母版 → H.264 MP4 / GIF + JPG 封面
```

浏览器对比页同时显示原始 GIF、GIF 输出和 MP4 输出。复现命令：

```bash
.venv/bin/python render_demo.py \
  --source inputs/basketball_motion_test.gif \
  --output-dir outputs-gif \
  --variant time-slices \
  --format both \
  --quality high
```

替换 `--source` 就可以测试自己的 GIF。当前“动态图片”明确指 GIF；APNG、动态 WebP 和手机 Live Photo 尚未纳入这条验证链路。

## 重新生成

需要 Python 3、FFmpeg 以及可显示中文的 Noto CJK 字体。没有系统 FFmpeg 时可以使用：

```bash
python3 -m venv .venv
.venv/bin/pip install imageio-ffmpeg==0.5.1
.venv/bin/python render_demo.py
```

也可以显式传入 FFmpeg：

```bash
python3 render_demo.py --ffmpeg /absolute/path/to/ffmpeg
```

更换输入视频：

```bash
python3 render_demo.py --source /absolute/path/to/input.mp4
```

输入 GIF 时，脚本会先保留原文件完成多帧解码，再转换为保持原尺寸的 4.10 秒 FFV1 无损 4:4:4 临时时间轴。视频和 GIF 的每个版式分支随后直接从源尺寸按最终视窗宽高比居中裁切并缩放一次，不先统一放大后再次缩小；同一版式渲染为 FFV1 无损 4:4:4 母版，再分别编码 MP4、GIF 和 JPG，避免 GIF 输入或输出在最终交付前增加一次 H.264 有损压缩。演示版取开头 4.10 秒；正式产品将按主体焦点裁切，并采用短 GIF 整段使用、长 GIF 推荐高光的策略。

输出格式可以选择：

```bash
# 只输出高清视频
python3 render_demo.py --format mp4 --quality high

# 只输出 GIF 动态图片
python3 render_demo.py --format gif

# 同时输出两种格式
python3 render_demo.py --format both
```

视频输入生成的 GIF 示例位于 `outputs-image/`；GIF 输入生成的 GIF 与 MP4 位于 `outputs-gif/`。

## 清晰度对比

`quality-comparison/` 保留同一封面的标准档和高清档：

- 标准档：H.264 CRF 19，约 2.3 MiB。
- 高清档：无损 4:4:4 版式母版导出 H.264 CRF 14、一次 Lanczos 规范化和轻度锐化，约 4.3 MiB。
- `pixel_comparison.jpg` 放大对比篮筐和人物区域。

高清档可以减少二次编码块和插值模糊，但原片只有 720 × 1280、约 645 kb/s，且存在夜景运动模糊；生成 1080 像素宽版面仍需放大 1.5 倍，无法凭编码恢复拍摄时没有记录的细节。

## 输出规格

- MP4：1080 × 1350、6 秒、30 fps、H.264 High、`yuv420p`、BT.709、`faststart`，默认静音。
- GIF：720 × 900、约 6 秒、15 fps、最多 256 色。
- 两种动态格式均附 1080 × 1350 JPG 封面。
- MP4、GIF 与 JPG 均由同一个无损 4:4:4 版式母版分别编码；视频不经过 GIF，GIF 也不经过有损 MP4。
- 母版统一为 BT.709 limited；GIF 显式转换到 RGB 调色板，JPG 显式转换到常规 JFIF 使用的 BT.601 full，避免不同解码器把矩阵误读后产生色偏。
- GIF 使用受控 Bayer 抖动，在保持 720 × 900、15 fps 和 256 色上限的同时让当前两支样片低于 15 MB。
- 第一帧和结束状态使用同一杂志落版，便于支持循环的播放器连续播放。

## 评价边界

- 原视频为 720 × 1280 HEVC 夜景素材，码率约 645 kb/s，存在运动模糊。本轮适合评价结构、节奏、标题层级和三版差异，不适合作为最终高清画质上限。
- 第二版不应被称为完整“主体破版”；真正让人物越出切面，需要后续增加逐帧主体分割和跟踪蒙版。
- 本地网页的自动循环不代表朋友圈一定自动重播。最终必须把样片保存到 iOS、Android 手机并发布到测试朋友圈回看。
- 当前演示素材为 BT.709、方形像素。正式产品仍需探测并校正非方形像素素材，对 HDR/BT.2020/PQ/HLG 做受控 tone-map，并在 GIF 超过 15 MB 时按“15→12 fps、再降尺寸、或改用 MP4”的顺序让用户选择。
