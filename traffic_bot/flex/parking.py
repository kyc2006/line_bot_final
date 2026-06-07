from __future__ import annotations

from flex.common import action_buttons, has_value, info_row, info_text
from utils.time_format import display_time


def parking_bubble(lots: list[dict], query: str = "", limit: int = 6) -> dict:
    shown = lots[:limit]
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
        available_spaces = lot["available_spaces"]
        contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"剩餘 {available_spaces} 格",
                        "weight": "bold",
                        "size": "xl",
                        "color": color,
                        "flex": 3,
                    },
                    *(
                        [
                            {
                                "type": "text",
                                "text": status,
                                "size": "sm",
                                "align": "end",
                                "color": color,
                                "flex": 2,
                                "wrap": True,
                            }
                        ]
                        if has_value(status)
                        else []
                    ),
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
