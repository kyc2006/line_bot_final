from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from config import Config
from flex.bus import bus_eta_bubble
from flex.bike import youbike_bubble
from flex.common import (
    empty_state_bubble,
    help_bubble,
    input_prompt_bubble,
    service_status_bubble,
    unknown_input_bubble,
)
from flex.menu import main_menu_bubble
from flex.parking import parking_bubble
from flex.subscription import subscription_status_bubble
from repositories.subscription_repository import (
    SubscriptionRepository,
    SubscriptionStorageError,
)
from services.bike_service import format_youbike_text, parse_youbike_query, search_youbike
from services.bus_service import (
    format_bus_eta_text,
    get_bus_eta,
    parse_bus_destination,
    parse_bus_route,
)
from services.parking_service import format_parking_text, parse_parking_query, search_parking
from utils.line_message import flex_or_text


app = Flask(__name__)

configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
subscription_repository = SubscriptionRepository()
daily_push_started = False
daily_push_start_lock = threading.Lock()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "taichung-traffic-line-bot",
        "version": os.getenv("APP_VERSION", "local"),
        "line_bot_enabled": Config.LINE_BOT_ENABLED,
        "tdx_enabled": Config.TDX_ENABLED,
    }


@app.get("/test")
def test_reply():
    if Config.TEST_TOKEN:
        token = request.args.get("token") or request.headers.get("X-Test-Token", "")
        if token != Config.TEST_TOKEN:
            abort(401)

    text = request.args.get("text", "主選單")
    messages = build_reply_messages(text, "debug-user")
    replies = [summarize_message(message) for message in messages]
    return {"input": text, "message_count": len(replies), "replies": replies}


@app.post("/internal/push-daily")
def internal_push_daily():
    if not Config.INTERNAL_API_TOKEN:
        app.logger.warning("Daily push endpoint called without INTERNAL_API_TOKEN configured.")
        return {"error": "internal push endpoint is not configured"}, 503

    token = request.headers.get("X-Internal-Token", "")
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    token = token or request.args.get("token", "")
    if token != Config.INTERNAL_API_TOKEN:
        abort(401)

    pushed_count = push_daily_subscriptions()
    return {"status": "ok", "pushed_messages": pushed_count}


@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    text = event.message.text.strip()
    user_id = event.source.user_id
    messages = build_reply_messages(text, user_id)
    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
        )
    except Exception as exc:
        app.logger.exception("LINE reply failed: %s", exc)


def build_reply_messages(text: str, user_id: str | None = None) -> list:
    normalized = text.lower().strip()

    if text in ("主選單", "回主選單", "選單", "menu"):
        return build_main_menu_messages()

    if normalized in ("hi", "hello", "嗨", "你好", "哈囉", "開始"):
        return build_main_menu_messages()

    if text in ("使用說明", "help"):
        return [
            flex_or_text(
                "台中交通小幫手使用說明",
                help_bubble,
                usage_text(),
            )
        ]

    if text in ("服務狀態", "資料來源") or normalized == "status":
        return [
            flex_or_text(
                "台中交通小幫手服務狀態",
                lambda: service_status_bubble(Config.LINE_BOT_ENABLED, Config.TDX_ENABLED),
                service_status_text(),
            )
        ]

    if text == "即時路況":
        return [TextMessage(text="即時路況功能準備中，之後會加入主要幹道壅塞提醒。")]

    if text in ("公車", "查公車", "重新整理") or normalized == "bus":
        return build_bus_prompt_messages()

    if normalized.startswith("取消訂閱"):
        route = parse_bus_route(text)
        return build_unsubscribe_messages(user_id, route)

    if normalized.startswith("訂閱"):
        route = parse_bus_route(text)
        return build_subscribe_messages(user_id, route)

    if text in ("我的訂閱", "訂閱清單"):
        return build_subscription_list_messages(user_id)

    if is_youbike_query(text):
        return build_youbike_messages(text)

    if "停車場" in text or "停車" in text or text == "換個區域" or normalized == "parking":
        return build_parking_messages(text)

    route = parse_bus_route(text)
    if route:
        return build_bus_eta_messages(route, parse_bus_destination(text))

    return [
        flex_or_text(
            "台中交通小幫手查詢提示",
            unknown_input_bubble,
            "請輸入要查詢的公車路線，例如：300、公車 300、查 300 到站。也可以輸入「主選單」或「使用說明」。",
        )
    ]


def build_main_menu_messages() -> list:
    return [
        flex_or_text(
            alt_text="台中交通小幫手主選單",
            flex_builder=main_menu_bubble,
            fallback_text="台中交通小幫手：輸入 300 查公車、YouBike 台中車站查站點、停車場查空位。",
        )
    ]


