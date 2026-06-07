def main_menu_bubble() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F766E",
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
                    "text": "公車、YouBike、停車資訊快速查",
                    "size": "sm",
                    "color": "#CCFBF1",
                    "margin": "md",
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                _menu_button("公車查詢", "300公車", "#14B8A6"),
                _menu_button("YouBike查詢", "YouBike 台中車站", "#0EA5E9"),
                _menu_button("停車場查詢", "停車場", "#F97316"),
                _menu_button("即時路況", "即時路況", "#64748B"),
                _menu_button("使用說明", "使用說明", "#334155"),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "也可輸入：訂閱 300、取消訂閱 300、我的訂閱",
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
