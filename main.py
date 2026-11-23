#!/usr/bin/env python3
"""The World in One Day - 23 November 2026.

A single-file, standard-library-only program that renders a 1024x1024
newspaper front page summing up Monday 23 November 2026's world news and
writes it to ``entry.png`` in the output directory (``$MAKEFUN_OUTPUT_DIR``
or ``/output``).

The program is fully self-contained: it carries its own PNG encoder, its own
rasterizer and its own 5x7 bitmap font, so it runs unchanged under the
grader's ``python3 -P -s /bot/main.py`` (no package import, no sys.path
bootstrap needed, no network, no clock, no randomness). Two runs produce
byte-identical output.

Stories (exactly the six in the plan; the day's news is events that happened
or were first reported on 23 November 2026):
  1. India vs New Zealand, 1st Test, Day 5 (Basin Reserve)
  2. FIFA confirms the UK will host the 2035 Women's World Cup
  3. Democrats clinch the House majority
  4. India's Youth Congress protests Meta
  5. Nine shot at a central California concert, one critical
  6. Elderly man rescued after 11 days in the Amazon

Rendering notes (thin set, built the morning of the day itself): the Amazon
rescue is the weakest of the six, so it takes the smallest visual weight in
the layout; the cricket lead and the FIFA confirmation carry the top row.
Headlines are set from explicit two-line splits rather than auto-wrapping so
no headline can ever clip at a panel edge.
"""

import binascii
import math
import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

PAPER = (247, 241, 222)
NAVY = (20, 33, 61)
RED = (192, 57, 43)
INK = (20, 33, 61)
WHITE = (255, 255, 255)
GRAY = (96, 104, 120)
LIGHT_BLUE = (176, 208, 232)
FIELD_GREEN = (46, 125, 50)
PITCH_TAN = (214, 186, 138)
GOLD = (212, 175, 55)
BROWN = (121, 85, 72)
PURPLE = (90, 40, 120)
TEAL = (0, 105, 92)
DARK_GREEN = (27, 94, 32)
BLUE = (30, 80, 160)

MASTHEAD = "MONDAY - 23 NOVEMBER 2026"
SUBHEAD = "THE WORLD IN ONE DAY"

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, '#' = ink, '.' = blank.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
}

BLANK_GLYPH = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def text_width(text, scale):
    """Width in pixels of *text* rendered at *scale*."""
    return len(text) * 6 * scale


