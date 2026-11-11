#!/usr/bin/env python3
"""源图 → iOS AppIcon.appiconset 全套尺寸。

iOS 的三条硬约束：
  1. 必须是正方形 PNG
  2. 图标不能带 alpha 通道（否则 App Store 校验直接拒）
  3. 1024×1024 的 marketing 图标缺了也过不了校验

用法:
  python scripts/make_appicon.py ios_assets/icon_src_1024.png ios_assets/AppIcon.appiconset
"""
import json
import sys
from pathlib import Path

from PIL import Image

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "ios_assets/icon_src_1024.png")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "ios_assets/AppIcon.appiconset")

# (pt, scale, idiom, 文件名)
SPECS = [
    (20.0, 1, "iphone", "Icon-App-20x20@1x.png"),
    (20.0, 2, "iphone", "Icon-App-20x20@2x.png"),
    (20.0, 3, "iphone", "Icon-App-20x20@3x.png"),
    (29.0, 1, "iphone", "Icon-App-29x29@1x.png"),
    (29.0, 2, "iphone", "Icon-App-29x29@2x.png"),
    (29.0, 3, "iphone", "Icon-App-29x29@3x.png"),
    (40.0, 1, "iphone", "Icon-App-40x40@1x.png"),
    (40.0, 2, "iphone", "Icon-App-40x40@2x.png"),
    (40.0, 3, "iphone", "Icon-App-40x40@3x.png"),
    (60.0, 2, "iphone", "Icon-App-60x60@2x.png"),
    (60.0, 3, "iphone", "Icon-App-60x60@3x.png"),
    (76.0, 1, "ipad", "Icon-App-76x76@1x.png"),
    (76.0, 2, "ipad", "Icon-App-76x76@2x.png"),
    (83.5, 2, "ipad", "Icon-App-83.5x83.5@2x.png"),
    (1024.0, 1, "ios-marketing", "Icon-App-1024x1024@1x.png"),
]


def fmt(v: float) -> str:
    """83.5 要写成 83.5，20.0 要写成 20。"""
    return str(int(v)) if float(v).is_integer() else str(v)


def main() -> int:
    if not SRC.exists():
        print(f"源图不存在: {SRC}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    src = Image.open(SRC)
    if src.mode != "RGBA":
        src = src.convert("RGBA")

    # 去 alpha：叠到与主界面一致的深色底上，结果转成纯 RGB
    flat = Image.new("RGB", src.size, (14, 14, 18))
    flat.paste(src, mask=src.split()[-1])

    images = []
    for pt, scale, idiom, name in SPECS:
        px = int(round(pt * scale))
        icon = flat.resize((px, px), Image.LANCZOS)
        if icon.mode != "RGB":
            icon = icon.convert("RGB")
        icon.save(OUT / name, "PNG", optimize=True)
        images.append(
            {
                "filename": name,
                "idiom": idiom,
                "scale": f"{scale}x",
                "size": f"{fmt(pt)}x{fmt(pt)}",
            }
        )
        print(f"{name:34s} {px}x{px}")

    contents = {"images": images, "info": {"author": "xcode", "version": 1}}
    (OUT / "Contents.json").write_text(
        json.dumps(contents, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Contents.json written  ({len(images)} 张图)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
