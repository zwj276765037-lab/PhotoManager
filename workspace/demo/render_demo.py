#!/usr/bin/env python3
"""Render reproducible AI motion-magazine MP4/GIF demos with FFmpeg."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "60c75319dd1281fef34a4b2f96579cc2.mp4"
OUTPUT_DIR = ROOT / "outputs"
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

WIDTH = 1080
HEIGHT = 1350
DURATION = 6
FPS = 30
STATIC_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SCALE_OPTIONS = (
    "flags=lanczos+accurate_rnd+full_chroma_int:"
    "out_color_matrix=bt709:out_range=tv"
)


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise SystemExit(f"FFmpeg 不存在：{path}")

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise SystemExit(
            "未找到 FFmpeg。请安装系统 FFmpeg，或在虚拟环境执行 "
            "'pip install imageio-ffmpeg==0.5.1'。"
        ) from exc


def run(command: list[str]) -> None:
    print(f"生成：{Path(command[-1]).name}", flush=True)
    subprocess.run(command, check=True)


def render_master(
    ffmpeg: str,
    source: Path,
    output: Path,
    filter_graph: str,
) -> None:
    """Render the design once to a lossless master shared by every export."""
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex_threads",
            "1",
            "-i",
            str(source),
            "-filter_complex",
            filter_graph,
            "-map",
            "[out]",
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-an",
            "-t",
            str(DURATION),
            "-r",
            str(FPS),
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-coder",
            "1",
            "-context",
            "1",
            "-g",
            "1",
            "-slicecrc",
            "1",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv444p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-color_range",
            "tv",
            str(output),
        ]
    )


def encode_video(ffmpeg: str, master: Path, output: Path, quality: str) -> None:
    """Encode a delivery MP4 from the lossless design master."""
    quality_settings = {
        "high": {
            "preset": "slow",
            "crf": "14",
            "maxrate": "12M",
            "bufsize": "24M",
        },
        "standard": {
            "preset": "medium",
            "crf": "19",
            "maxrate": "6M",
            "bufsize": "12M",
        },
    }[quality]
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex_threads",
            "1",
            "-i",
            str(master),
            "-vf",
            (
                "scale=iw:ih:flags=lanczos+accurate_rnd+full_chroma_int:"
                "in_color_matrix=bt709:out_color_matrix=bt709:"
                "in_range=tv:out_range=tv,format=yuv420p"
            ),
            "-map",
            "0:v:0",
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-an",
            "-t",
            str(DURATION),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            quality_settings["preset"],
            "-threads",
            "1",
            "-flags:v",
            "+bitexact",
            "-crf",
            quality_settings["crf"],
            "-maxrate",
            quality_settings["maxrate"],
            "-bufsize",
            quality_settings["bufsize"],
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "60",
            "-keyint_min",
            "60",
            "-sc_threshold",
            "0",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-color_range",
            "tv",
            "-tag:v",
            "avc1",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def export_gif(ffmpeg: str, video: Path, output: Path) -> None:
    """Export a 4:5 animated image with a per-video optimized palette."""
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex_threads",
            "1",
            "-i",
            str(video),
            "-filter_complex",
            (
                "fps=15,scale=720:900:"
                "flags=lanczos+accurate_rnd+full_chroma_int:"
                "in_color_matrix=bt709:in_range=tv:out_range=pc,"
                "format=rgb24,split[g0][g1];"
                "[g0]palettegen=max_colors=256:stats_mode=diff[p];"
                "[g1][p]paletteuse=dither=bayer:bayer_scale=3:"
                "diff_mode=rectangle"
            ),
            "-loop",
            "0",
            "-an",
            str(output),
        ]
    )


def extract_cover(ffmpeg: str, video: Path, cover: Path) -> None:
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-ss",
            "0.05",
            "-i",
            str(video),
            "-vf",
            (
                "scale=iw:ih:flags=lanczos+accurate_rnd+full_chroma_int:"
                "in_color_matrix=bt709:out_color_matrix=bt601:"
                "in_range=tv:out_range=pc,format=yuvj444p"
            ),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-color_range",
            "pc",
            str(cover),
        ]
    )


def normalize_gif(ffmpeg: str, source: Path, output: Path) -> None:
    """Decode a GIF into a lossless 4:4:4 canonical demo timeline."""
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex_threads",
            "1",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-vf",
            (
                "fps=30,scale=iw:ih:"
                "flags=lanczos+accurate_rnd+full_chroma_int:"
                "out_color_matrix=bt709:in_range=pc:out_range=tv,"
                "setsar=1,format=yuv444p"
            ),
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-an",
            "-t",
            "4.10",
            "-r",
            "30",
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-coder",
            "1",
            "-context",
            "1",
            "-g",
            "1",
            "-slicecrc",
            "1",
            "-threads",
            "1",
            "-flags:v",
            "+bitexact",
            "-pix_fmt",
            "yuv444p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-color_range",
            "tv",
            str(output),
        ]
    )


def normalize_static_image(ffmpeg: str, source: Path, output: Path) -> None:
    """Turn a still image into a lossless timeline for magazine composition."""
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex_threads",
            "1",
            "-loop",
            "1",
            "-i",
            str(source),
            "-vf",
            (
                "fps=30,scale=iw:ih:"
                "flags=lanczos+accurate_rnd+full_chroma_int:"
                "out_color_matrix=bt709:in_range=pc:out_range=tv,"
                "setsar=1,format=yuv444p"
            ),
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-an",
            "-t",
            "4.10",
            "-r",
            "30",
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-coder",
            "1",
            "-context",
            "1",
            "-g",
            "1",
            "-slicecrc",
            "1",
            "-threads",
            "1",
            "-flags:v",
            "+bitexact",
            "-pix_fmt",
            "yuv444p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-color_range",
            "tv",
            str(output),
        ]
    )


def create_comparison(ffmpeg: str, covers: list[Path], output: Path) -> None:
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning"]
    for cover in covers:
        command.extend(["-i", str(cover)])
    command.extend(
        [
            "-filter_complex",
            (
                "[0:v]scale=360:450[a];"
                "[1:v]scale=360:450[b];"
                "[2:v]scale=360:450[c];"
                "[a][b][c]hstack=inputs=3[out]"
            ),
            "-map",
            "[out]",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ]
    )
    run(command)


def motion_cover_graph(bold: Path, regular: Path) -> str:
    return f"""
