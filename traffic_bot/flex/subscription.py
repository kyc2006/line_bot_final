from __future__ import annotations


def subscription_status_bubble(title: str, body: str, routes: list[str]) -> dict:
    contents = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "lg",
            "color": "#FFFFFF",
            "wrap": True,
        },
        {
            "type": "text",
            "text": body,
            "size": "sm",
            "color": "#DBEAFE",
            "margin": "sm",
            "wrap": True,
        },
    ]

    route_cards = [_route_card(route) for route in routes] or [
        {
            "type": "text",
            "text": "目前沒有訂閱路線。",
            "size": "sm",
            "color": "#475569",
            "wrap": True,
        }
    ]

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1E3A5F",
            "paddingAll": "18px",
            "contents": contents,
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": route_cards,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "取消訂閱請輸入：取消訂閱 300",
                    "size": "xs",
                    "color": "#64748B",
                    "wrap": True,
                }
            ],
        },
    }


def _route_card(route: str) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": "#E2E8F0",
        "borderWidth": "1px",
        "contents": [
            {
                "type": "text",
                "text": f"🚌 {route}",
                "weight": "bold",
                "size": "md",
                "color": "#0F172A",
                "flex": 2,
            },
            {
                "type": "text",
                "text": "每日推播中",
                "size": "sm",
                "color": "#0F766E",
                "align": "end",
                "flex": 3,
            },
        ],
    }
