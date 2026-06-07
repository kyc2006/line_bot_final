from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import tempfile
import textwrap
import zlib
from pathlib import Path

import requests


LINE_API_BASE = "https://api.line.me/v2/bot"
RICH_MENU_SIZE = {"width": 2500, "height": 1686}
DEFAULT_IMAGE_PATH = Path(__file__).resolve().parents[1] / "assets" / "rich_menu.png"
LABELS = [
    "查公車",
    "找 YouBike",
    "查停車場",
    "我的訂閱",
    "服務狀態",
    "使用說明",
]


def build_rich_menu() -> dict:
    return {
        "size": RICH_MENU_SIZE,
        "selected": True,
        "name": "taichung-traffic-main-menu",
        "chatBarText": "台中交通小幫手",
        "areas": [
            _area(0, 0, 833, 843, "查公車"),
            _area(833, 0, 834, 843, "找 YouBike"),
            _area(1667, 0, 833, 843, "查停車場"),
            _area(0, 843, 833, 843, "我的訂閱"),
            _area(833, 843, 834, 843, "服務狀態"),
            _area(1667, 843, 833, 843, "使用說明"),
        ],
    }


def _area(x: int, y: int, width: int, height: int, text: str) -> dict:
    return {
        "bounds": {"x": x, "y": y, "width": width, "height": height},
        "action": {"type": "message", "text": text},
    }


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_rich_menu(token: str, rich_menu: dict) -> str:
    response = requests.post(
        f"{LINE_API_BASE}/richmenu",
        headers={**_headers(token), "Content-Type": "application/json"},
        json=rich_menu,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["richMenuId"]


def upload_image(token: str, rich_menu_id: str, image_path: Path) -> None:
    content_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    with image_path.open("rb") as file:
        response = requests.post(
            f"{LINE_API_BASE}/richmenu/{rich_menu_id}/content",
            headers={**_headers(token), "Content-Type": content_type},
            data=file,
            timeout=30,
        )
    response.raise_for_status()


def set_default(token: str, rich_menu_id: str) -> None:
    response = requests.post(
        f"{LINE_API_BASE}/user/all/richmenu/{rich_menu_id}",
        headers=_headers(token),
        timeout=20,
    )
    response.raise_for_status()


def ensure_rich_menu_image(image_path: Path) -> Path:
    if image_path.exists():
        return image_path
    generate_rich_menu_image(image_path)
    return image_path


def generate_rich_menu_image(image_path: Path) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _generate_with_swift(image_path)
    except Exception:
        try:
            _generate_with_pillow(image_path)
        except Exception:
            _generate_plain_png(image_path)


def _generate_with_swift(image_path: Path) -> None:
    swift_code = textwrap.dedent(
        """
        import AppKit

        let outputPath = CommandLine.arguments[1]
        let width: CGFloat = 2500
        let height: CGFloat = 1686
        let image = NSImage(size: NSSize(width: width, height: height))

        func color(_ hex: UInt32) -> NSColor {
            let r = CGFloat((hex >> 16) & 0xFF) / 255.0
            let g = CGFloat((hex >> 8) & 0xFF) / 255.0
            let b = CGFloat(hex & 0xFF) / 255.0
            return NSColor(calibratedRed: r, green: g, blue: b, alpha: 1.0)
        }

        func drawText(_ text: String, x: CGFloat, y: CGFloat, width: CGFloat, size: CGFloat, weight: NSFont.Weight, fill: NSColor) {
            let paragraph = NSMutableParagraphStyle()
            paragraph.alignment = .left
            paragraph.lineBreakMode = .byWordWrapping
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: size, weight: weight),
                .foregroundColor: fill,
                .paragraphStyle: paragraph
            ]
            (text as NSString).draw(in: NSRect(x: x, y: y, width: width, height: size * 2.4), withAttributes: attrs)
        }

        image.lockFocusFlipped(true)
        color(0xEAF3FF).setFill()
        NSRect(x: 0, y: 0, width: width, height: height).fill()
        color(0x1E3A5F).setFill()
        NSRect(x: 0, y: 0, width: width, height: 220).fill()

        drawText("台中交通小幫手", x: 88, y: 44, width: 900, size: 92, weight: .bold, fill: .white)
        drawText("公車｜YouBike｜停車｜訂閱｜服務", x: 88, y: 145, width: 900, size: 38, weight: .medium, fill: color(0xDBEAFE))

        let tiles: [(CGFloat, CGFloat, CGFloat, CGFloat, UInt32, String, String)] = [
            (0, 220, 833, 733, 0x2563EB, "查公車", "輸入 300 查到站"),
            (833, 220, 834, 733, 0x0F766E, "找 YouBike", "查可借與可還"),
            (1667, 220, 833, 733, 0xB45309, "查停車場", "看剩餘車位"),
            (0, 953, 833, 733, 0x475569, "我的訂閱", "管理常用路線"),
            (833, 953, 834, 733, 0x2563EB, "服務狀態", "查看資料來源"),
            (1667, 953, 833, 733, 0x475569, "使用說明", "快速上手")
        ]

        for tile in tiles {
            let (x, y, w, h, accent, title, subtitle) = tile
            let card = NSBezierPath(roundedRect: NSRect(x: x + 28, y: y + 28, width: w - 56, height: h - 56), xRadius: 34, yRadius: 34)
            NSColor.white.setFill()
            card.fill()
            color(0xC7D2FE).setStroke()
            card.lineWidth = 4
            card.stroke()

            let mark = NSBezierPath(roundedRect: NSRect(x: x + 84, y: y + 104, width: 166, height: 166), xRadius: 30, yRadius: 30)
            color(accent).setFill()
            mark.fill()
            drawText(title, x: x + 84, y: y + 352, width: w - 168, size: 82, weight: .bold, fill: color(0x0F172A))
            drawText(subtitle, x: x + 84, y: y + 450, width: w - 168, size: 42, weight: .medium, fill: color(0x64748B))
            color(accent).setFill()
            NSRect(x: x + 84, y: y + 545, width: w - 168, height: 14).fill()
        }

        image.unlockFocus()

        guard let tiffData = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData),
              let pngData = bitmap.representation(using: .png, properties: [:]) else {
            fatalError("Unable to render rich menu PNG")
        }
        try pngData.write(to: URL(fileURLWithPath: outputPath))
        """
    )
    with tempfile.NamedTemporaryFile("w", suffix=".swift", delete=False) as file:
        file.write(swift_code)
        swift_path = Path(file.name)
    try:
        subprocess.run(
            ["swift", str(swift_path), str(image_path)],
            check=True,
            timeout=45,
            capture_output=True,
            text=True,
        )
    finally:
        swift_path.unlink(missing_ok=True)
    if not image_path.exists():
        raise RuntimeError("Swift renderer did not create the rich menu image.")


def _generate_with_pillow(image_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width = RICH_MENU_SIZE["width"]
    height = RICH_MENU_SIZE["height"]
    image = Image.new("RGB", (width, height), "#EAF3FF")
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width, height)], fill="#EAF3FF")
    draw.rectangle([(0, 0), (width, 220)], fill="#1E3A5F")

    title_font = _font(ImageFont, 92)
    label_font = _font(ImageFont, 82)
    hint_font = _font(ImageFont, 38)
    draw.text((88, 56), "台中交通小幫手", fill="#FFFFFF", font=title_font)
    draw.text((88, 158), "公車｜YouBike｜停車｜訂閱｜服務", fill="#DBEAFE", font=hint_font)

    tiles = [
        (0, 220, 833, 733, "#FFFFFF", "#2563EB", "BUS"),
        (833, 220, 834, 733, "#FFFFFF", "#0F766E", "BIKE"),
        (1667, 220, 833, 733, "#FFFFFF", "#B45309", "P"),
        (0, 953, 833, 733, "#FFFFFF", "#475569", "SUB"),
        (833, 953, 834, 733, "#FFFFFF", "#2563EB", "OK"),
        (1667, 953, 833, 733, "#FFFFFF", "#475569", "?"),
    ]
    for index, (x, y, w, h, fill, accent, icon) in enumerate(tiles):
        draw.rounded_rectangle(
            [(x + 28, y + 28), (x + w - 28, y + h - 28)],
            radius=34,
            fill=fill,
            outline="#C7D2FE",
            width=4,
        )
        draw.rounded_rectangle(
            [(x + 84, y + 104), (x + 250, y + 270)],
            radius=30,
            fill=accent,
        )
        draw.text((x + 115, y + 152), icon, fill="#FFFFFF", font=hint_font)
        draw.text((x + 84, y + 360), LABELS[index], fill="#0F172A", font=label_font)
        draw.rectangle([(x + 84, y + 480), (x + w - 84, y + 494)], fill=accent)

    image.save(image_path, format="PNG", optimize=True)