[0:v]fps={FPS},setsar=1,split=2[landing][motion];
[landing]trim=start_frame=88:end_frame=89,setpts=PTS-STARTPTS,
 scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop={WIDTH}:{HEIGHT},
 unsharp=5:5:0.35:5:5:0.0,
 eq=saturation=0.78:contrast=1.10:brightness=-0.05,
 tpad=stop_mode=clone:stop=179,setpts=N/({FPS}*TB),trim=end_frame=180[base];
[motion]trim=start=0:end=4.10,setpts=PTS-STARTPTS,
 scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop={WIDTH}:{HEIGHT},
 unsharp=5:5:0.35:5:5:0.0,
 eq=saturation=1.12:contrast=1.08:brightness=-0.02,
 tpad=start_mode=clone:start_duration=0.35:stop_mode=clone:stop_duration=1.55,
 trim=duration=6,format=rgba,
 fade=t=in:st=0.18:d=0.38:alpha=1,
 fade=t=out:st=5.25:d=0.55:alpha=1[motion_rgba];
[base][motion_rgba]overlay=eof_action=pass:format=yuv444,
 drawbox=x=0:y=0:w=iw:h=270:color=0x081018@0.36:t=fill,
 drawbox=x=0:y=1020:w=iw:h=330:color=0x081018@0.58:t=fill,
 drawbox=x=62:y=52:w=10:h=158:color=0xFF5A36@1:t=fill,
 drawtext=fontfile={bold}:text='人生动刊':fontcolor=0xF7F1E7:fontsize=106:x=92:y=42:
          shadowcolor=black@0.35:shadowx=2:shadowy=2,
 drawtext=fontfile={regular}:text='LIFE IN MOTION':fontcolor=0xF7F1E7:fontsize=28:x=94:y=176,
 drawtext=fontfile={bold}:text='NIGHT GAME':fontcolor=0xF7F1E7:fontsize=104:x=62:y=1012:
          shadowcolor=black@0.45:shadowx=2:shadowy=2,
 drawtext=fontfile={bold}:text='夜色上篮':fontcolor=0xFF5A36:fontsize=70:x=66:y=1136,
 drawtext=fontfile={regular}:text='THE NIGHT HAS ITS OWN RHYTHM':fontcolor=0xF7F1E7:fontsize=23:x=66:y=1244,
 drawtext=fontfile={regular}:text='ISSUE 001  ·  4.10 SEC':fontcolor=0xF7F1E7:fontsize=22:x=764:y=1288,
 drawtext=fontfile={bold}:text='01':fontcolor=white@0.20:fontsize=150:x=875:y=28,
 setsar=1,format=yuv444p[out]
