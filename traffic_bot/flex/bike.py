from __future__ import annotations

from flex.common import action_buttons, info_row
from utils.time_format import display_time


def youbike_bubble(query: str, stations: list[dict], limit: int = 6) -> dict:
    shown = stations[:limit]
    update_time = display_time(shown[0].get("update_time", "")) if shown and shown[0].get("update_time") else ""
    subtitle = "資料來源：TDX"
    if update_time:
        subtitle = f"更新於 {update_time}｜{subtitle}"
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F4C81",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": f"🚲 YouBike {query}",
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
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [_station_card(station) for station in shown],
        },
        "footer": action_buttons(
            [
                ("重新查詢", f"YouBike {query}", "primary"),
                ("換個地點", "換個地點", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def _station_card(station: dict) -> dict:
    status = station.get("status_text", "")
    contents = [
        {
            "type": "text",
            "text": station.get("station_name", "YouBike 站點"),
            "weight": "bold",
            "size": "md",
            "color": "#0F172A",
            "wrap": True,
        },
    ]
    metrics = []
    if station.get("available_rent") is not None:
        metrics.append(_metric("可借", str(station["available_rent"]), "#0F766E"))
    if station.get("available_return") is not None:
        metrics.append(_metric("可還", str(station["available_return"]), "#2563EB"))
    if metrics:
        contents.append({"type": "box", "layout": "horizontal", "contents": metrics})
    for row in (
        info_row("狀態", status),
        info_row("容量", station.get("capacity")),
        info_row("地址", station.get("address")),
    ):
        if row:
            contents.append(row)

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


def _metric(label: str, value: str, color: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "flex": 1,
        "contents": [
            {"type": "text", "text": label, "size": "xs", "color": "#64748B"},
            {"type": "text", "text": value, "size": "xl", "weight": "bold", "color": color},
        ],
    }
