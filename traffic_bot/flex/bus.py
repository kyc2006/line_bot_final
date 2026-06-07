from __future__ import annotations

from flex.common import action_buttons, info_row
from utils.time_format import display_time


def _direction_label(item: dict) -> str:
    destination = item.get("destination")
    if destination:
        return f"往 {destination}"
    direction = item.get("direction") or ""
    return str(direction)


def _status_color(arrival_text: str) -> str:
    if "即將" in arrival_text:
        return "#DC2626"
    if "約" in arrival_text:
        return "#0F766E"
    if "末班" in arrival_text or "未營運" in arrival_text:
        return "#64748B"
    if "尚未" in arrival_text:
        return "#B45309"
    return "#2563EB"


def bus_eta_bubble(route: str, arrivals: list[dict], limit: int = 6) -> dict:
    shown = arrivals[:limit]
    update_time = display_time(shown[0].get("update_time", "") if shown else "")
    direction = _direction_label(shown[0]) if shown else ""

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F766E",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": f"🚌 {route} 公車即時到站",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                    "wrap": True,
                },
                *(
                    [
                        {
                            "type": "text",
                            "text": direction,
                            "size": "sm",
                            "color": "#CCFBF1",
                            "margin": "sm",
                            "wrap": True,
                        }
                    ]
                    if direction
                    else []
                ),
                {
                    "type": "text",
                    "text": f"更新於 {update_time}｜資料來源：TDX",
                    "size": "xs",
                    "color": "#ECFEFF",
                    "margin": "sm",
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [_stop_card(item) for item in shown],
        },
        "footer": action_buttons(
            [
                ("重新整理", route, "primary"),
                ("訂閱路線", f"訂閱{route}", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def bus_eta_carousel(route: str, arrivals: list[dict], limit: int = 6) -> dict:
    return {
        "type": "carousel",
        "contents": [bus_eta_bubble(route, arrivals, limit=limit)],
    }


def _stop_card(item: dict) -> dict:
    arrival_text = str(item.get("arrival_text") or "資料更新中")
    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": f"📍 {item.get('stop_name') or '站牌'}",
                    "weight": "bold",
                    "size": "md",
                    "color": "#0F172A",
                    "wrap": True,
                    "flex": 4,
                },
                {
                    "type": "text",
                    "text": arrival_text,
                    "size": "sm",
                    "weight": "bold",
                    "align": "end",
                    "color": _status_color(arrival_text),
                    "wrap": True,
                    "flex": 2,
                },
            ],
        },
    ]
    detail_rows = [
        info_row("路線", item.get("route_name")),
        info_row("方向", _direction_label(item)),
        info_row("到站", arrival_text),
        info_row("狀態", item.get("stop_status")),
    ]
    contents.extend(row for row in detail_rows if row)

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