""".replace("\n", "")


def break_frame_graph(bold: Path, regular: Path) -> str:
    return f"""
[0:v]fps={FPS},setsar=1,split=2[landing][motion];
color=c=0xEDE4D6:s={WIDTH}x{HEIGHT}:r={FPS}:d={DURATION},format=yuv444p,
 drawtext=fontfile={bold}:text='07':fontcolor=0x14233C@0.12:fontsize=650:x=28:y=250,
 drawtext=fontfile={bold}:text='BREAK':fontcolor=0x14233C@0.18:fontsize=168:x=48:y=46,
 drawtext=fontfile={bold}:text='THE LINE':fontcolor=0x14233C@0.18:fontsize=134:x=48:y=206,
 format=yuv444p[paper];
[landing]trim=start_frame=88:end_frame=89,setpts=PTS-STARTPTS,
 scale=700:972:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=700:972,
 unsharp=5:5:0.35:5:5:0.0,
 eq=saturation=0.88:contrast=1.10,
 tpad=stop_mode=clone:stop=179,setpts=N/({FPS}*TB),trim=end_frame=180,
 format=rgba,rotate=-7*PI/180:ow=rotw(iw):oh=roth(ih):c=none[landing_panel];
[motion]trim=start=0:end=4.10,setpts=PTS-STARTPTS,
 scale=700:972:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=700:972,
 unsharp=5:5:0.35:5:5:0.0,
 eq=saturation=1.08:contrast=1.08,
 tpad=start_mode=clone:start_duration=0.35:stop_mode=clone:stop_duration=1.55,
 trim=duration=6,format=rgba,
 fade=t=in:st=0.18:d=0.38:alpha=1,
 fade=t=out:st=5.25:d=0.55:alpha=1,
 rotate=-7*PI/180:ow=rotw(iw):oh=roth(ih):c=none[motion_panel];
[paper][landing_panel]overlay=x=300:y=190:eof_action=pass:format=yuv444[with_landing];
[with_landing][motion_panel]overlay=x=300:y=190:eof_action=pass:format=yuv444,
 drawbox=x=58:y=946:w=812:h=172:color=0xF05237@0.96:t=fill,
 drawbox=x=58:y=1124:w=510:h=5:color=0x14233C@1:t=fill,
 drawtext=fontfile={bold}:text='越过边界':fontcolor=0xF8F3EA:fontsize=96:x=88:y=958,
 drawtext=fontfile={bold}:text='BREAK THE LINE':fontcolor=0x14233C:fontsize=42:x=62:y=1152,
 drawtext=fontfile={regular}:text='ACTION STUDY  /  NIGHT COURT':fontcolor=0x14233C:fontsize=23:x=64:y=1212,
 drawtext=fontfile={regular}:text='斜切破版基线  ·  SUBJECT MASK NEXT':fontcolor=0x14233C:fontsize=20:x=64:y=1264,
 drawbox=x=940:y=56:w=78:h=78:color=0x14233C@1:t=fill,
 drawtext=fontfile={bold}:text='02':fontcolor=0xEDE4D6:fontsize=35:x=955:y=72,
 setsar=1,format=yuv444p[out]
