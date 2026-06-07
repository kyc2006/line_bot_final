from __future__ import annotations

from utils.time_format import display_time


def parking_bubble(lots: list[dict], query: str = "", limit: int = 6) -> dict:
    shown = lots[:limit]
    update_time = display_time(shown[0].get("update_time", "") if shown else "")
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
                    "text": f"更新於 {update_time}｜資料來源：{shown[0].get('source', 'TDX') if shown else 'TDX'}",
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
            "contents": [_lot_card(lot) for lot in shown],
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                _button("重新查詢", f"{query}停車場" if query else "停車場"),
                _button("附近停車", "停車"),
                _button("主選單", "主選單"),
            ],
        },
    }


def _lot_card(lot: dict) -> dict:
    status = lot.get("status_text", "資料更新中")
    color = "#0F766E"
    if status == "車位緊張":
        color = "#B45309"
    elif status == "已滿":
        color = "#DC2626"

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
                "text": lot.get("name", "未提供名稱"),
                "weight": "bold",
                "size": "md",
                "color": "#0F172A",
                "wrap": True,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"剩餘 {lot.get('available_spaces', '未提供')}",
                        "weight": "bold",
                        "size": "lg",
                        "color": color,
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": status,
                        "size": "sm",
                        "align": "end",
                        "color": color,
                        "flex": 1,
                    },
                ],
            },
            {
                "type": "text",
                "text": f"總車位：{lot.get('total_spaces', '未提供')}",
                "size": "xs",
                "color": "#475569",
            },
            {
                "type": "text",
                "text": lot.get("address", "地址資料更新中"),
                "size": "xs",
                "color": "#64748B",
                "wrap": True,
            },
            {
                "type": "text",
                "text": f"收費：{lot.get('fare_description', 'TDX 尚未提供此欄位')}",
                "size": "xs",
                "color": "#64748B",
                "wrap": True,
            },
            {
                "type": "text",
                "text": f"營業時間：{lot.get('open_time', 'TDX 尚未提供此欄位')}",
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
