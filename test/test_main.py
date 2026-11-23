#!/usr/bin/env python3
"""Tests for the news-image-20261123 entry.

Run from the entry directory:  python3 -m unittest discover -s test -v
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY_DIR = os.path.dirname(HERE)
sys.path.insert(0, ENTRY_DIR)

import main as entry_main  # noqa: E402

TRAP_PHRASES = [
    "COP31", "CHAPO", "IRAN", "BAHRAIN", "FIDE", "HORMUZ", "BENGHAZI",
    "DYMER", "CIKANDE", "LIVERPOOL", "SHURI", "BEPICOLOMBO", "MYANMAR",
    "SHENZHEN", "GTA",
]

EXPECTED_HEADLINES = [
    "INDIA DECLARE 720/9",
    "NZ 157/4 AT LUNCH, DAY 5",
    "UK TO HOST 2035",
    "WOMEN'S WORLD CUP",
    "DEMOCRATS CLINCH",
    "HOUSE MAJORITY",
    "YOUTH CONGRESS",
    "PROTESTS META",
    "NINE SHOT AT",
    "CALIFORNIA CONCERT",
    "MAN FOUND AFTER",
    "11 DAYS IN AMAZON",
]


def decode_png(data):
    """Decode a filter-0 truecolour PNG into (width, height, pixels)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    idat = bytearray()
    width = height = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", chunk[:10])
            assert depth == 8 and ctype == 2, "expected 8-bit RGB"
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break
        pos += 12 + length
    raw = zlib.decompress(bytes(idat))
    stride = width * 3 + 1
    assert len(raw) == stride * height, "unexpected IDAT length"
    pixels = bytearray()
    for y in range(height):
        row = raw[y * stride:(y + 1) * stride]
        assert row[0] == 0, "expected filter 0"
        pixels += row[1:]
    return width, height, pixels


def pixel(pixels, width, x, y):
    off = (y * width + x) * 3
    return tuple(pixels[off:off + 3])


def count_ink(pixels, width, rect, background):
    """Pixels in *rect* that differ from *background*."""
    x0, y0, x1, y1 = rect
    count = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pixel(pixels, width, x, y) != background:
                count += 1
    return count


class TestEntry(unittest.TestCase):
    def test_png_dimensions_and_size(self):
        data = entry_main.render_png_bytes()
        self.assertLessEqual(len(data), 1048576, "entry.png over 1 MiB")
        width, height, _ = decode_png(data)
        self.assertEqual((width, height), (1024, 1024))

    def test_determinism(self):
        first = entry_main.render_png_bytes()
        second = entry_main.render_png_bytes()
        self.assertEqual(first, second, "two renders differ")

    def test_masthead_and_six_stories_present(self):
        self.assertEqual(len(entry_main.STORIES), 6)
        self.assertEqual(entry_main.MASTHEAD, "MONDAY - 23 NOVEMBER 2026")
        with open(os.path.join(ENTRY_DIR, "main.py")) as fh:
            source = fh.read()
        self.assertIn("MONDAY - 23 NOVEMBER 2026", source)
        for headline in EXPECTED_HEADLINES:
            self.assertIn(headline, source, "missing headline: %s" % headline)

    def test_no_trap_stories(self):
        joined = " ".join(
            s["kicker"] + " " + " ".join(s["lines"]) + " " + s["detail"]
            for s in entry_main.STORIES
        ).upper()
        for trap in TRAP_PHRASES:
            self.assertNotIn(trap, joined, "trap story present: %s" % trap)

    def test_all_panels_render_ink(self):
        data = entry_main.render_png_bytes()
        width, height, pixels = decode_png(data)
        self.assertEqual((width, height), (1024, 1024))
        for story in entry_main.STORIES:
            x, y, w, h = story["rect"]
            ink = count_ink(pixels, width, (x, y, x + w, y + h),
                            entry_main.PAPER)
            self.assertGreater(
                ink, 2000,
                "panel %r looks blank (%d ink pixels)"
                % (story["kicker"], ink))

    def test_detail_lines_render(self):
        """The detail band of every panel must contain ink: this catches
        the lowercase-glyph bug (details are set in capitals)."""
        data = entry_main.render_png_bytes()
        width, _, pixels = decode_png(data)
        for story in entry_main.STORIES:
            x, y, w, h = story["rect"]
            ink = count_ink(pixels, width,
                            (x + 16, y + 106, x + w - 16, y + 146),
                            entry_main.WHITE)
            self.assertGreater(
                ink, 150,
                "detail band of %r looks blank (%d ink pixels)"
                % (story["kicker"], ink))

    def test_masthead_band_is_navy(self):
        data = entry_main.render_png_bytes()
        width, _, pixels = decode_png(data)
        self.assertEqual(pixel(pixels, width, 512, 8), entry_main.NAVY)
        self.assertEqual(pixel(pixels, width, 10, 110), entry_main.NAVY)

    def test_output_dir_env_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, MAKEFUN_OUTPUT_DIR=tmp)
            proc = subprocess.run(
                [sys.executable, os.path.join(ENTRY_DIR, "main.py")],
                env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = os.path.join(tmp, "entry.png")
            self.assertTrue(os.path.exists(out))
            with open(out, "rb") as fh:
                self.assertEqual(fh.read(), entry_main.render_png_bytes())

    def test_grader_like_run_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            out1 = os.path.join(tmp, "out1")
            out2 = os.path.join(tmp, "out2")
            shutil.copytree(ENTRY_DIR, repo,
                            ignore=shutil.ignore_patterns(".git"))
            for root, dirs, files in os.walk(repo):
                for name in dirs:
                    os.chmod(os.path.join(root, name), 0o555)
                for name in files:
                    os.chmod(os.path.join(root, name), 0o444)
            env1 = dict(os.environ, MAKEFUN_OUTPUT_DIR=out1)
            env2 = dict(os.environ, MAKEFUN_OUTPUT_DIR=out2)
            main_py = os.path.join(repo, "main.py")
            proc1 = subprocess.run(
                [sys.executable, "-P", "-s", main_py],
                env=env1, capture_output=True, text=True)
            self.assertEqual(proc1.returncode, 0, proc1.stderr)
            proc2 = subprocess.run(
                [sys.executable, "-P", "-s", main_py],
                env=env2, capture_output=True, text=True)
            self.assertEqual(proc2.returncode, 0, proc2.stderr)
            with open(os.path.join(out1, "entry.png"), "rb") as fh:
                first = fh.read()
            with open(os.path.join(out2, "entry.png"), "rb") as fh:
                second = fh.read()
            self.assertEqual(first, second,
                             "grader-like runs not byte-identical")
            self.assertEqual(first, entry_main.render_png_bytes())


if __name__ == "__main__":
    unittest.main()