""".replace("\n", "")


def time_slices_graph(bold: Path, regular: Path) -> str:
    return f"""
[0:v]fps={FPS},setsar=1,split=6[k1][k2][k3][s1][s2][s3];
color=c=0x0B0D12:s={WIDTH}x{HEIGHT}:r={FPS}:d={DURATION},format=yuv444p,
 drawbox=x=48:y=318:w=320:h=630:color=0xF2EEE5@0.10:t=fill,
 drawbox=x=348:y=238:w=380:h=750:color=0xF2EEE5@0.10:t=fill,
 drawbox=x=738:y=378:w=300:h=580:color=0xF2EEE5@0.10:t=fill,
 format=yuv444p[paper];
[k1]trim=start_frame=14:end_frame=15,setpts=PTS-STARTPTS,
 scale=300:610:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=300:610,
 eq=saturation=0.72:contrast=1.10,
 tpad=stop_mode=clone:stop=179,setpts=N/({FPS}*TB),trim=end_frame=180[k1_card];
[k2]trim=start_frame=54:end_frame=55,setpts=PTS-STARTPTS,
 scale=360:730:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=360:730,
 eq=saturation=0.82:contrast=1.10,
 tpad=stop_mode=clone:stop=179,setpts=N/({FPS}*TB),trim=end_frame=180[k2_card];
[k3]trim=start_frame=88:end_frame=89,setpts=PTS-STARTPTS,
 scale=280:560:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=280:560,
 eq=saturation=0.92:contrast=1.12,
 tpad=stop_mode=clone:stop=179,setpts=N/({FPS}*TB),trim=end_frame=180[k3_card];
[s1]trim=start=0:end=4.10,setpts=PTS-STARTPTS,
 scale=300:610:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=300:610,
 eq=saturation=1.02:contrast=1.08,
 tpad=start_mode=clone:start_duration=0.35:stop_mode=clone:stop_duration=1.55,
 trim=duration=6,format=rgba,
 fade=t=in:st=0.12:d=0.30:alpha=1,fade=t=out:st=5.25:d=0.55:alpha=1[s1_card];
[s2]trim=start=0.55:end=4.10,setpts=PTS-STARTPTS,
 scale=360:730:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=360:730,
 eq=saturation=1.05:contrast=1.08,
 tpad=start_mode=clone:start_duration=0.35:stop_mode=clone:stop_duration=2.10,
 trim=duration=6,format=rgba,
 fade=t=in:st=0.26:d=0.30:alpha=1,fade=t=out:st=5.25:d=0.55:alpha=1[s2_card];
[s3]trim=start=1.10:end=4.10,setpts=PTS-STARTPTS,
 scale=280:560:force_original_aspect_ratio=increase:{SCALE_OPTIONS},
 format=yuv444p,crop=280:560,
 eq=saturation=1.10:contrast=1.10,
 tpad=start_mode=clone:start_duration=0.35:stop_mode=clone:stop_duration=2.65,
 trim=duration=6,format=rgba,
 fade=t=in:st=0.40:d=0.30:alpha=1,fade=t=out:st=5.25:d=0.55:alpha=1[s3_card];
