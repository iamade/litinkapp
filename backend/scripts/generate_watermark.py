"""
Generate the composite LitInkAI watermark image.

Creates a ~300x80px transparent PNG with the LitInkAI logo icon
and "LitInkAI" text side by side at 70% opacity.

Usage:
    python backend/scripts/generate_watermark.py
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)

LOGO_PATH = os.path.join(REPO_ROOT, "frontend", "public", "litink.png")
OUTPUT_PATH = os.path.join(BACKEND_DIR, "static", "assets", "watermark.png")

# Config
LOGO_SIZE = 80
TEXT = "LitInkAI"
OPACITY = 0.7  # 70%
PADDING = 12  # space between logo and text
FONT_SIZE = 48


def find_font():
    """Try to find a clean system font, fall back to Pillow default."""
    # (path, index) — TTC files need a font index
    candidates = [
        ("/System/Library/Fonts/Helvetica.ttc", 1),       # Helvetica Bold
        ("/System/Library/Fonts/Avenir Next.ttc", 1),      # Avenir Next Demi Bold
        ("/System/Library/Fonts/Helvetica.ttc", 0),        # Helvetica Regular
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
    ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, FONT_SIZE, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


def generate():
    if not os.path.exists(LOGO_PATH):
        print(f"ERROR: Logo not found at {LOGO_PATH}")
        sys.exit(1)

    # Load and resize logo
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)

    # Apply opacity to logo
    r, g, b, a = logo.split()
    a = a.point(lambda x: int(x * OPACITY))
    logo = Image.merge("RGBA", (r, g, b, a))

    # Measure text
    font = find_font()
    temp_img = Image.new("RGBA", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    text_bbox = temp_draw.textbbox((0, 0), TEXT, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # Calculate canvas size
    canvas_w = LOGO_SIZE + PADDING + text_w + 4  # small right margin
    canvas_h = max(LOGO_SIZE, text_h + 8)

    # Create transparent canvas
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Paste logo (vertically centered)
    logo_y = (canvas_h - LOGO_SIZE) // 2
    canvas.paste(logo, (0, logo_y), logo)

    # Draw text (vertically centered next to logo)
    draw = ImageDraw.Draw(canvas)
    text_x = LOGO_SIZE + PADDING
    text_y = (canvas_h - text_h) // 2 - text_bbox[1]  # offset for font baseline
    text_alpha = int(255 * OPACITY)
    draw.text((text_x, text_y), TEXT, fill=(255, 255, 255, text_alpha), font=font)

    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    canvas.save(OUTPUT_PATH, "PNG")
    print(f"Watermark saved: {canvas_w}x{canvas_h}px -> {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)} bytes)")


if __name__ == "__main__":
    generate()
