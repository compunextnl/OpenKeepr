#!/usr/bin/env python3
"""Generate the Open Graph share image as a PNG.

Most social platforms (Facebook, LinkedIn, WhatsApp, iMessage, Slack, Discord,
Telegram, Mastodon) reject SVG for OpenGraph previews — they want PNG/JPEG. We
ship one of each: the SVG at ``app/static/img/og-image.svg`` is the source of
truth for the design; this script renders an equivalent PNG using Pillow so the
preview actually shows up everywhere.

Usage::

    python scripts/generate_og_image.py

Run after editing branding (logo, tagline, colours). Commit the resulting PNG.

The output is 1200×630, the canonical OpenGraph size; Twitter/X uses the same
file via ``summary_large_image``.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUTPUT = Path(__file__).resolve().parent.parent / "app" / "static" / "img" / "og-image.png"
WIDTH, HEIGHT = 1200, 630


# ──────────────────────────────────────────────────────────────────────────────
# Colour palette (matches app/static/css/app.css light tokens)
# ──────────────────────────────────────────────────────────────────────────────

BG_TOP    = (247, 246, 255)   # var(--bg-1)
BG_BOTTOM = (253, 251, 248)   # var(--bg-2)
INK_DARK  = (14,  16,  36)    # var(--ink-1)
INK_SOFT  = (56,  59,  84)    # var(--ink-2)

AURORA_1 = (199, 201, 255, 200)  # soft indigo (top-left)
AURORA_2 = (255, 210, 236, 180)  # soft pink (top-right)
AURORA_3 = (185, 240, 234, 160)  # mint (bottom-right)

# Brand gradient stops (left → right)
BRAND_STOPS = [
    (0.00, (106, 107, 255)),
    (0.60, (157, 107, 255)),
    (1.00, (255, 123, 205)),
]


def _vertical_gradient(width: int, height: int, top, bottom) -> Image.Image:
    """Return a vertical RGB gradient from `top` to `bottom`."""
    base = Image.new("RGB", (width, height), top)
    pixels = base.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        r = round(top[0] * (1 - t) + bottom[0] * t)
        g = round(top[1] * (1 - t) + bottom[1] * t)
        b = round(top[2] * (1 - t) + bottom[2] * t)
        for x in range(width):
            pixels[x, y] = (r, g, b)
    return base


def _add_aurora_blob(canvas: Image.Image, center_xy, radius: int, rgba) -> None:
    """Paint a soft radial-gradient blob (in-place, alpha-composited)."""
    cx, cy = center_xy
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Filled circle that we'll blur into a soft glow.
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=rgba)
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.55))
    canvas.alpha_composite(layer)


def _hgradient_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    stops,
) -> Image.Image:
    """Render `text` filled with a horizontal gradient defined by `stops`.

    `stops` is a list of (position, (r, g, b)) tuples; position is in 0..1.
    """
    # 1) Render the text in white on a transparent canvas, sized to fit.
    bbox = font.getbbox(text)
    pad_x, pad_y = 4, 4
    w = bbox[2] - bbox[0] + pad_x * 2
    h = bbox[3] - bbox[1] + pad_y * 2
    text_layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(text_layer).text((-bbox[0] + pad_x, -bbox[1] + pad_y),
                                    text, fill=255, font=font)

    # 2) Build the gradient strip.
    gradient = Image.new("RGB", (w, h))
    grad_px = gradient.load()
    for x in range(w):
        t = x / max(w - 1, 1)
        # Find surrounding stops.
        prev = stops[0]
        nxt = stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                prev, nxt = stops[i], stops[i + 1]
                break
        span = nxt[0] - prev[0] or 1
        local_t = (t - prev[0]) / span
        r = round(prev[1][0] * (1 - local_t) + nxt[1][0] * local_t)
        g = round(prev[1][1] * (1 - local_t) + nxt[1][1] * local_t)
        b = round(prev[1][2] * (1 - local_t) + nxt[1][2] * local_t)
        for y in range(h):
            grad_px[x, y] = (r, g, b)

    # 3) Mask the gradient by the text alpha.
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(gradient, mask=text_layer)
    return out


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try a sequence of common system fonts; fall back to Pillow's default."""
    candidates_bold = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    candidates_reg = [
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans.ttf",
    ]
    for path in (candidates_bold if bold else candidates_reg):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def main() -> None:
    # ── Background gradient ──────────────────────────────────────────────
    bg = _vertical_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM).convert("RGBA")

    # ── Aurora highlights ────────────────────────────────────────────────
    _add_aurora_blob(bg, (180,  130), 320, AURORA_1)
    _add_aurora_blob(bg, (1050,  90), 280, AURORA_2)
    _add_aurora_blob(bg, (1000, 580), 340, AURORA_3)

    draw = ImageDraw.Draw(bg)

    # ── Brand mark (rounded square + checkmark) ──────────────────────────
    mark_x, mark_y, mark = 96, 96, 84
    # Outer rounded rect filled with brand gradient (approximate with mid colour).
    draw.rounded_rectangle(
        (mark_x, mark_y, mark_x + mark, mark_y + mark),
        radius=22, fill=(124, 110, 255, 255),
    )
    # Inner subtle highlight.
    draw.rounded_rectangle(
        (mark_x + 14, mark_y + 14, mark_x + mark - 14, mark_y + mark - 14),
        radius=14, fill=(255, 255, 255, 130),
    )
    # Checkmark.
    cx0, cy0 = mark_x + 22, mark_y + 44
    draw.line([(cx0, cy0), (cx0 + 14, cy0 + 14), (cx0 + 38, cy0 - 14)],
              fill=(86, 84, 232, 255), width=7, joint="curve")

    # ── App name (top, beside the mark) ──────────────────────────────────
    name_font = _load_font(38, bold=True)
    draw.text((mark_x + mark + 18, mark_y + 18), "OpenKeepr",
              fill=INK_DARK, font=name_font)

    # ── Headline ──────────────────────────────────────────────────────────
    h1_font = _load_font(92, bold=True)
    draw.text((96, 250), "Share securely.", fill=INK_DARK, font=h1_font)

    # Gradient second line.
    grad_text = _hgradient_text("Once. Encrypted.", h1_font, BRAND_STOPS)
    bg.alpha_composite(grad_text, (96, 350))

    # ── Tagline ──────────────────────────────────────────────────────────
    tag_font = _load_font(28)
    draw.text((96, 480),
              "End-to-end encrypted in your browser. Zero-knowledge.",
              fill=INK_SOFT, font=tag_font)

    # ── Status pill ──────────────────────────────────────────────────────
    pill_x, pill_y, pill_w, pill_h = 96, 540, 320, 44
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=22, fill=(255, 255, 255, 190),
        outline=(14, 16, 36, 25), width=1,
    )
    # Green dot.
    dot_r = 5
    dot_cx = pill_x + 22
    dot_cy = pill_y + pill_h // 2
    draw.ellipse((dot_cx - dot_r, dot_cy - dot_r,
                  dot_cx + dot_r, dot_cy + dot_r),
                 fill=(16, 185, 129, 255))
    pill_font = _load_font(14, bold=True)
    draw.text((pill_x + 40, pill_y + 13),
              "AES-256-GCM · BROWSER-SIDE",
              fill=INK_SOFT, font=pill_font)

    # ── Save ─────────────────────────────────────────────────────────────
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(OUTPUT, "PNG", optimize=True)
    print(f"wrote {OUTPUT}  ({OUTPUT.stat().st_size:,} bytes, {WIDTH}×{HEIGHT})")


if __name__ == "__main__":
    main()
