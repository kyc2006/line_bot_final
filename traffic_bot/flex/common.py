from __future__ import annotations

from utils.time_format import display_time


def help_bubble() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header("使用說明", "不用背指令，直接輸入想查的交通資訊。"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [
                _help_item("查公車", "輸入 300、查300、300多久到"),
                _help_item("找 YouBike", "輸入 YouBike 台中車站、ubike 台中車站"),
                _help_item("查停車場", "輸入 停車場、查停車、西屯停車場"),
                _help_item("訂閱推播", "輸入 訂閱300、我的訂閱、取消訂閱300"),
                _help_item("服務資訊", "輸入 服務狀態 或 status"),
            ],
        },
        "footer": _footer("資料來源：TDX、台中市開放資料"),
    }


def service_status_bubble(line_enabled: bool, tdx_enabled: bool) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header("服務狀態", f"更新於 {display_time('')}"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [
                _status_item("LINE Bot", "正常" if line_enabled else "尚未設定", line_enabled),
                _status_item("TDX 資料", "可查詢" if tdx_enabled else "尚未設定", tdx_enabled),
                _status_item("資料來源", "TDX / 台中市開放資料", True),
            ],
        },
        "footer": _footer("若查詢暫時失敗，可能是資料來源更新或網路逾時。"),
    }


def unknown_input_bubble() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header("想查什麼呢？", "可以直接輸入路線、站點或功能名稱。"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#F8FAFC",
            "contents": [
                _help_item("公車", "300、查 300 到站、300 往靜宜大學"),
                _help_item("YouBike", "YouBike 台中車站、腳踏車 台中車站"),
                _help_item("停車", "停車場、查停車"),
            ],
        },
        "footer": _footer("輸入「主選單」可查看所有功能。"),
    }


def _header(title: str, subtitle: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#1E3A5F",
        "paddingAll": "18px",
        "contents": [
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
                "text": subtitle,
                "size": "sm",
                "color": "#DBEAFE",
                "margin": "sm",
                "wrap": True,
            },
        ],
    }


def _help_item(title: str, description: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": "#E2E8F0",
        "borderWidth": "1px",
        "contents": [
            {
                "type": "text",
                "text": title,
                "weight": "bold",
                "size": "sm",
                "color": "#0F172A",
            },
            {
                "type": "text",
                "text": description,
                "size": "xs",
                "color": "#64748B",
                "margin": "xs",
                "wrap": True,
            },
        ],
    }


def _status_item(label: str, value: str, healthy: bool) -> dict:
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
                "text": label,
                "weight": "bold",
                "size": "sm",
                "color": "#0F172A",
                "flex": 2,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "align": "end",
                "color": "#0F766E" if healthy else "#B45309",
                "flex": 3,
                "wrap": True,
            },
        ],
    }


def _footer(text: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": text,
                "size": "xs",
                "color": "#64748B",
                "wrap": True,
            }
        ],
    }