[paper][k1_card]overlay=x=58:y=328:eof_action=pass:format=yuv444[b1];
[b1][k2_card]overlay=x=358:y=248:eof_action=pass:format=yuv444[b2];
[b2][k3_card]overlay=x=748:y=388:eof_action=pass:format=yuv444[b3];
[b3][s1_card]overlay=x=58:y=328:eof_action=pass:format=yuv444[b4];
[b4][s2_card]overlay=x=358:y=248:eof_action=pass:format=yuv444[b5];
[b5][s3_card]overlay=x=748:y=388:eof_action=pass:format=yuv444,
 drawtext=fontfile={bold}:text='TIME IN MOTION':fontcolor=0xF2EEE5:fontsize=70:x=54:y=42,
 drawtext=fontfile={bold}:text='三步  抵达篮下':fontcolor=0xD6FF3F:fontsize=48:x=57:y=126,
 drawtext=fontfile={regular}:text='0.0  →  4.1 SEC':fontcolor=0xF2EEE5:fontsize=24:x=804:y=68,
 drawtext=fontfile={bold}:text='01':fontcolor=0xD6FF3F:fontsize=40:x=58:y=974,
 drawtext=fontfile={regular}:text='启动  START':fontcolor=0xF2EEE5:fontsize=20:x=122:y=990,
 drawtext=fontfile={bold}:text='02':fontcolor=0xD6FF3F:fontsize=40:x=358:y=1014,
 drawtext=fontfile={regular}:text='突破  DRIVE':fontcolor=0xF2EEE5:fontsize=20:x=422:y=1030,
 drawtext=fontfile={bold}:text='03':fontcolor=0xD6FF3F:fontsize=40:x=748:y=982,
 drawtext=fontfile={regular}:text='出手  RELEASE':fontcolor=0xF2EEE5:fontsize=20:x=812:y=998,
 setsar=1,format=yuv444p[out]
""".replace("\n", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ffmpeg", help="FFmpeg 可执行文件路径")
    parser.add_argument("--font-bold", type=Path, default=FONT_BOLD)
    parser.add_argument("--font-regular", type=Path, default=FONT_REGULAR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--format",
        choices=("mp4", "gif", "both", "jpg"),
        default="mp4",
        help="输出 MP4、GIF、JPG 静态封面或同时输出两种动态格式",
    )
    parser.add_argument(
        "--quality",
        choices=("high", "standard"),
        default="high",
        help="MP4 编码质量；默认 high 使用 CRF 14",
    )
    parser.add_argument(
        "--variant",
        choices=("all", "motion-cover", "break-frame", "time-slices"),
        default="all",
        help="只生成指定结构；默认生成全部三版",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"源素材不存在：{source}")
    for font in (args.font_bold, args.font_regular):
        if not font.is_file():
            raise SystemExit(f"字体不存在：{font}")

    ffmpeg = find_ffmpeg(args.ffmpeg)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    variant_map = {
        "motion-cover": (
            "01_motion_cover",
            motion_cover_graph(args.font_bold, args.font_regular),
        ),
        "break-frame": (
            "02_break_frame",
            break_frame_graph(args.font_bold, args.font_regular),
        ),
        "time-slices": (
            "03_time_slices",
            time_slices_graph(args.font_bold, args.font_regular),
        ),
    }
    selected = (
        list(variant_map.values())
        if args.variant == "all"
        else [variant_map[args.variant]]
    )

    with tempfile.TemporaryDirectory(prefix="photomanager-input-") as temp_dir:
        prepared_source = source
        if source.suffix.lower() == ".gif":
            prepared_source = Path(temp_dir) / "normalized-gif-input.mkv"
            normalize_gif(ffmpeg, source, prepared_source)
        elif source.suffix.lower() in STATIC_IMAGE_SUFFIXES:
            prepared_source = Path(temp_dir) / "normalized-static-input.mkv"
            normalize_static_image(ffmpeg, source, prepared_source)

        covers: list[Path] = []
        for name, graph in selected:
            master = Path(temp_dir) / f"{name}-lossless-master.mkv"
            cover = output_dir / f"{name}.jpg"
            render_master(ffmpeg, prepared_source, master, graph)
            extract_cover(ffmpeg, master, cover)
            if args.format in ("mp4", "both"):
                encode_video(
                    ffmpeg,
                    master,
                    output_dir / f"{name}.mp4",
                    args.quality,
                )
            if args.format in ("gif", "both"):
                export_gif(ffmpeg, master, output_dir / f"{name}.gif")
            covers.append(cover)
            master.unlink()

    if len(covers) == 3:
        create_comparison(ffmpeg, covers, output_dir / "comparison.jpg")
    print(f"完成。输出目录：{output_dir}", flush=True)


if __name__ == "__main__":
    main()
