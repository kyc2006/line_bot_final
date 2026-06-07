def main_menu_bubble() -> dict:
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
                _menu_button("查公車", "公車", "#2563EB"),
                _menu_button("找 YouBike", "YouBike", "#0F766E"),
                _menu_button("查停車場", "停車", "#B45309"),
                _menu_button("我的訂閱", "我的訂閱", "#475569"),
                _menu_button("服務狀態", "服務狀態", "#475569"),
                _menu_button("使用說明", "使用說明", "#334155"),
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
