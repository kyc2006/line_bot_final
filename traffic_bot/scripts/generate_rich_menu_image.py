from __future__ import annotations

import argparse
import struct
import subprocess
import tempfile
import textwrap
import zlib
from pathlib import Path


RICH_MENU_SIZE = {"width": 2500, "height": 1686}
DEFAULT_IMAGE_PATH = Path(__file__).resolve().parents[1] / "assets" / "rich_menu.png"


def ensure_rich_menu_image(image_path: Path = DEFAULT_IMAGE_PATH) -> Path:
    if not image_path.exists():
        generate_rich_menu_image(image_path)
    return image_path


def generate_rich_menu_image(image_path: Path = DEFAULT_IMAGE_PATH) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _generate_with_swift(image_path)
        return
    except Exception:
        pass

    try:
        _generate_with_pillow(image_path)
        return
    except Exception:
        pass

    _generate_plain_png(image_path)


def _generate_with_swift(image_path: Path) -> None:
    swift_code = textwrap.dedent(
        """
        import AppKit

        let outputPath = CommandLine.arguments[1]
        let width: CGFloat = 2500
        let height: CGFloat = 1686
        let image = NSImage(size: NSSize(width: width, height: height))

        func color(_ hex: UInt32, alpha: CGFloat = 1.0) -> NSColor {
            let r = CGFloat((hex >> 16) & 0xFF) / 255.0
            let g = CGFloat((hex >> 8) & 0xFF) / 255.0
            let b = CGFloat(hex & 0xFF) / 255.0
            return NSColor(calibratedRed: r, green: g, blue: b, alpha: alpha)
        }

        func drawText(
            _ text: String,
            x: CGFloat,
            y: CGFloat,
            width: CGFloat,
            size: CGFloat,
            weight: NSFont.Weight,
            fill: NSColor,
            align: NSTextAlignment = .left
        ) {
            let paragraph = NSMutableParagraphStyle()
            paragraph.alignment = align
            paragraph.lineBreakMode = .byTruncatingTail
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: size, weight: weight),
                .foregroundColor: fill,
                .paragraphStyle: paragraph
            ]
            (text as NSString).draw(
                in: NSRect(x: x, y: y, width: width, height: size * 1.45),
                withAttributes: attrs
            )
        }

        func roundedRect(_ rect: NSRect, radius: CGFloat, fill: NSColor, stroke: NSColor? = nil, lineWidth: CGFloat = 1) {
            let path = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
            fill.setFill()
            path.fill()
            if let strokeColor = stroke {
                strokeColor.setStroke()
                path.lineWidth = lineWidth
                path.stroke()
            }
        }

        func strokeLine(from start: NSPoint, to end: NSPoint, color stroke: NSColor, width: CGFloat) {
            let path = NSBezierPath()
            path.move(to: start)
            path.line(to: end)
            stroke.setStroke()
            path.lineWidth = width
            path.lineCapStyle = .round
            path.stroke()
        }

        func drawBusIcon(x: CGFloat, y: CGFloat, accent: NSColor) {
            roundedRect(NSRect(x: x, y: y, width: 150, height: 150), radius: 36, fill: accent)
            let body = NSBezierPath(roundedRect: NSRect(x: x + 32, y: y + 40, width: 86, height: 62), xRadius: 14, yRadius: 14)
            NSColor.white.setStroke()
            body.lineWidth = 8
            body.stroke()
            strokeLine(from: NSPoint(x: x + 46, y: y + 62), to: NSPoint(x: x + 104, y: y + 62), color: .white, width: 8)
            NSBezierPath(ovalIn: NSRect(x: x + 44, y: y + 98, width: 14, height: 14)).fill()
            NSBezierPath(ovalIn: NSRect(x: x + 92, y: y + 98, width: 14, height: 14)).fill()
        }

        func drawBikeIcon(x: CGFloat, y: CGFloat, accent: NSColor) {
            roundedRect(NSRect(x: x, y: y, width: 150, height: 150), radius: 36, fill: accent)
            NSColor.white.setStroke()
            let left = NSBezierPath(ovalIn: NSRect(x: x + 30, y: y + 82, width: 36, height: 36))
            let right = NSBezierPath(ovalIn: NSRect(x: x + 88, y: y + 82, width: 36, height: 36))
            left.lineWidth = 7
            right.lineWidth = 7
            left.stroke()
            right.stroke()
            strokeLine(from: NSPoint(x: x + 48, y: y + 88), to: NSPoint(x: x + 72, y: y + 54), color: .white, width: 7)
            strokeLine(from: NSPoint(x: x + 72, y: y + 54), to: NSPoint(x: x + 104, y: y + 88), color: .white, width: 7)
            strokeLine(from: NSPoint(x: x + 72, y: y + 54), to: NSPoint(x: x + 84, y: y + 44), color: .white, width: 7)
        }

        func drawLetterIcon(_ letter: String, x: CGFloat, y: CGFloat, accent: NSColor) {
            roundedRect(NSRect(x: x, y: y, width: 150, height: 150), radius: 36, fill: accent)
            drawText(letter, x: x, y: y + 22, width: 150, size: 92, weight: .bold, fill: .white, align: .center)
        }

        func drawListIcon(x: CGFloat, y: CGFloat, accent: NSColor) {
            roundedRect(NSRect(x: x, y: y, width: 150, height: 150), radius: 36, fill: accent)
            for offset in [44.0, 74.0, 104.0] {
                strokeLine(from: NSPoint(x: x + 44, y: y + offset), to: NSPoint(x: x + 108, y: y + offset), color: .white, width: 9)
            }
        }

        func drawStatusIcon(x: CGFloat, y: CGFloat, accent: NSColor) {
            roundedRect(NSRect(x: x, y: y, width: 150, height: 150), radius: 36, fill: accent)
            let circle = NSBezierPath(ovalIn: NSRect(x: x + 38, y: y + 38, width: 74, height: 74))
            NSColor.white.setStroke()
            circle.lineWidth = 8
            circle.stroke()
            strokeLine(from: NSPoint(x: x + 57, y: y + 77), to: NSPoint(x: x + 73, y: y + 93), color: .white, width: 9)
            strokeLine(from: NSPoint(x: x + 73, y: y + 93), to: NSPoint(x: x + 99, y: y + 61), color: .white, width: 9)
        }

        struct Item {
            let title: String
            let subtitle: String
            let message: String
            let accent: UInt32
            let icon: String
        }

        let items = [
            Item(title: "查公車", subtitle: "即時到站", message: "查公車", accent: 0x2563EB, icon: "bus"),
            Item(title: "YouBike", subtitle: "借還資訊", message: "找 YouBike", accent: 0x0F766E, icon: "bike"),
            Item(title: "查停車", subtitle: "剩餘車位", message: "查停車場", accent: 0xC46A1A, icon: "P"),
            Item(title: "我的訂閱", subtitle: "常用路線", message: "我的訂閱", accent: 0x475569, icon: "list"),
            Item(title: "服務狀態", subtitle: "系統資訊", message: "服務狀態", accent: 0x2563EB, icon: "status"),
            Item(title: "使用說明", subtitle: "快速上手", message: "使用說明", accent: 0x475569, icon: "?")
        ]

        image.lockFocusFlipped(true)

        color(0xEEF3F8).setFill()
        NSRect(x: 0, y: 0, width: width, height: height).fill()

        color(0x20385C).setFill()
        NSRect(x: 0, y: 0, width: width, height: 184).fill()
        drawText("台中交通小幫手", x: 84, y: 42, width: 900, size: 78, weight: .bold, fill: .white)
        drawText("公車・YouBike・停車", x: 86, y: 120, width: 700, size: 34, weight: .semibold, fill: color(0xD9E7F7))

        let panel = NSRect(x: 42, y: 222, width: 2416, height: 1390)
        roundedRect(panel, radius: 42, fill: .white, stroke: color(0xD7E2F0), lineWidth: 3)

        let separator = color(0xE3EAF3)
        strokeLine(from: NSPoint(x: 833, y: 222), to: NSPoint(x: 833, y: 1612), color: separator, width: 3)
        strokeLine(from: NSPoint(x: 1667, y: 222), to: NSPoint(x: 1667, y: 1612), color: separator, width: 3)
        strokeLine(from: NSPoint(x: 42, y: 843), to: NSPoint(x: 2458, y: 843), color: separator, width: 3)

        for index in 0..<items.count {
            let item = items[index]
            let col = index % 3
            let row = index / 3
            let cellX = CGFloat(col) * 833.333
            let cellY: CGFloat = row == 0 ? 184 : 843
            let contentTop = row == 0 ? 292.0 : 1012.0
            let iconX = cellX + 88.0
            let titleY = contentTop + 210.0
            let accent = color(item.accent)

            switch item.icon {
            case "bus":
                drawBusIcon(x: iconX, y: contentTop, accent: accent)
            case "bike":
                drawBikeIcon(x: iconX, y: contentTop, accent: accent)
            case "list":
                drawListIcon(x: iconX, y: contentTop, accent: accent)
            case "status":
                drawStatusIcon(x: iconX, y: contentTop, accent: accent)
            default:
                drawLetterIcon(item.icon, x: iconX, y: contentTop, accent: accent)
            }

            drawText(item.title, x: cellX + 88.0, y: titleY, width: 640, size: 86, weight: .bold, fill: color(0x111827))
            drawText(item.subtitle, x: cellX + 90.0, y: titleY + 94.0, width: 560, size: 40, weight: .semibold, fill: color(0x667085))
            color(item.accent).setFill()
            NSRect(x: cellX + 88.0, y: titleY + 168.0, width: 104, height: 10).fill()
        }

        image.unlockFocus()

        guard let tiffData = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData),
              let pngData = bitmap.representation(using: .png, properties: [:]) else {
            fatalError("Unable to render PNG")
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
    _normalize_png_size(image_path)


def _png_size(image_path: Path) -> tuple[int, int]:
    with image_path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file.")
    return struct.unpack(">II", header[16:24])


def _normalize_png_size(image_path: Path) -> None:
    expected = (RICH_MENU_SIZE["width"], RICH_MENU_SIZE["height"])
    if _png_size(image_path) == expected:
        return
    subprocess.run(
        ["sips", "-z", str(expected[1]), str(expected[0]), str(image_path)],
        check=True,
        timeout=30,
        capture_output=True,
        text=True,
    )
    if _png_size(image_path) != expected:
        raise RuntimeError("Unable to normalize rich menu image size.")


def _generate_with_pillow(image_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width = RICH_MENU_SIZE["width"]
    height = RICH_MENU_SIZE["height"]
    image = Image.new("RGB", (width, height), "#EEF3F8")
    draw = ImageDraw.Draw(image)
    title_font = _font(ImageFont, 92)
    label_font = _font(ImageFont, 104)
    subtitle_font = _font(ImageFont, 46)

    draw.rectangle([(0, 0), (width, 184)], fill="#20385C")
    draw.text((84, 42), "台中交通小幫手", fill="#FFFFFF", font=title_font)
    draw.text((88, 122), "公車・YouBike・停車", fill="#D9E7F7", font=subtitle_font)

    draw.rounded_rectangle([(42, 222), (2458, 1612)], radius=42, fill="#FFFFFF", outline="#D7E2F0", width=3)
    for x in (833, 1667):
        draw.line([(x, 222), (x, 1612)], fill="#E3EAF3", width=3)
    draw.line([(42, 843), (2458, 843)], fill="#E3EAF3", width=3)

    items = [
        ("查公車", "即時到站", "#2563EB"),
        ("YouBike", "借還資訊", "#0F766E"),
        ("查停車", "剩餘車位", "#C46A1A"),
        ("我的訂閱", "常用路線", "#475569"),
        ("服務狀態", "系統資訊", "#2563EB"),
        ("使用說明", "快速上手", "#475569"),
    ]
    for index, (title, subtitle, accent) in enumerate(items):
        col = index % 3
        row = index // 3
        cell_x = int(col * 833.333)
        content_top = 292 if row == 0 else 1012
        draw.rounded_rectangle([(cell_x + 88, content_top), (cell_x + 238, content_top + 150)], radius=36, fill=accent)
        draw.text((cell_x + 88, content_top + 210), title, fill="#111827", font=label_font)
        draw.text((cell_x + 90, content_top + 304), subtitle, fill="#667085", font=subtitle_font)
        draw.rectangle([(cell_x + 88, content_top + 378), (cell_x + 192, content_top + 388)], fill=accent)

    image.save(image_path, format="PNG", optimize=True)


def _font(image_font, size: int):
    for name in ("PingFang TC", "Noto Sans CJK TC", "Microsoft JhengHei", "Arial Unicode MS"):
        try:
            return image_font.truetype(name, size=size)
        except Exception:
            pass
    return image_font.load_default()


def _generate_plain_png(image_path: Path) -> None:
    width = RICH_MENU_SIZE["width"]
    height = RICH_MENU_SIZE["height"]
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            color = (238, 243, 248)
            if y < 184:
                color = (32, 56, 92)
            elif 42 <= x < 2458 and 222 <= y < 1612:
                color = (255, 255, 255)
                if x in range(831, 836) or x in range(1665, 1670) or y in range(841, 846):
                    color = (227, 234, 243)
                cell_col = min(2, x // 833)
                cell_row = 0 if y < 843 else 1
                cell_x = int(cell_col * 833.333)
                content_top = 292 if cell_row == 0 else 1012
                accents = [
                    (37, 99, 235),
                    (15, 118, 110),
                    (196, 106, 26),
                    (71, 85, 105),
                    (37, 99, 235),
                    (71, 85, 105),
                ]
                accent = accents[cell_row * 3 + cell_col]
                if cell_x + 88 <= x < cell_x + 238 and content_top <= y < content_top + 150:
                    color = accent
                if cell_x + 88 <= x < cell_x + 192 and content_top + 378 <= y < content_top + 388:
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
    parser = argparse.ArgumentParser(description="Generate assets/rich_menu.png for LINE Rich Menu.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_IMAGE_PATH,
        help="Output PNG path. Default: assets/rich_menu.png",
    )
    args = parser.parse_args()
    generate_rich_menu_image(args.output)
    print(f"Generated rich menu image: {args.output}")
    print(f"Size: {RICH_MENU_SIZE['width']}x{RICH_MENU_SIZE['height']} px")


if __name__ == "__main__":
    main()
