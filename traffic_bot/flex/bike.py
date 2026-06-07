from __future__ import annotations

from utils.time_format import display_time


def youbike_bubble(query: str, stations: list[dict], limit: int = 6) -> dict:
    shown = stations[:limit]
    update_time = display_time(shown[0].get("update_time", "") if shown else "")
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
                    "text": f"更新於 {update_time}｜資料來源：TDX",
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
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                _button("重新查詢", f"YouBike {query}"),
                _button("其他站點", "YouBike 台中車站"),
                _button("主選單", "主選單"),
            ],
        },
    }


def _station_card(station: dict) -> dict:
    status = station.get("status_text", "資料更新中")
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": "#E2E8F0",
        "borderWidth": "1px",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": station.get("station_name", "未提供站名"),
                "weight": "bold",
                "size": "md",
                "color": "#0F172A",
                "wrap": True,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    _metric("可借", str(station.get("available_rent", 0)), "#0F766E"),
                    _metric("可還", str(station.get("available_return", 0)), "#2563EB"),
                ],
            },
            {
                "type": "text",
                "text": f"狀態：{status}",
                "size": "xs",
                "color": "#475569",
                "wrap": True,
            },
            {
                "type": "text",
                "text": f"容量：{station.get('capacity', 'TDX 尚未提供此欄位')}",
                "size": "xs",
                "color": "#475569",
                "wrap": True,
            },
            {
                "type": "text",
                "text": station.get("address") or "地址資料更新中",
                "size": "xs",
                "color": "#64748B",
                "wrap": True,
            },
        ],
    }


def _button(label: str, text: str) -> dict:
    return {
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "action": {"type": "message", "label": label, "text": text},
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
