from __future__ import annotations

import json
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
    FlexContainer,
    FlexMessage,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from config import Config
from flex.menu import main_menu_bubble
from services.bike_service import reply_youbike
from services.bus_service import parse_bus_route, reply_bus_eta
from services.parking_service import reply_parking


app = Flask(__name__)

configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
subscription_lock = threading.Lock()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "taichung-traffic-line-bot",
        "line_bot_enabled": Config.LINE_BOT_ENABLED,
        "tdx_enabled": Config.TDX_ENABLED,
    }


@app.get("/test")
def test_reply():
    text = request.args.get("text", "主選單")
    messages = build_reply_messages(text, "debug-user")
    replies = []
    for message in messages:
        if isinstance(message, TextMessage):
            replies.append({"type": "text", "text": message.text})
        elif isinstance(message, FlexMessage):
            replies.append({"type": "flex", "alt_text": message.alt_text})
        else:
            replies.append({"type": message.__class__.__name__})
    return {"input": text, "replies": replies}


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
    line_bot_api.reply_message(
        ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
    )


def build_reply_messages(text: str, user_id: str | None = None) -> list:
    normalized = text.lower().strip()

    if text in ("主選單", "選單", "menu"):
        return [
            FlexMessage(
                alt_text="台中交通小幫手主選單",
                contents=FlexContainer.from_dict(main_menu_bubble()),
            )
        ]

    if text in ("使用說明", "help"):
        return [TextMessage(text=usage_text())]

    if text == "即時路況":
        return [TextMessage(text="即時路況功能已保留於主選單，後續可串接 TDX 路況資訊 v2。")]

    if normalized.startswith("取消訂閱"):
        route = parse_bus_route(text)
        return [TextMessage(text=unsubscribe_route(user_id, route))]

    if normalized.startswith("訂閱"):
        route = parse_bus_route(text)
        return [TextMessage(text=subscribe_route(user_id, route))]

    if text in ("我的訂閱", "訂閱清單"):
        return [TextMessage(text=list_subscriptions(user_id))]

    if "youbike" in normalized or "ubike" in normalized:
        return [TextMessage(text=reply_youbike(text))]

    if "停車場" in text or "停車" in text:
        return [TextMessage(text=reply_parking())]

    if "公車" in text:
        route = parse_bus_route(text)
        return [TextMessage(text=reply_bus_eta(route))]

    return [TextMessage(text="我看不太懂這次要查什麼。輸入「主選單」或「使用說明」可以查看範例。")]


def usage_text() -> str:
    return "\n".join(
        [
            "台中交通小幫手使用說明",
            "",
            "公車：輸入「300公車」",
            "YouBike：輸入「YouBike 台中車站」",
            "停車場：輸入「停車場」",
            "主選單：輸入「主選單」",
            "訂閱公車：輸入「訂閱 300」",
            "取消訂閱：輸入「取消訂閱 300」",
            "查看訂閱：輸入「我的訂閱」",
        ]
    )


def load_subscriptions() -> dict[str, list[str]]:
    if not Config.SUBSCRIPTION_FILE.exists():
        return {}
    with subscription_lock:
        with Config.SUBSCRIPTION_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)


def save_subscriptions(data: dict[str, list[str]]) -> None:
    Config.SUBSCRIPTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with subscription_lock:
        with Config.SUBSCRIPTION_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


def subscribe_route(user_id: str | None, route: str) -> str:
    if not user_id:
        return "無法取得 LINE 使用者 ID，暫時不能訂閱。"
    if not route:
        return "請輸入要訂閱的路線，例如：訂閱 300"

    data = load_subscriptions()
    routes = set(data.get(user_id, []))
    routes.add(route)
    data[user_id] = sorted(routes)
    save_subscriptions(data)
    return f"已訂閱 {route} 公車，每天會自動推播最新到站資訊。"


def unsubscribe_route(user_id: str | None, route: str) -> str:
    if not user_id:
        return "無法取得 LINE 使用者 ID，暫時不能取消訂閱。"
    if not route:
        return "請輸入要取消的路線，例如：取消訂閱 300"

    data = load_subscriptions()
    routes = set(data.get(user_id, []))
    if route not in routes:
        return f"你目前沒有訂閱 {route} 公車。"

    routes.remove(route)
    if routes:
        data[user_id] = sorted(routes)
    else:
        data.pop(user_id, None)
    save_subscriptions(data)
    return f"已取消訂閱 {route} 公車。"


def list_subscriptions(user_id: str | None) -> str:
    if not user_id:
        return "無法取得 LINE 使用者 ID，暫時不能查看訂閱。"

    routes = load_subscriptions().get(user_id, [])
    if not routes:
        return "你目前沒有訂閱公車路線。可輸入「訂閱 300」開始訂閱。"
    return "你已訂閱的公車路線：\n" + "\n".join(f"- {route}" for route in routes)


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
    subscriptions = load_subscriptions()
    for user_id, routes in subscriptions.items():
        for route in routes:
            text = "每日公車訂閱通知\n\n" + reply_bus_eta(route)
            try:
                line_bot_api.push_message(
                    PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
                )
            except Exception as exc:
                app.logger.warning("Push message failed for %s %s: %s", user_id, route, exc)


def start_daily_push_worker() -> None:
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return
    thread = threading.Thread(target=daily_push_worker, daemon=True)
    thread.start()


start_daily_push_worker()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5050")))
