from __future__ import annotations

from flex.common import action_buttons, has_value, info_row, info_text
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
        "footer": action_buttons(
            [
                ("重新查詢", f"{query}停車場" if query else "停車場", "primary"),
                ("換個區域", "換個區域", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def _lot_card(lot: dict) -> dict:
    status = lot.get("status_text", "")
    color = "#0F766E"
    if status == "車位緊張":
        color = "#B45309"
    elif status == "已滿":
        color = "#DC2626"

    contents = [
        {
            "type": "text",
            "text": lot.get("name", "停車場"),
            "weight": "bold",
            "size": "md",
            "color": "#0F172A",
            "wrap": True,
        }
    ]

    if isinstance(lot.get("available_spaces"), int):
        contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"剩餘 {lot['available_spaces']} 格",
                        "weight": "bold",
                        "size": "xl",
                        "color": color,
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": status,
                        "size": "sm",
                        "align": "end",
                        "color": color,
                        "flex": 2,
                        "wrap": True,
                    },
                ],
            }
        )
    elif has_value(status):
        contents.append(
            {
                "type": "text",
                "text": status,
                "weight": "bold",
                "size": "md",
                "color": color,
                "wrap": True,
            }
        )

    for row in (
        info_row("總車位", lot.get("total_spaces")),
        info_row("地址", lot.get("address")),
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
