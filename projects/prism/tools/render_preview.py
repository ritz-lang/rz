#!/usr/bin/env python3
"""
Prism Text Rendering Preview

This script simulates Prism's text rendering pipeline using the same
font file and similar logic to produce a preview image.

Dependencies: pip install pillow fonttools

Usage: python tools/render_preview.py
Output: output/text_preview.png
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Please install Pillow: pip install pillow")
    sys.exit(1)

# Configuration
WIDTH = 800
HEIGHT = 400
BACKGROUND = (30, 30, 40)  # Dark blue-gray
FONT_PATH = "../angelo/tests/fixtures/aadhunik.ttf"

def main():
    # Create output directory
    os.makedirs("output", exist_ok=True)

    # Create image with dark background
    img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(img)

    # Try to load the font
    font_path = os.path.join(os.path.dirname(__file__), "..", FONT_PATH)
    if not os.path.exists(font_path):
        # Try alternate path
        font_path = os.path.join(os.path.dirname(__file__), "..", "..", "angelo", "tests", "fixtures", "aadhunik.ttf")

    if not os.path.exists(font_path):
        print(f"Font not found at {font_path}")
        print("Using default font instead")
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
    else:
        print(f"Using font: {font_path}")
        font_large = ImageFont.truetype(font_path, 48)
        font_medium = ImageFont.truetype(font_path, 32)
        font_small = ImageFont.truetype(font_path, 20)

    # Render various text samples
    y = 40

    # Title
    draw.text((40, y), "Prism Display Server", fill=(255, 200, 100), font=font_large)
    y += 70

    # Subtitle
    draw.text((40, y), "Text Rendering Preview", fill=(200, 200, 200), font=font_medium)
    y += 50

    # Separator line
    draw.line([(40, y), (WIDTH - 40, y)], fill=(80, 80, 100), width=2)
    y += 30

    # Different colors
    colors = [
        ((255, 100, 100), "Red text"),
        ((100, 255, 100), "Green text"),
        ((100, 100, 255), "Blue text"),
        ((255, 255, 100), "Yellow text"),
        ((255, 100, 255), "Magenta text"),
        ((100, 255, 255), "Cyan text"),
    ]

    x = 40
    for color, label in colors:
        draw.text((x, y), label, fill=color, font=font_small)
        x += 120
        if x > WIDTH - 150:
            x = 40
            y += 30

    y += 50

    # Separator
    draw.line([(40, y), (WIDTH - 40, y)], fill=(80, 80, 100), width=2)
    y += 30

    # ASCII art style text (simulating terminal output)
    draw.text((40, y), "Terminal Output:", fill=(150, 150, 150), font=font_small)
    y += 30

    terminal_text = [
        "$ prism --version",
        "Prism Display Server v0.1.0",
        "$ ls -la",
        "drwxr-xr-x  5 aaron  staff   160 Feb 14 10:30 .",
        "drwxr-xr-x  8 aaron  staff   256 Feb 14 09:15 ..",
        "-rw-r--r--  1 aaron  staff  4096 Feb 14 10:30 main.ritz",
    ]

    for line in terminal_text:
        if line.startswith("$"):
            draw.text((40, y), line, fill=(100, 255, 100), font=font_small)
        else:
            draw.text((40, y), line, fill=(200, 200, 200), font=font_small)
        y += 25

    # Add a rectangle to show compositing
    draw.rectangle([(WIDTH - 200, 50), (WIDTH - 50, 150)], outline=(100, 150, 255), width=2)
    draw.text((WIDTH - 190, 60), "Widget", fill=(100, 150, 255), font=font_small)
    draw.text((WIDTH - 190, 90), "Area", fill=(100, 150, 255), font=font_small)

    # Save the image
    output_path = os.path.join(os.path.dirname(__file__), "..", "output", "text_preview.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"Saved preview to: {output_path}")

    # Also save as PPM (the format Prism will use)
    ppm_path = os.path.join(os.path.dirname(__file__), "..", "output", "text_preview.ppm")
    img.save(ppm_path, "PPM")
    print(f"Saved PPM to: {ppm_path}")

    return output_path

if __name__ == "__main__":
    output = main()
    print(f"\nOpen with: open {output}")
