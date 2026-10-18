"""
Generate minimalistic, clean, professional file icons for Aerix (.arx).

Design Concept: "Supersonic Duo"
- Letter 'X' formed by two aerodynamic, code-inspired chevrons (< and >) interlocking at the center.
- Left Chevron: Vibrant Electric Aero Cyan (#00DCFF) representing speed, flow, and modern syntax.
- Right Chevron: Royal Azure / Systems Blue (#1E90FF) representing compiled C99 native safety.
- Proportions: Perfectly balanced 60px height within 128px canvas for ideal breathing room in IDE file trees.
- 100% transparent background.
"""

import os
import glob
from PIL import Image, ImageDraw

icons_dir = os.path.join(os.path.dirname(__file__), "..", "editors", "vscode-aerix", "icons")
os.makedirs(icons_dir, exist_ok=True)

# 1. Clean Vector SVG
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <!-- Aerix Language Icon: Supersonic Duo 'X' -->
  <defs>
    <linearGradient id="aerixCyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#00B4D8"/>
    </linearGradient>
    <linearGradient id="aerixAzure" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
  </defs>

  <!-- Right Chevron (Royal Azure): Points inward from right -->
  <path d="M 92 34 L 66 64 L 92 94" 
        fill="none" 
        stroke="url(#aerixAzure)" 
        stroke-width="14" 
        stroke-linecap="round" 
        stroke-linejoin="round"/>

  <!-- Left Chevron (Electric Aero Cyan): Points inward from left -->
  <path d="M 36 34 L 62 64 L 36 94" 
        fill="none" 
        stroke="url(#aerixCyan)" 
        stroke-width="14" 
        stroke-linecap="round" 
        stroke-linejoin="round"/>
</svg>
"""

svg_path = os.path.join(icons_dir, "aerix-icon.svg")
with open(svg_path, "w", encoding="utf-8") as f:
    f.write(svg_content)

# 2. Render pixel-perfect PNG with 4x supersampling (512x512 downsampled to 128x128 and 16x16)
size = 128
scale = 4
canvas_size = size * scale

img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0)) # 100% Transparent
draw = ImageDraw.Draw(img)

cyan_color = (0, 220, 255, 255)   # #00DCFF
azure_color = (30, 144, 255, 255) # #1E90FF
stroke_w = 14 * scale

# Right chevron (Azure)
r_pts = [
    (92 * scale, 34 * scale),
    (66 * scale, 64 * scale),
    (92 * scale, 94 * scale)
]
draw.line(r_pts, fill=azure_color, width=stroke_w, joint="round")
draw.ellipse([(92*scale - stroke_w//2, 34*scale - stroke_w//2), (92*scale + stroke_w//2, 34*scale + stroke_w//2)], fill=azure_color)
draw.ellipse([(92*scale - stroke_w//2, 94*scale - stroke_w//2), (92*scale + stroke_w//2, 94*scale + stroke_w//2)], fill=azure_color)

# Left chevron (Cyan)
l_pts = [
    (36 * scale, 34 * scale),
    (62 * scale, 64 * scale),
    (36 * scale, 94 * scale)
]
draw.line(l_pts, fill=cyan_color, width=stroke_w, joint="round")
draw.ellipse([(36*scale - stroke_w//2, 34*scale - stroke_w//2), (36*scale + stroke_w//2, 34*scale + stroke_w//2)], fill=cyan_color)
draw.ellipse([(36*scale - stroke_w//2, 94*scale - stroke_w//2), (36*scale + stroke_w//2, 94*scale + stroke_w//2)], fill=cyan_color)

# Save 128x128 PNG (for Extension badge / marketplace)
img_128 = img.resize((size, size), Image.Resampling.LANCZOS)
png_path = os.path.join(icons_dir, "aerix-icon.png")
img_128.save(png_path, "PNG")

# Save 16x16 PNG (for VS Code file explorer tab icon)
img_16 = img.resize((16, 16), Image.Resampling.LANCZOS)
png_16_path = os.path.join(icons_dir, "aerix-icon-16.png")
img_16.save(png_16_path, "PNG")

# Clean up test scripts in scripts/ if any
test_script = os.path.join(os.path.dirname(__file__), "test_design.py")
if os.path.exists(test_script):
    try:
        os.remove(test_script)
    except Exception:
        pass

print("Successfully generated minimalist, clean Supersonic Duo icons:")
print(" - SVG (Vector):", svg_path)
print(" - PNG 128x128:", png_path)
print(" - PNG 16x16:", png_16_path)
