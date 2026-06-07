from __future__ import annotations

from flex.common import action_buttons, has_value, info_row, info_text
from utils.time_format import display_time


def parking_bubble(lots: list[dict], query: str = "", limit: int = 6) -> dict:
    shown = [lot for lot in lots if _has_parking_identity(lot)][:limit]
    update_time = display_time(shown[0].get("update_time", "")) if shown and shown[0].get("update_time") else ""
    source = shown[0].get("source", "TDX") if shown else "TDX"
    subtitle = f"資料來源：{source}"
    if update_time:
        subtitle = f"更新於 {update_time}｜{subtitle}"
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1E3A5F",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": "🅿️ 台中停車場空位",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": subtitle,
                    "size": "xs",
                    "color": "#DBEAFE",
                    "margin": "sm",
                    "wrap": True,
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [_lot_card(lot) for lot in shown] or [info_text("目前查不到可用資料，請換個地點或稍後再試。")],
        },
        "footer": action_buttons(
            [
                ("重新查詢", f"{query}停車場" if query else "停車場", "primary"),
                ("換個區域", "換個區域", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def _lot_card(lot: dict) -> dict:
    available_spaces = lot.get("available_spaces")
    status = _display_status(lot)
    color = _status_color(status)

    contents = [
        {
            "type": "text",
            "text": _parking_title(lot),
            "weight": "bold",
            "size": "md",
            "color": "#0F172A",
            "wrap": True,
        }
    ]

    contents.append(_availability_row(available_spaces, status, color))

    for row in (
        info_row("總車位", _total_spaces_text(lot)),
        info_row("地址", lot.get("address")),
        info_row("更新", display_time(lot.get("update_time", "")) if lot.get("update_time") else ""),
        info_row("收費", lot.get("fare_description")),
        info_row("營業時間", lot.get("open_time")),
    ):
        if row:
            contents.append(row)

    if len(contents) == 1:
        contents.append(info_text("目前查不到可用資料，請換個地點或稍後再試。"))

    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": "#E2E8F0",
        "borderWidth": "1px",
        "spacing": "sm",
        "contents": contents,
    }


def _availability_row(available_spaces, status: str, color: str) -> dict:
    primary_text = (
        f"剩餘 {available_spaces} 格"
        if isinstance(available_spaces, int)
        else status if has_value(status) and status != "暫無即時車位"
        else "資料更新中"
    )
    return {
        "type": "box",
        "layout": "horizontal",
        "alignItems": "center",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": primary_text,
                "weight": "bold",
                "size": "xl",
                "color": color,
                "flex": 3,
                "wrap": True,
            },
            _status_badge(status, color),
        ],
    }


def _display_status(lot: dict) -> str:
    available_spaces = lot.get("available_spaces")
    if isinstance(available_spaces, int):
        if available_spaces <= 0:
            return "已滿"
        if available_spaces <= 20:
            return "車位緊張"
        return "尚有車位"
    if has_value(lot.get("status_text")):
        return str(lot["status_text"])
    return "暫無即時車位"


def _status_badge(status: str, color: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": _badge_background(status),
        "cornerRadius": "999px",
        "paddingTop": "4px",
        "paddingBottom": "4px",
        "paddingStart": "8px",
        "paddingEnd": "8px",
        "flex": 0,
        "contents": [
            {
                "type": "text",
                "text": status,
                "size": "xs",
                "weight": "bold",
                "color": color,
                "wrap": False,
            }
        ],
    }


def _status_color(status: str) -> str:
    if status == "車位緊張":
        return "#B45309"
    if status == "已滿":
        return "#DC2626"
    if status == "暫無即時車位":
        return "#475569"
    return "#0F766E"


def _badge_background(status: str) -> str:
    if status == "車位緊張":
        return "#FEF3C7"
    if status == "已滿":
        return "#FEE2E2"
    if status == "暫無即時車位":
        return "#F1F5F9"
    return "#DCFCE7"


def _parking_title(lot: dict) -> str:
    if has_value(lot.get("name")):
        return str(lot["name"])
    if has_value(lot.get("address")):
        return str(lot["address"])
    return "停車場"


def _has_parking_identity(lot: dict) -> bool:
    return has_value(lot.get("name")) or has_value(lot.get("address"))


def _total_spaces_text(lot: dict) -> str:
    total_spaces = lot.get("total_spaces")
    available_spaces = lot.get("available_spaces")
    if not isinstance(total_spaces, int):
        return ""
    if isinstance(available_spaces, int) and total_spaces > 0:
        used_spaces = max(total_spaces - available_spaces, 0)
        usage = round(used_spaces / total_spaces * 100)
        return f"{total_spaces} 格｜使用率 {usage}%"
    return f"{total_spaces} 格"