def build_bus_prompt_messages() -> list:
    return [
        flex_or_text(
            "請輸入公車路線",
            lambda: input_prompt_bubble(
                "查公車",
                "請輸入公車路線，若知道方向也可以一起輸入。",
                ["300", "307", "300 往台中車站"],
            ),
            "請輸入公車路線，例如：300、307、300 往台中車站。",
        )
    ]


def build_youbike_prompt_messages() -> list:
    return [
        flex_or_text(
            "請輸入 YouBike 地點",
            lambda: input_prompt_bubble(
                "找 YouBike",
                "目前尚未開啟定位查詢，請輸入站名、地標或區域。",
                ["YouBike 台中車站", "ubike 逢甲", "腳踏車 靜宜"],
            ),
            "目前尚未開啟定位查詢，請輸入地點，例如：YouBike 台中車站。",
        )
    ]


def build_parking_prompt_messages() -> list:
    return [
        flex_or_text(
            "請輸入停車場地點",
            lambda: input_prompt_bubble(
                "查停車場",
                "請輸入地點或區域；若只輸入「停車場」會顯示目前可用資料前幾筆。",
                ["台中車站停車場", "西屯停車場", "逢甲停車場"],
            ),
            "請輸入地點或區域，例如：台中車站停車場、西屯停車場。",
        )
    ]


def summarize_message(message) -> dict:
    if isinstance(message, TextMessage):
        return {
            "type": "text",
            "text": message.text,
            "summary": message.text[:80],
        }
    if isinstance(message, FlexMessage):
        return {
            "type": "flex",
            "alt_text": message.alt_text,
            "summary": message.alt_text,
        }
    return {"type": message.__class__.__name__, "summary": message.__class__.__name__}


def is_youbike_query(text: str) -> bool:
    normalized = text.lower()
    return (
        "youbike" in normalized
        or "ubike" in normalized
        or "腳踏車" in text
        or "自行車" in text
        or text == "換個地點"
    )


def build_bus_eta_messages(route: str, destination: str = "") -> list:
    try:
        arrivals = get_bus_eta(route, destination=destination)
    except Exception as exc:
        app.logger.warning("Bus ETA lookup failed for %s: %s", route, exc)
        return [TextMessage(text=f"目前查不到 {route} 的即時資料，請確認路線是否正確，或稍後再試。")]

    if not arrivals:
        return [TextMessage(text=f"目前查不到 {route} 的即時資料，請確認路線是否正確，或稍後再試。")]

    fallback_text = format_bus_eta_text(route, arrivals)
    message = flex_or_text(
        f"{route} 公車即時到站資訊",
        lambda: bus_eta_bubble(route, arrivals),
        fallback_text,
    )
    return [message]


def build_youbike_messages(text: str) -> list:
    if text == "換個地點":
        return build_youbike_prompt_messages()

    query = parse_youbike_query(text)
    if not query:
        return build_youbike_prompt_messages()

    try:
        stations = search_youbike(text)
    except Exception as exc:
        app.logger.warning("YouBike lookup failed: %s", exc)
        return [TextMessage(text="目前 YouBike 資料暫時無法取得，請稍後再試。")]

    if not stations:
        return [
            flex_or_text(
                "目前查不到可用資料",
                lambda: empty_state_bubble("目前查不到可用資料", "請換個地點或稍後再試。", "YouBike"),
                format_youbike_text(text, stations),
            )
        ]

    fallback_text = format_youbike_text(text, stations)
    return [
        flex_or_text(
            "YouBike 即時車位資訊",
            lambda: youbike_bubble(query, stations),
            fallback_text,
        )
    ]


def build_parking_messages(text: str = "停車場") -> list:
    query = parse_parking_query(text)
    if text in ("停車", "查停車", "查停車場", "附近停車場", "換個區域") or text.lower() == "parking":
        return build_parking_prompt_messages()

    try:
        lots = search_parking(text)
    except Exception as exc:
        app.logger.warning("Parking lookup failed: %s", exc)
        return [TextMessage(text="目前停車場資料暫時無法取得，請稍後再試。")]

    if not lots:
        return [
            flex_or_text(
                "目前查不到可用資料",
                lambda: empty_state_bubble("目前查不到可用資料", "請換個地點或稍後再試。", "停車"),
                "目前查不到台中停車場資料，請換個地點或稍後再試。",
            )
        ]

    return [
        flex_or_text(
            "台中停車場即時空位",
            lambda: parking_bubble(lots, query=query),
            format_parking_text(lots),
        )
    ]


def usage_text() -> str:
    return "\n".join(
        [
            "台中交通小幫手使用說明",
            "",
            "公車：輸入「300」、「查 300 到站」或「300 往靜宜大學」",
            "YouBike：輸入「YouBike 台中車站」或「ubike 台中車站」",
            "停車場：輸入「停車場」",
            "主選單：輸入「主選單」",
            "訂閱公車：輸入「訂閱 300」",
            "取消訂閱：輸入「取消訂閱 300」",
            "查看訂閱：輸入「我的訂閱」",
            "",
            "資料來源：TDX、台中市開放資料。",
        ]
    )


