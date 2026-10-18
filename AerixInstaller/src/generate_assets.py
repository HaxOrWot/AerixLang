# -*- coding: utf-8 -*-
"""
generate_assets.py
Generates official multi-resolution Windows .ico files and Inno Setup
branding bitmaps from the Aerix language icon.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

def create_assets():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    installer_dir = os.path.abspath(os.path.join(script_dir, ".."))
    assets_dir = os.path.join(installer_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    root_dir = os.path.abspath(os.path.join(installer_dir, ".."))
    icon_png = os.path.join(root_dir, "editors", "vscode-aerix", "icons", "aerix-icon.png")

    if not os.path.exists(icon_png):
        print(f"[ERROR] Source icon not found at: {icon_png}")
        sys.exit(1)

    print(f"[*] Loading source icon: {icon_png}")
    src_img = Image.open(icon_png).convert("RGBA")

    # Resize to 256x256 base for high-resolution icon generation
    base_256 = src_img.resize((256, 256), Image.Resampling.LANCZOS)

    # 1. Generate aerix.ico (Main app & toolchain icon)
    app_ico_path = os.path.join(assets_dir, "aerix.ico")
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    base_256.save(app_ico_path, format="ICO", sizes=icon_sizes)
    print(f"[OK] Generated: {app_ico_path} with sizes {icon_sizes}")

    # 2. Generate aerix_file.ico (Document icon for .arx files in Windows Explorer)
    # A sleek document badge with subtle border and Aerix supersonic logo centered
    file_doc = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(file_doc)

    # Draw rounded document page background
    doc_bounds = [24, 16, 232, 240]
    draw.rounded_rectangle(doc_bounds, radius=24, fill=(11, 17, 32, 255), outline=(0, 242, 254, 220), width=6)

    # Paste resized Aerix supersonic chevron icon onto document center
    center_logo = src_img.resize((150, 150), Image.Resampling.LANCZOS)
    file_doc.paste(center_logo, (53, 53), mask=center_logo)

    file_ico_path = os.path.join(assets_dir, "aerix_file.ico")
    file_doc.save(file_ico_path, format="ICO", sizes=icon_sizes)
    print(f"[OK] Generated: {file_ico_path} with sizes {icon_sizes}")

    # 3. Generate Inno Setup Wizard Left Sidebar (wizard_side.bmp - 164 x 314 px)
    # Deep midnight gradient with electric cyan accent and Aerix logo
    side_bmp = Image.new("RGB", (164, 314), (11, 17, 32)) # Deep Midnight
    side_draw = ImageDraw.Draw(side_bmp)

    # Decorative top glow accent
    for y in range(40):
        alpha = int(255 * (1.0 - y / 40.0))
        side_draw.line([(0, y), (164, y)], fill=(0, min(242, int(y * 4)), min(254, int(y * 5))))

    # Paste centered Aerix logo
    side_logo = src_img.resize((96, 96), Image.Resampling.LANCZOS)
    # Convert RGBA to RGB composite over background
    temp_canvas = Image.new("RGBA", (164, 314), (11, 17, 32, 255))
    temp_canvas.paste(side_logo, (34, 70), mask=side_logo)
    side_bmp = temp_canvas.convert("RGB")
    side_bmp_path = os.path.join(assets_dir, "wizard_side.bmp")
    side_bmp.save(side_bmp_path, format="BMP")
    print(f"[OK] Generated: {side_bmp_path} (164x314)")

    # 4. Generate Inno Setup Wizard Top Banner (wizard_banner.bmp - 492 x 58 px)
    banner_bmp = Image.new("RGB", (492, 58), (11, 17, 32))
    temp_banner = Image.new("RGBA", (492, 58), (11, 17, 32, 255))
    banner_logo = src_img.resize((46, 46), Image.Resampling.LANCZOS)
    temp_banner.paste(banner_logo, (436, 6), mask=banner_logo)
    banner_bmp = temp_banner.convert("RGB")
    banner_bmp_path = os.path.join(assets_dir, "wizard_banner.bmp")
    banner_bmp.save(banner_bmp_path, format="BMP")
    print(f"[OK] Generated: {banner_bmp_path} (492x58)")

    print("[SUCCESS] All installer graphics & multi-resolution icons generated successfully!")

if __name__ == "__main__":
    create_assets()
