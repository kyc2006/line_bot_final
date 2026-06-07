from __future__ import annotations

from utils.time_format import display_time

PRIMARY = "#1E3A5F"
BLUE = "#2563EB"
TEAL = "#0F766E"
AMBER = "#B45309"
RED = "#DC2626"
TEXT = "#0F172A"
MUTED = "#64748B"
SUBTLE = "#475569"
SURFACE = "#FFFFFF"
BACKGROUND = "#F8FAFC"
LINE = "#E2E8F0"


def has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip()
        return normalized not in (
            "",
            "未提供",
            "未提供資料",
            "None",
            "null",
            "N/A",
            "TDX 尚未提供此欄位",
            "OpenData 尚未提供此欄位",
            "OpenData 未提供資料",
        )
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def info_text(text: str, color: str = SUBTLE) -> dict:
    return {
        "type": "text",
        "text": text,
        "size": "xs",
        "color": color,
        "wrap": True,
    }


def info_row(label: str, value) -> dict | None:
    if not has_value(value):
        return None
    return info_text(f"{label}：{value}")


def compact_button(label: str, text: str, style: str = "secondary") -> dict:
    return {
        "type": "button",
        "style": style,
        "height": "sm",
        "action": {"type": "message", "label": label, "text": text},
    }


def action_buttons(buttons: list[tuple[str, str, str | None]]) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            compact_button(label, text, style or "secondary")
            for label, text, style in buttons
        ],
    }


def empty_state_bubble(title: str, description: str, retry_text: str) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header(title, description),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": BACKGROUND,
            "contents": [
                _help_item("可能原因", "資料來源更新中、關鍵字太精確，或目前沒有符合的資料。"),
                _help_item("下一步", "換個地點、縮短關鍵字，或稍後再試。"),
            ],
        },
        "footer": action_buttons(
            [
                ("重新輸入", retry_text, "primary"),
                ("使用說明", "使用說明", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def help_bubble() -> dict:
    return help_carousel()


def help_carousel() -> dict:
    pages = [
        ("查公車", "輸入路線即可查即時到站。", ["300", "查300", "300 往台中車站"]),
        ("找 YouBike", "輸入站名、地標或區域。", ["YouBike 台中車站", "ubike 逢甲", "腳踏車 靜宜"]),
        ("查停車場", "輸入地點或區域查停車資訊。", ["停車場", "西屯停車場", "台中車站停車場"]),
        ("訂閱推播", "訂閱常用路線，每日推播到站資訊。", ["訂閱300", "我的訂閱", "取消訂閱300"]),
        ("常見問題", "目前沒有定位查詢，請先輸入地點。", ["服務狀態", "主選單"]),
    ]
    return {
        "type": "carousel",
        "contents": [_guide_page(title, subtitle, examples) for title, subtitle, examples in pages],
    }


def _guide_page(title: str, subtitle: str, examples: list[str]) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header(title, subtitle),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": BACKGROUND,
            "contents": [_help_item("範例", example) for example in examples],
        },
        "footer": action_buttons([("主選單", "主選單", None)]),
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
                _status_item("TDX 資料", "可查詢" if tdx_enabled else "待設定", tdx_enabled),
                _status_item("資料來源", "TDX / 台中市開放資料", True),
            ],
        },
        "footer": action_buttons([("主選單", "主選單", None)]),
    }


def unknown_input_bubble() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header("我可以幫你查台中交通", "直接用聊天方式輸入也可以。"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": BACKGROUND,
            "contents": [
                _help_item("公車", "300多久到、幫我查300、300往靜宜大學"),
                _help_item("YouBike", "台中車站附近 YouBike、逢甲哪裡可以借腳踏車"),
                _help_item("停車", "西屯停車場、台中車站附近哪裡可以停車"),
            ],
        },
        "footer": action_buttons(
            [
                ("查公車", "查公車", "primary"),
                ("找 YouBike", "找 YouBike", None),
                ("查停車場", "查停車場", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def input_prompt_bubble(
    title: str,
    description: str,
    examples: list[str],
    buttons: list[tuple[str, str, str | None]] | None = None,
) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header(title, description),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": BACKGROUND,
            "contents": [_help_item("範例", example) for example in examples],
        },
        "footer": action_buttons(
            buttons or [("使用說明", "使用說明", None), ("主選單", "主選單", None)]
        ),
    }


def popular_routes_bubble() -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "header": _header("熱門公車路線", "點選路線後會直接查詢即時到站。"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": BACKGROUND,
            "contents": [
                _help_item("市區幹線", "300、301、302"),
                _help_item("常用路線", "307、310、323"),
                _help_item("也可以輸入方向", "例如：300 往台中車站"),
            ],
        },
        "footer": action_buttons(
            [
                ("300", "300", "primary"),
                ("307", "307", None),
                ("主選單", "主選單", None),
            ]
        ),
    }


def _header(title: str, subtitle: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": PRIMARY,
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
        "backgroundColor": SURFACE,
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": LINE,
        "borderWidth": "1px",
        "contents": [
            {
                "type": "text",
                "text": title,
                "weight": "bold",
                "size": "sm",
                "color": TEXT,
            },
            {
                "type": "text",
                "text": description,
                "size": "xs",
                "color": MUTED,
                "margin": "xs",
                "wrap": True,
            },
        ],
    }


def _status_item(label: str, value: str, healthy: bool) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "backgroundColor": SURFACE,
        "cornerRadius": "8px",
        "paddingAll": "12px",
        "borderColor": LINE,
        "borderWidth": "1px",
        "contents": [
            {
                "type": "text",
                "text": label,
                "weight": "bold",
                "size": "sm",
                "color": TEXT,
                "flex": 2,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "align": "end",
                "color": TEAL if healthy else AMBER,
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
                "color": MUTED,
                "wrap": True,
            }
        ],
    }