def _font(image_font, size: int):
    for path in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        try:
            return image_font.truetype(path, size=size)
        except Exception:
            pass
    return image_font.load_default()


def _generate_plain_png(image_path: Path) -> None:
    width = RICH_MENU_SIZE["width"]
    height = RICH_MENU_SIZE["height"]
    tile_specs = [
        (0, 220, 833, 733, (255, 255, 255), (37, 99, 235)),
        (833, 220, 834, 733, (255, 255, 255), (15, 118, 110)),
        (1667, 220, 833, 733, (255, 255, 255), (180, 83, 9)),
        (0, 953, 833, 733, (255, 255, 255), (71, 85, 105)),
        (833, 953, 834, 733, (255, 255, 255), (37, 99, 235)),
        (1667, 953, 833, 733, (255, 255, 255), (71, 85, 105)),
    ]
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            color = (234, 243, 255)
            if y < 220:
                color = (30, 58, 95)
            for tx, ty, tw, th, fill, accent in tile_specs:
                if tx + 28 <= x < tx + tw - 28 and ty + 28 <= y < ty + th - 28:
                    color = fill
                if tx + 84 <= x < tx + tw - 84 and ty + 480 <= y < ty + 494:
                    color = accent
                if tx + 84 <= x < tx + 250 and ty + 104 <= y < ty + 270:
                    color = accent
            row.extend(color)
        rows.append(b"\x00" + bytes(row))

    raw = b"".join(rows)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    for chunk_type, data in (
        (b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
        (b"IDAT", zlib.compress(raw, 9)),
        (b"IEND", b""),
    ):
        png.extend(struct.pack(">I", len(data)))
        png.extend(chunk_type)
        png.extend(data)
        png.extend(struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF))
    image_path.write_bytes(bytes(png))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the LINE Rich Menu for 台中交通小幫手.")
    parser.add_argument("--apply", action="store_true", help="Create the rich menu through LINE API.")
    parser.add_argument(
        "--image",
        type=Path,
        default=DEFAULT_IMAGE_PATH,
        help="PNG/JPEG rich menu image to upload. Default: assets/rich_menu.png",
    )
    parser.add_argument("--set-default", action="store_true", help="Set the created rich menu as default.")
    args = parser.parse_args()

    rich_menu = build_rich_menu()
    image_path = ensure_rich_menu_image(args.image)
    if not args.apply:
        print(json.dumps(rich_menu, ensure_ascii=False, indent=2))
        print(f"\nRich menu image: {image_path}")
        print("\nDry run only. Add --apply to create this rich menu.")
        return

    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("LINE_CHANNEL_ACCESS_TOKEN is required.")
    rich_menu_id = create_rich_menu(token, rich_menu)
    print(f"Created rich menu: {rich_menu_id}")

    upload_image(token, rich_menu_id, image_path)
    print(f"Uploaded image: {image_path}")

    if args.set_default:
        set_default(token, rich_menu_id)
        print("Set rich menu as default.")


if __name__ == "__main__":
    main()