def service_status_text() -> str:
    line_status = "正常" if Config.LINE_BOT_ENABLED else "尚未設定"
    tdx_status = "可查詢" if Config.TDX_ENABLED else "尚未設定"
    return "\n".join(
        [
            "台中交通小幫手服務狀態",
            f"LINE Bot：{line_status}",
            f"TDX 資料：{tdx_status}",
            "資料來源：TDX、台中市開放資料",
        ]
    )


def build_subscribe_messages(user_id: str | None, route: str) -> list:
    if not user_id:
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能訂閱。")]
    if not route:
        return [TextMessage(text="請輸入要訂閱的路線，例如：訂閱 300")]

    try:
        created, routes = subscription_repository.subscribe(user_id, route)
    except SubscriptionStorageError as exc:
        app.logger.warning("Subscribe failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法更新，請稍後再試。")]

    if created:
        title = f"已訂閱 {route} 公車"
        body = "每天會依設定時間推播即時到站資訊。"
    else:
        title = f"你已經訂閱過 {route} 公車"
        body = "這條路線已在你的訂閱清單中。"
    fallback = f"{title}\n{body}\n\n目前訂閱：{', '.join(routes)}"
    return [
        flex_or_text(
            title,
            lambda: subscription_status_bubble(title, body, routes),
            fallback,
        )
    ]


def build_unsubscribe_messages(user_id: str | None, route: str) -> list:
    if not user_id:
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能取消訂閱。")]
    if not route:
        return [TextMessage(text="請輸入要取消的路線，例如：取消訂閱 300")]

    try:
        removed, routes = subscription_repository.unsubscribe(user_id, route)
    except SubscriptionStorageError as exc:
        app.logger.warning("Unsubscribe failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法更新，請稍後再試。")]

    if removed:
        title = f"已取消訂閱 {route}"
        body = "之後不會再推播這條路線。"
    else:
        title = f"你目前沒有訂閱 {route} 公車"
        body = "可以輸入「訂閱 300」加入常用路線。"
    fallback = f"{title}\n{body}"
    if routes:
        fallback += "\n\n目前訂閱：" + ", ".join(routes)
    return [
        flex_or_text(
            title,
            lambda: subscription_status_bubble(title, body, routes),
            fallback,
        )
    ]


def build_subscription_list_messages(user_id: str | None) -> list:
    if not user_id:
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能查看訂閱。")]

    try:
        routes = subscription_repository.list_routes(user_id)
    except SubscriptionStorageError as exc:
        app.logger.warning("List subscriptions failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法讀取，請稍後再試。")]

    if not routes:
        title = "我的訂閱"
        body = "目前沒有訂閱路線。可輸入「訂閱 300」加入常用公車。"
        return [
            flex_or_text(
                title,
                lambda: subscription_status_bubble(title, body, []),
                body,
            )
        ]

    title = "我的訂閱"
    body = "以下路線會依設定時間推播即時到站資訊。"
    fallback = "你已訂閱的公車路線：\n" + "\n".join(f"- {route}" for route in routes)
    return [
        flex_or_text(
            title,
            lambda: subscription_status_bubble(title, body, routes),
            fallback,
        )
    ]


def daily_push_worker() -> None:
    timezone = ZoneInfo(Config.PUSH_TIMEZONE)
    last_sent_date = None

    while True:
        now = datetime.now(timezone)
        should_push = (
            now.hour == Config.PUSH_HOUR
            and now.minute == Config.PUSH_MINUTE
            and last_sent_date != now.date()
        )

        if should_push:
            push_daily_subscriptions()
            last_sent_date = now.date()

        time.sleep(30)


def push_daily_subscriptions() -> None:
    try:
        subscriptions = subscription_repository.all()
    except SubscriptionStorageError as exc:
        app.logger.warning("Daily push skipped because subscriptions failed to load: %s", exc)
        return 0

    pushed_count = 0
    for user_id, routes in subscriptions.items():
        for route in routes:
            messages = build_bus_eta_messages(route)
            try:
                line_bot_api.push_message(
                    PushMessageRequest(to=user_id, messages=messages)
                )
                pushed_count += len(messages)
            except Exception as exc:
                app.logger.warning("Push message failed for %s %s: %s", user_id, route, exc)
    return pushed_count


def start_daily_push_worker() -> None:
    global daily_push_started
    if not Config.ENABLE_DAILY_PUSH:
        return
    with daily_push_start_lock:
        if daily_push_started:
            return
        thread = threading.Thread(target=daily_push_worker, daemon=True)
        thread.start()
        daily_push_started = True


start_daily_push_worker()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5050")))