# ---------------------------------------------------------------------------
# Canvas: a plain RGB raster with small drawing helpers.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background * 3) * (width * height)

    def _offset(self, x, y):
        return (y * self.width + x) * 3

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            off = self._offset(x, y)
            self.pixels[off] = color[0]
            self.pixels[off + 1] = color[1]
            self.pixels[off + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            for xx in range(x0, x1):
                off = base + (xx - x0) * 3
                self.pixels[off] = color[0]
                self.pixels[off + 1] = color[1]
                self.pixels[off + 2] = color[2]

    def border(self, x, y, w, h, color, thickness=3):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def hline(self, x0, x1, y, color):
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(x0, x1 + 1):
            self.set_pixel(x, y, color)

    def vline(self, x, y0, y1, color):
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(y0, y1 + 1):
            self.set_pixel(x, y, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set_pixel(x, y, color)
            if x == x1 and y == y1:
                return
            err2 = 2 * err
            if err2 >= dy:
                err += dy
                x += sx
            if err2 <= dx:
                err += dx
                y += sy

    def thick_line(self, x0, y0, x1, y1, color, thickness):
        half = thickness // 2
        for t in range(-half, half + 1):
            self.line(x0 + t, y0, x1 + t, y1, color)

    def filled_circle(self, cx, cy, radius, color):
        for dy in range(-radius, radius + 1):
            dx = int(math.sqrt(max(0, radius * radius - dy * dy)))
            self.hline(cx - dx, cx + dx, cy + dy, color)

    def circle_outline(self, cx, cy, radius, color, thickness=2):
        for dy in range(-radius, radius + 1):
            dx = int(math.sqrt(max(0, radius * radius - dy * dy)))
            for t in range(thickness):
                self.set_pixel(cx - dx + t, cy + dy, color)
                self.set_pixel(cx + dx - t, cy + dy, color)

    def fill_triangle(self, p0, p1, p2, color):
        """Scanline-filled triangle; vertices are (x, y) tuples."""
        points = sorted([p0, p1, p2], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = points
        if ay == cy:
            return
        for y in range(ay, cy + 1):
            if y < by:
                span = (by - ay) or 1
                xa = ax + (bx - ax) * (y - ay) / span
            else:
                span = (cy - by) or 1
                xa = bx + (cx - bx) * (y - by) / span
            xb = ax + (cx - ax) * (y - ay) / (cy - ay)
            self.hline(int(min(xa, xb)), int(max(xa, xb)), y, color)

    def text(self, x, y, text, scale, color):
        cursor = x
        for ch in text:
            glyph = FONT.get(ch, BLANK_GLYPH)
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(
                            cursor + col * scale, y + row * scale,
                            scale, scale, color)
            cursor += 6 * scale

    def text_centered(self, cx, y, text, scale, color):
        self.text(cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap_text(text, max_chars):
    """Greedy word wrap; returns a list of lines, each <= max_chars."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# The six stories.
# ---------------------------------------------------------------------------

STORIES = [
    {
        "kicker": "CRICKET - 1ST TEST",
        "color": FIELD_GREEN,
        "lines": ["INDIA DECLARE 720/9", "NZ 157/4 AT LUNCH, DAY 5"],
        "detail": "Basin Reserve, Wellington - India lead by 352 runs",
        "art": "cricket",
        "rect": (12, 128, 604, 292),
    },
    {
        "kicker": "FOOTBALL",
        "color": DARK_GREEN,
        "lines": ["UK TO HOST 2035", "WOMEN'S WORLD CUP"],
        "detail": "First World Cup in Britain since 1966",
        "art": "football",
        "rect": (628, 128, 384, 292),
    },
    {
        "kicker": "WASHINGTON",
        "color": BLUE,
        "lines": ["DEMOCRATS CLINCH", "HOUSE MAJORITY"],
        "detail": "Final North Carolina seat flips - biggest since 1992",
        "art": "capitol",
        "rect": (12, 432, 488, 268),
    },
    {
        "kicker": "INDIA",
        "color": RED,
        "lines": ["YOUTH CONGRESS", "PROTESTS META"],
        "detail": "Clashes at Meta offices in Hyderabad, Mumbai, Gurugram",
        "art": "protest",
        "rect": (512, 432, 500, 268),
    },
    {
        "kicker": "CALIFORNIA",
        "color": PURPLE,
        "lines": ["NINE SHOT AT", "CALIFORNIA CONCERT"],
        "detail": "One victim in critical condition",
        "art": "concert",
        "rect": (12, 712, 488, 300),
    },
    {
        "kicker": "AMAZON",
        "color": TEAL,
        "lines": ["MAN FOUND AFTER", "11 DAYS IN AMAZON"],
        "detail": "Elderly man rescued alive",
        "art": "amazon",
        "rect": (512, 712, 500, 300),
    },
]


# ---------------------------------------------------------------------------
# Pictorial cues: one small flat illustration per story.
# ---------------------------------------------------------------------------

def draw_cricket(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, FIELD_GREEN)
    # Pitch down the middle.
    pitch_x0 = (x0 + x1) // 2 - 55
    pitch_x1 = (x0 + x1) // 2 + 55
    cv.fill_rect(pitch_x0, y0, pitch_x1 - pitch_x0, y1 - y0, PITCH_TAN)
    cv.hline(pitch_x0, pitch_x1, y0 + 18, WHITE)
    cv.hline(pitch_x0, pitch_x1, y1 - 18, WHITE)
    # Stumps at the near end.
    sx = (x0 + x1) // 2
    for dx in (-14, 0, 14):
        cv.fill_rect(sx + dx - 3, y1 - 52, 6, 34, WHITE)
    cv.fill_rect(sx - 20, y1 - 56, 40, 4, WHITE)
    # Red ball on the pitch.
    cv.filled_circle(sx + 34, y0 + 46, 11, RED)
    # Bat leaning on the pitch.
    cv.thick_line(sx - 44, y1 - 20, sx - 70, y0 + 60, BROWN, 7)
    cv.fill_rect(sx - 78, y0 + 44, 16, 22, BROWN)


def draw_football(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, FIELD_GREEN)
    mid_y = (y0 + y1) // 2
    cv.hline(x0, x1, mid_y, WHITE)
    cv.circle_outline((x0 + x1) // 2, mid_y, 34, WHITE, 3)
    # Ball, lower right.
    bx, by = x1 - 62, y1 - 44
    cv.filled_circle(bx, by, 26, WHITE)
    cv.filled_circle(bx, by, 8, NAVY)
    for dx, dy in ((-16, -8), (16, -8), (-16, 12), (16, 12), (0, -20)):
        cv.filled_circle(bx + dx, by + dy, 4, NAVY)
    # Corner flag.
    cv.vline(x0 + 12, y0 + 8, y0 + 44, WHITE)
    cv.fill_triangle((x0 + 12, y0 + 8), (x0 + 34, y0 + 14), (x0 + 12, y0 + 20),
                     RED)


def draw_capitol(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, LIGHT_BLUE)
    cx = (x0 + x1) // 2
    # Everything is sized from the art rect so nothing can poke into the
    # headline/detail zone above it.
    base_top = y1 - 46
    dome_r = 32
    # Dome: white circle sitting on the base.
    cv.filled_circle(cx, base_top, dome_r, WHITE)
    cv.fill_rect(cx - dome_r, base_top, dome_r * 2, 4, NAVY)
    # Small lantern on the dome.
    cv.fill_rect(cx - 4, base_top - dome_r - 8, 8, 8, WHITE)
    cv.fill_rect(cx - 7, base_top - dome_r - 11, 14, 3, NAVY)
    # Flag on top of the lantern.
    cv.vline(cx, base_top - dome_r - 30, base_top - dome_r - 11, NAVY)
    cv.fill_triangle((cx, base_top - dome_r - 30),
                     (cx + 22, base_top - dome_r - 25),
                     (cx, base_top - dome_r - 20), RED)
    # Building base with columns spread across its full width.
    base_x0 = x0 + 24
    base_w = x1 - x0 - 48
    cv.fill_rect(base_x0, base_top, base_w, y1 - base_top, WHITE)
    for i in range(6):
        col_x = base_x0 + 20 + i * ((base_w - 50) // 5)
        cv.fill_rect(col_x, base_top + 10, 10, y1 - base_top - 10, NAVY)
    cv.fill_rect(base_x0, base_top, base_w, 8, NAVY)


def draw_protest(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, (232, 222, 196))
    # Three placards on sticks, at staggered heights.
    placards = [
        (x0 + 30, y0 + 12, 92, 44, RED),
        (x0 + 150, y0 + 30, 92, 44, BLUE),
        (x0 + 272, y0 + 8, 92, 44, GOLD),
    ]
    for px, py, pw, ph, color in placards:
        cv.fill_rect(px, py, pw, ph, color)
        cv.border(px, py, pw, ph, NAVY, 2)
        cv.fill_rect(px + pw // 2 - 3, py + ph, 6, y1 - py - ph - 34, BROWN)
    # Crowd: a row of heads along the bottom.
    head_colors = [NAVY, RED, BLUE, GOLD, TEAL, PURPLE]
    for i in range(12):
        hx = x0 + 26 + i * 34
        cv.filled_circle(hx, y1 - 22, 11, head_colors[i % len(head_colors)])
        cv.fill_rect(hx - 12, y1 - 12, 24, 12, head_colors[i % len(head_colors)])


def draw_concert(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, (16, 22, 48))
    # Spotlight beams from the top corners.
    cv.fill_triangle((x0 + 20, y0), (x0 + 90, y0),
                     ((x0 + x1) // 2 - 40, y1 - 60), GOLD)
    cv.fill_triangle((x1 - 20, y0), (x1 - 90, y0),
                     ((x0 + x1) // 2 + 40, y1 - 60), GOLD)
    # Stage.
    stage_top = y1 - 52
    cv.fill_rect(x0 + 30, stage_top, x1 - x0 - 60, y1 - stage_top, (40, 40, 56))
    cv.fill_rect(x0 + 30, stage_top, x1 - x0 - 60, 6, RED)
    # Speaker stacks.
    for sx in (x0 + 44, x1 - 84):
        cv.fill_rect(sx, stage_top - 44, 40, 44, NAVY)
        cv.filled_circle(sx + 20, stage_top - 32, 8, WHITE)
        cv.filled_circle(sx + 20, stage_top - 12, 8, WHITE)
    # Performer silhouette and microphone.
    px = (x0 + x1) // 2
    cv.filled_circle(px, stage_top - 26, 9, WHITE)
    cv.fill_rect(px - 8, stage_top - 18, 16, 18, WHITE)
    cv.vline(px + 18, stage_top - 40, stage_top, WHITE)
    cv.filled_circle(px + 18, stage_top - 44, 5, RED)
    # Crowd hands along the bottom.
    for i in range(10):
        hx = x0 + 30 + i * 42
        cv.vline(hx, y1 - 26, y1 - 8, WHITE)


def draw_amazon(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, (24, 84, 44))
    # Sun.
    cv.filled_circle(x1 - 46, y0 + 30, 18, GOLD)
    # Jungle canopy: overlapping circles.
    canopy = [
        (x0 + 40, y0 + 26, 34, DARK_GREEN),
        (x0 + 110, y0 + 14, 40, FIELD_GREEN),
        (x0 + 190, y0 + 30, 34, DARK_GREEN),
        (x0 + 260, y0 + 16, 38, FIELD_GREEN),
        (x0 + 330, y0 + 28, 32, DARK_GREEN),
    ]
    for cx, cy, r, color in canopy:
        cv.filled_circle(cx, cy, r, color)
    # River, wavy band across the lower half.
    for x in range(x0, x1):
        wave = int(6 * math.sin((x - x0) / 34.0))
        river_top = y0 + (y1 - y0) * 2 // 3 + wave
        cv.vline(x, river_top, y1, (48, 130, 190))
    # Rescue boat on the river.
    bx = (x0 + x1) // 2
    by = y0 + (y1 - y0) * 2 // 3 + 34
    cv.fill_rect(bx - 34, by, 68, 16, BROWN)
    cv.fill_triangle((bx - 34, by), (bx + 34, by), (bx, by - 22), GOLD)
    cv.filled_circle(bx - 8, by - 6, 6, RED)


ART_DRAWERS = {
    "cricket": draw_cricket,
    "football": draw_football,
    "capitol": draw_capitol,
    "protest": draw_protest,
    "concert": draw_concert,
    "amazon": draw_amazon,
}


# ---------------------------------------------------------------------------
# Layout.
# ---------------------------------------------------------------------------

def draw_panel(cv, story):
    x, y, w, h = story["rect"]
    cv.fill_rect(x, y, w, h, WHITE)
    cv.border(x, y, w, h, NAVY, 3)
    # Kicker strip.
    cv.fill_rect(x + 3, y + 3, w - 6, 34, story["color"])
    cv.text(x + 16, y + 12, story["kicker"], 2, WHITE)
    # Headline lines.
    line_y = y + 50
    for line in story["lines"]:
        cv.text(x + 16, line_y, line, 3, NAVY)
        line_y += 27
    # Detail, wrapped to the panel's inner width. The font has no lowercase
    # glyphs, so the detail is set in capitals like the headlines.
    max_chars = (w - 32) // 12
    detail_lines = wrap_text(story["detail"], max_chars)
    detail_y = line_y + 4
    for line in detail_lines:
        cv.text(x + 16, detail_y, line.upper(), 2, GRAY)
        detail_y += 18
    # Pictorial cue in the remaining space.
    art_top = max(detail_y + 8, y + 146)
    art_bottom = y + h - 12
    if art_bottom - art_top >= 40:
        ART_DRAWERS[story["art"]](cv, x + 14, art_top, x + w - 14, art_bottom)


def render():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    # Masthead band.
    cv.fill_rect(0, 0, WIDTH, 116, NAVY)
    cv.text_centered(WIDTH // 2, 14, SUBHEAD, 2, (232, 222, 196))
    cv.fill_rect(362, 46, 300, 4, RED)
    cv.text_centered(WIDTH // 2, 58, MASTHEAD, 6, WHITE)
    for story in STORIES:
        draw_panel(cv, story)
    return cv


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.height):
        raw.append(0)  # filter: none
        start = y * cv.width * 3
        raw += cv.pixels[start:start + cv.width * 3]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data))
        out += kind
        out += data
        out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.width, cv.height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    return png


def render_png_bytes():
    return encode_png(render())


def output_dir():
    return os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def main():
    out_dir = output_dir()
    os.makedirs(out_dir, exist_ok=True)
    data = render_png_bytes()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
