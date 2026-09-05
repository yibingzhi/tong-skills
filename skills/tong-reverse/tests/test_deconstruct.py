#!/usr/bin/env python3
"""Unit tests for tong-reverse deconstruct engine."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from deconstruct import analyze_image, build_contact_sheet, deconstruct_video, find_ffmpeg, get_video_metadata


class TestDeconstruct(unittest.TestCase):
    def test_analyze_image(self):
        with tempfile.TemporaryDirectory(prefix="tong-reverse-img-") as tmp:
            tmp_path = Path(tmp)
            img_path = tmp_path / "test_16_9.png"
            img = Image.new("RGB", (1920, 1080), (255, 120, 20))
            img.save(img_path)

            res = analyze_image(img_path)
            self.assertEqual(res["aspect_ratio"], "16:9")
            self.assertEqual(res["ar_flag"], "--ar 16:9")
            self.assertEqual(res["width"], 1920)
            self.assertEqual(res["height"], 1080)
            self.assertIn("warm", res["tone_estimate"])

    def test_find_ffmpeg(self):
        ffmpeg_bin = find_ffmpeg()
        self.assertTrue(bool(ffmpeg_bin), "ffmpeg should be discoverable on test machine")

    def test_build_contact_sheet(self):
        with tempfile.TemporaryDirectory(prefix="tong-reverse-test-") as tmp:
            tmp_path = Path(tmp)
            frames = []
            for i in range(4):
                p = tmp_path / f"frame_{i}.png"
                img = Image.new("RGB", (320, 240), (i * 50, 100, 150))
                img.save(p)
                frames.append((p, float(i)))

            meta = {"width": 320, "height": 240, "fps": 24.0, "duration": 3.0}
            out_sheet = tmp_path / "contact_sheet.png"
            sheet = build_contact_sheet(frames, meta, out_sheet, cols=2)
            self.assertTrue(sheet.is_file())
            with Image.open(sheet) as res:
                self.assertGreater(res.width, 320)
                self.assertGreater(res.height, 240)

    def test_synthetic_video_pipeline(self):
        ffmpeg_bin = find_ffmpeg()
        if not ffmpeg_bin:
            self.skipTest("ffmpeg not available")

        with tempfile.TemporaryDirectory(prefix="tong-reverse-vid-") as tmp:
            tmp_path = Path(tmp)
            video_file = tmp_path / "synthetic.mp4"
            # Generate 1.5s synthetic test video
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f", "lavfi",
                "-i", "testsrc=duration=1.5:size=320x240:rate=24",
                "-pix_fmt", "yuv420p",
                str(video_file)
            ]
            res = subprocess.run(cmd, capture_output=True)
            self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))

            out_dir = tmp_path / "out_frames"
            data = deconstruct_video(video_file, out_dir=out_dir, num_frames=4)
            self.assertTrue(Path(data["first_frame"]).is_file())
            self.assertTrue(Path(data["last_frame"]).is_file())
            self.assertTrue(Path(data["contact_sheet"]).is_file())
            self.assertEqual(len(data["sample_frames"]), 4)


if __name__ == "__main__":
    unittest.main()
