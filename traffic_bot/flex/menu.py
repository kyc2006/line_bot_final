def main_menu_bubble() -> dict:
    return main_menu_carousel()


def main_menu_carousel() -> dict:
    return {
        "type": "carousel",
        "contents": [
            _home_page(),
            _feature_page(
                "公車查詢",
                "輸入路線即可查即時到站。",
                ["300", "300公車", "公車300", "300多久到"],
                [
                    ("開始查公車", "查公車", "#2563EB"),
                    ("熱門路線", "熱門路線", "#0F766E"),
                    ("回主選單", "主選單", "#475569"),
                ],
            ),
            _feature_page(
                "YouBike 查詢",
                "輸入站名、地標或區域。",
                ["YouBike 台中車站", "ubike 逢甲"],
                [
                    ("開始查 YouBike", "找 YouBike", "#0F766E"),
                    ("換個地點", "換個地點", "#2563EB"),
                    ("回主選單", "主選單", "#475569"),
                ],
            ),
            _feature_page(
                "停車場查詢",
                "輸入地點或區域查剩餘車位。",
                ["西屯停車場", "台中車站停車場"],
                [
                    ("開始查停車場", "查停車場", "#B45309"),
                    ("換個區域", "換個區域", "#2563EB"),
                    ("回主選單", "主選單", "#475569"),
                ],
            ),
            _feature_page(
                "訂閱與服務",
                "管理推播與查看資料來源狀態。",
                ["我的訂閱", "服務狀態", "使用說明"],
                [
                    ("我的訂閱", "我的訂閱", "#2563EB"),
                    ("服務狀態", "服務狀態", "#0F766E"),
                    ("使用說明", "使用說明", "#475569"),
                ],
            ),
        ],
    }


def _home_page() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1E3A5F",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "台中交通小幫手",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "text": "即時掌握公車、YouBike 與停車資訊",
                    "size": "sm",
                    "color": "#DBEAFE",
                    "margin": "md",
                    "wrap": True,
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                _menu_button("查公車", "查公車", "#2563EB"),
                _menu_button("找 YouBike", "找 YouBike", "#0F766E"),
                _menu_button("查停車場", "查停車場", "#B45309"),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": [
                {
                    "type": "text",
                    "text": "可直接輸入：查 300 到站、訂閱 300、取消訂閱 300",
                    "size": "xs",
                    "color": "#64748B",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": "資料來源：TDX、台中市開放資料",
                    "size": "xs",
                    "color": "#64748B",
                    "wrap": True,
                }
            ],
        },
    }


def _feature_page(
    title: str,
    subtitle: str,
    examples: list[str],
    buttons: list[tuple[str, str, str]],
) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1E3A5F",
            "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "xl", "color": "#FFFFFF"},
                {"type": "text", "text": subtitle, "size": "sm", "color": "#DBEAFE", "margin": "md", "wrap": True},
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F8FAFC",
                    "cornerRadius": "8px",
                    "paddingAll": "12px",
                    "contents": [
                        {"type": "text", "text": "可以這樣輸入", "size": "xs", "color": "#64748B"},
                        {"type": "text", "text": "、".join(examples), "weight": "bold", "size": "md", "color": "#0F172A", "wrap": True},
                    ],
                },
                *[_menu_button(label, text, color) for label, text, color in buttons],
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "資料來源：TDX、台中市開放資料", "size": "xs", "color": "#64748B", "wrap": True}
            ],
        },
    }


def _menu_button(label: str, text: str, color: str) -> dict:
    return {
        "type": "button",
        "style": "primary",
        "height": "sm",
        "color": color,
        "action": {
            "type": "message",
            "label": label,
            "text": text,
        },
    }
