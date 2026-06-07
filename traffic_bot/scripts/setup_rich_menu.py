from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests

try:
    from scripts.generate_rich_menu_image import (
        DEFAULT_IMAGE_PATH,
        RICH_MENU_SIZE,
        ensure_rich_menu_image,
        generate_rich_menu_image,
    )
except ModuleNotFoundError:
    from generate_rich_menu_image import (
        DEFAULT_IMAGE_PATH,
        RICH_MENU_SIZE,
        ensure_rich_menu_image,
        generate_rich_menu_image,
    )

LINE_API_BASE = "https://api.line.me/v2/bot"


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
