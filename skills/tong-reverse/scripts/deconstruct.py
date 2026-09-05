#!/usr/bin/env python3
"""
tong-reverse deconstruct engine:
Extracts keyframes, first/last states, and builds a cinematic contact sheet
for multimodal video reverse-engineering.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    common_win = [
        "E:/ffmpeg/bin/ffmpeg.exe",
        "C:/ffmpeg/bin/ffmpeg.exe",
        "C:/Program Files/ffmpeg/bin/ffmpeg.exe",
    ]
    for p in common_win:
        if os.path.isfile(p):
            return p
    return ""


def find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path:
        return path
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        probe_cand = Path(ffmpeg).parent / "ffprobe.exe"
        if probe_cand.is_file():
            return str(probe_cand)
    return ""


def get_video_metadata(video_path: Path) -> Dict[str, float | int | str]:
    ffprobe = find_ffprobe()
    ffmpeg = find_ffmpeg()
    
    meta = {
        "duration": 5.0,
        "width": 1280,
        "height": 720,
        "fps": 24.0,
    }

    if ffprobe:
        try:
            cmd = [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration:stream=width,height,r_frame_rate",
                "-of", "json",
                str(video_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            if "format" in data and "duration" in data["format"]:
                meta["duration"] = float(data["format"]["duration"])
            if "streams" in data and len(data["streams"]) > 0:
                s = data["streams"][0]
                meta["width"] = int(s.get("width", 1280))
                meta["height"] = int(s.get("height", 720))
                r = s.get("r_frame_rate", "24/1")
                if "/" in r:
                    num, den = r.split("/")
                    meta["fps"] = round(float(num) / float(den), 2)
                else:
                    meta["fps"] = float(r)
            return meta
        except Exception:
            pass

    # Fallback to ffmpeg stderr parsing
    if ffmpeg:
        try:
            res = subprocess.run([ffmpeg, "-i", str(video_path)], capture_output=True, text=True, errors="replace")
            out = res.stderr
            d_match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
            if d_match:
                h, m, s = d_match.groups()
                meta["duration"] = int(h) * 3600 + int(m) * 60 + float(s)
            v_match = re.search(r"(\d{3,5})x(\d{3,5})", out)
            if v_match:
                meta["width"] = int(v_match.group(1))
                meta["height"] = int(v_match.group(2))
            fps_match = re.search(r"([\d.]+)\s*fps", out)
            if fps_match:
                meta["fps"] = float(fps_match.group(1))
        except Exception:
            pass

    return meta


def extract_frame_ffmpeg(video_path: Path, timestamp: float, out_path: Path, ffmpeg_bin: str) -> bool:
    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", f"{timestamp:.3f}",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(out_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0 and out_path.is_file()
    except Exception:
        return False


def build_contact_sheet(
    frames_info: List[Tuple[Path, float]],
    meta: Dict[str, float | int | str],
    out_path: Path,
    cols: int = 3,
) -> Path:
    images = []
    for p, _ in frames_info:
        if p.is_file():
            with Image.open(p) as im:
                images.append(im.convert("RGB"))

    if not images:
        raise RuntimeError("No frames extracted to build contact sheet")

    count = len(images)
    rows = (count + cols - 1) // cols

    thumb_w = 480
    thumb_h = int(thumb_w * (images[0].height / images[0].width))

    pad = 16
    header_h = 70
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * thumb_h + (rows + 1) * pad + header_h

    sheet = Image.new("RGB", (sheet_w, sheet_h), (20, 22, 26))
    draw = ImageDraw.Draw(sheet)

    try:
        font_header = ImageFont.truetype("arial.ttf", 20)
        font_badge = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_header = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    # Header title
    title_text = f"TONG-REVERSE: {meta.get('width', 0)}x{meta.get('height', 0)} @ {meta.get('fps', 0)}fps | Duration: {meta.get('duration', 0):.2f}s | {count} Frames"
    draw.text((pad, 18), title_text, fill=(240, 242, 245), font=font_header)
    sub_text = "[TIMELINE CONTACT SHEET: Analyze Camera Vector & Physical Dynamics Delta]"
    draw.text((pad, 42), sub_text, fill=(224, 86, 36), font=font_header)

    for i, (p, ts) in enumerate(frames_info):
        r = i // cols
        c = i % cols
        x = pad + c * (thumb_w + pad)
        y = header_h + pad + r * (thumb_h + pad)

        resized = images[i].resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(resized, (x, y))

        draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(50, 55, 65), width=1)

        badge_str = f" {ts:.2f}s "
        if i == 0:
            badge_str = " [0.00s START / BASE] "
        elif i == count - 1:
            badge_str = f" [{ts:.2f}s END] "

        bb = draw.textbbox((0, 0), badge_str, font=font_badge)
        bw = bb[2] - bb[0] + 8
        bh = bb[3] - bb[1] + 6
        bx = x + 8
        by = y + 8
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=4, fill=(15, 17, 21))
        draw.text((bx + 4, by + 2), badge_str, fill=(245, 166, 35) if i == 0 else (240, 240, 240), font=font_badge)

    sheet.save(out_path, quality=95)
    return out_path


def deconstruct_video(
    video_path: Path | str,
    out_dir: Path | str = "tmp/reverse",
    num_frames: int = 6,
) -> Dict[str, str | float | int | List[str]]:
    v_path = Path(video_path).resolve()
    if not v_path.is_file():
        raise FileNotFoundError(f"Video file not found: {v_path}")

    out_p = Path(out_dir).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        raise RuntimeError(
            "ffmpeg is required for video keyframe extraction.\n"
            "Install ffmpeg: Windows (winget install Gyan.FFmpeg), macOS (brew install ffmpeg), Linux (apt install ffmpeg)."
        )

    meta = get_video_metadata(v_path)
    duration = float(meta["duration"])
    if duration <= 0.2:
        duration = 1.0

    num_frames = max(3, min(12, num_frames))
    timestamps = []
    step = (duration - 0.1) / (num_frames - 1)
    for i in range(num_frames):
        t = min(duration - 0.05, max(0.0, i * step))
        timestamps.append(t)

    extracted_frames: List[Tuple[Path, float]] = []
    frame_paths: List[str] = []

    for idx, t in enumerate(timestamps):
        fname = f"frame_{idx:02d}_{t:.2f}s.png"
        frame_file = out_p / fname
        ok = extract_frame_ffmpeg(v_path, t, frame_file, ffmpeg_bin)
        if ok:
            extracted_frames.append((frame_file, t))
            frame_paths.append(str(frame_file))

    if not extracted_frames:
        raise RuntimeError("Failed to extract any frames from video")

    # 1. Base First Frame
    first_frame_path = out_p / "first_frame.png"
    shutil.copy2(extracted_frames[0][0], first_frame_path)

    # 2. Last Frame
    last_frame_path = out_p / "last_frame.png"
    shutil.copy2(extracted_frames[-1][0], last_frame_path)

    # 3. Contact Sheet
    contact_sheet_path = out_p / "contact_sheet.png"
    cols = 3 if len(extracted_frames) >= 5 else 2
    build_contact_sheet(extracted_frames, meta, contact_sheet_path, cols=cols)

    return {
        "video": str(v_path),
        "duration": duration,
        "width": meta["width"],
        "height": meta["height"],
        "fps": meta["fps"],
        "first_frame": str(first_frame_path),
        "last_frame": str(last_frame_path),
        "contact_sheet": str(contact_sheet_path),
        "sample_frames": frame_paths,
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Deconstruct video into keyframes and contact sheet for reverse prompting.")
    parser.add_argument("--video", help="Path to video file (.mp4, .mov, .webm, etc.)")
    parser.add_argument("--frames", type=int, default=6, help="Number of timeline frames to sample (default: 6)")
    parser.add_argument("--out-dir", default="tmp/reverse", help="Output directory for extracted frames")
    parser.add_argument("--describe", default="", help="Text description of the video when running in text-only mode")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.describe:
        print("=== TONG-REVERSE TEXT MODE ===")
        print("[Scene Description]:", args.describe)
        print("[NOTICE]: For highest precision, provide a video file to a multimodal agent to automatically read camera trajectories.")
        return 0

    if not args.video:
        parser.print_help()
        sys.exit(1)

    try:
        res = deconstruct_video(args.video, out_dir=args.out_dir, num_frames=args.frames)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print("=== TONG-REVERSE DECONSTRUCTION OK ===")
            print(f"Video: {res['video']} ({res['width']}x{res['height']} @ {res['fps']}fps, {res['duration']:.2f}s)")
            print(f"First Frame (Base Image): {res['first_frame']}")
            print(f"Last Frame (End State):   {res['last_frame']}")
            print(f"Contact Sheet:            {res['contact_sheet']}")
            print(f"Sample Frames ({len(res['sample_frames'])}):       {args.out_dir}/")
            print("\n[NEXT STEP FOR AGENT]:")
            print("1. View 'contact_sheet.png' and 'first_frame.png' using vision.")
            print("2. If using a pure text LLM, advise switching to a multimodal model or describe the scene motions.")
            print("3. Output 5-layer reverse prompt protocol: MJ/FLUX First Frame + Kling + Runway + Hailuo.")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
