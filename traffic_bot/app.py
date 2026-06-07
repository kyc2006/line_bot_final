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
    popular_routes_bubble,
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
from services.parking_service import (
    format_parking_text,
    inspect_parking_data,
    parse_parking_query,
    search_parking,
)
from utils.line_message import flex_or_text, make_quick_reply
from utils.nlu import UserIntent, parse_user_intent, resolve_context


app = Flask(__name__)

configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
subscription_repository = SubscriptionRepository()
daily_push_started = False
daily_push_start_lock = threading.Lock()
conversation_contexts: dict[str, dict] = {}
CONTEXT_TTL_SECONDS = 30 * 60

MAIN_QUICK_REPLIES = [
    ("查公車", "查公車"),
    ("找 YouBike", "找 YouBike"),
    ("查停車場", "查停車場"),
    ("我的訂閱", "我的訂閱"),
    ("服務狀態", "服務狀態"),
    ("使用說明", "使用說明"),
]

BUS_GUIDE_QUICK_REPLIES = [
    ("300", "300"),
    ("301", "301"),
    ("306", "306"),
    ("307", "307"),
    ("回主選單", "主選單"),
]

YOUBIKE_GUIDE_QUICK_REPLIES = [
    ("台中車站", "YouBike 台中車站"),
    ("逢甲", "YouBike 逢甲"),
    ("靜宜", "YouBike 靜宜"),
    ("換個地點", "換個地點"),
    ("回主選單", "主選單"),
]

PARKING_GUIDE_QUICK_REPLIES = [
    ("台中車站", "台中車站停車場"),
    ("西屯", "西屯停車場"),
    ("逢甲", "逢甲停車場"),
    ("市政府", "市政府停車場"),
    ("回主選單", "主選單"),
]

UNKNOWN_QUICK_REPLIES = [
    ("查公車", "查公車"),
    ("找 YouBike", "找 YouBike"),
    ("查停車場", "查停車場"),
    ("使用說明", "使用說明"),
    ("主選單", "主選單"),
]


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
    user_id = request.args.get("user", "debug-user")
    if request.args.get("reset_context") == "1":
        conversation_contexts.pop(user_id, None)
    result = build_reply_result(text, user_id)
    replies = [summarize_message(message) for message in result["messages"]]
    payload = {
        "input": text,
        "parsed_intent": result["intent"].name,
        "confidence": result["intent"].confidence,
        "entities": result["intent"].entities,
        "extracted_entities": result["intent"].entities,
        "context_before": result["context_before"],
        "context_after": result["context_after"],
        "message_count": len(replies),
        "quick_reply_count": sum(reply.get("quick_reply_count", 0) for reply in replies),
        "replies": replies,
    }
    if request.args.get("debug") == "1":
        payload["parking_debug"] = inspect_parking_data()
    return payload


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
    return build_reply_result(text, user_id)["messages"]


def build_reply_result(text: str, user_id: str | None = None) -> dict:
    context_before = get_user_context(user_id)
    parsed_intent = parse_user_intent(text)
    intent = resolve_context(parsed_intent, context_before)
    messages = dispatch_intent(text, user_id, intent)
    context_after = update_user_context(user_id, intent)
    return {
        "intent": intent,
        "context_before": context_before,
        "context_after": context_after,
        "messages": messages,
    }


def dispatch_intent(text: str, user_id: str | None, intent: UserIntent) -> list:
    if intent.name in ("main_menu", "greeting"):
        return build_main_menu_messages()

    if intent.name == "capability_question":
        return [
            flex_or_text(
                "台中交通小幫手功能介紹",
                main_menu_bubble,
                "我可以幫你查台中公車、YouBike 和停車資訊。你可以直接問：300多久到、逢甲附近有 YouBike 嗎、西屯哪裡有車位。",
                MAIN_QUICK_REPLIES,
            )
        ]

    if intent.name == "help":
        return [
            flex_or_text(
                "台中交通小幫手使用說明",
                help_bubble,
                usage_text(),
                MAIN_QUICK_REPLIES,
            )
        ]

    if intent.name == "status":
        return [
            flex_or_text(
                "台中交通小幫手服務狀態",
                lambda: service_status_bubble(Config.LINE_BOT_ENABLED, Config.TDX_ENABLED),
                service_status_text(),
                MAIN_QUICK_REPLIES,
            )
        ]

    if text == "即時路況":
        return [
            TextMessage(
                text="即時路況功能準備中，之後會加入主要幹道壅塞提醒。",
                quick_reply=make_quick_reply(MAIN_QUICK_REPLIES),
            )
        ]

    if intent.name == "bus_guide":
        return build_bus_prompt_messages()

    if intent.name == "popular_routes":
        return [
            flex_or_text(
                "台中熱門公車路線",
                popular_routes_bubble,
                "熱門公車路線：300、301、302、307、310、323。",
                BUS_GUIDE_QUICK_REPLIES,
            )
        ]

    if intent.name == "bus_unsubscribe":
        return build_unsubscribe_messages(user_id, intent.route)

    if intent.name == "bus_subscribe":
        return build_subscribe_messages(user_id, intent.route)

    if intent.name == "subscription_list":
        return build_subscription_list_messages(user_id)

    if intent.name == "bike_guide":
        return build_youbike_prompt_messages()

    if intent.name == "bike_search":
        return with_intro(
            build_youbike_messages(intent.query),
            f"幫你找{intent.query or '附近'}的 YouBike 站點，會優先顯示可借與可還數量。",
            _is_conversational_query(text),
        )

    if intent.name == "parking_guide":
        return build_parking_prompt_messages()

    if intent.name == "parking_search":
        return with_intro(
            build_parking_messages(intent.query),
            f"幫你找{intent.query or '台中'}附近的停車場，優先顯示有即時車位的資料。",
            _is_conversational_query(text),
        )

    if intent.name == "bus_search":
        return with_intro(
            build_bus_eta_messages(intent.route, intent.entities.get("destination", "")),
            f"幫你查 {intent.route} 公車即時到站資訊。",
            _is_conversational_query(text),
        )

    if intent.name == "retry_guide":
        return build_retry_guide_messages()

    if intent.name == "clarify":
        target = intent.entities.get("target_intent")
        if target == "bus_search":
            return build_bus_prompt_messages()
        if target == "bike_search":
            return build_youbike_prompt_messages()
        if target == "parking_search":
            return build_parking_prompt_messages()
        return build_retry_guide_messages()

    return [
        flex_or_text(
            "台中交通小幫手查詢提示",
            unknown_input_bubble,
            "請輸入要查詢的公車路線，例如：300、公車 300、查 300 到站。也可以輸入「主選單」或「使用說明」。",
            UNKNOWN_QUICK_REPLIES,
        )
    ]


def with_intro(messages: list, intro: str, enabled: bool) -> list:
    if not enabled:
        return messages
    return [TextMessage(text=intro), *messages]


def _is_conversational_query(text: str) -> bool:
    return any(keyword in text for keyword in ("我", "幫", "附近", "哪裡", "多久", "現在", "想", "可以", "還有"))


def get_user_context(user_id: str | None) -> dict:
    if not user_id:
        return {}
    context = conversation_contexts.get(user_id, {}).copy()
    updated_at = float(context.get("updated_at") or 0)
    if updated_at and time.time() - updated_at <= CONTEXT_TTL_SECONDS:
        return context
    conversation_contexts.pop(user_id, None)
    return {}


def update_user_context(user_id: str | None, intent: UserIntent) -> dict:
    if not user_id:
        return {}
    context = get_user_context(user_id)
    context["last_intent"] = intent.name
    context["updated_at"] = round(time.time(), 3)

    if intent.name == "clarify":
        target = intent.entities.get("target_intent")
        if target in ("bus_search", "bike_search", "parking_search"):
            context["pending_intent"] = target
        conversation_contexts[user_id] = context
        return context

    context.pop("pending_intent", None)
    if intent.name == "bus_search" and intent.route:
        context["last_bus_route"] = intent.route
    elif intent.name == "bike_search" and intent.query:
        context["last_bike_query"] = intent.query
    elif intent.name == "parking_search" and intent.query:
        context["last_parking_query"] = intent.query
    elif intent.name == "bus_subscribe" and intent.route:
        context["last_bus_route"] = intent.route

    conversation_contexts[user_id] = context
    return context.copy()


def build_main_menu_messages() -> list:
    return [
        flex_or_text(
            alt_text="台中交通小幫手主選單",
            flex_builder=main_menu_bubble,
            fallback_text="台中交通小幫手：輸入 300 查公車、YouBike 台中車站查站點、停車場查空位。",
            quick_reply_items=MAIN_QUICK_REPLIES,
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
                [("熱門路線", "熱門路線", "primary"), ("主選單", "主選單", None)],
            ),
            "請輸入公車路線，例如：300、307、300 往台中車站。",
            BUS_GUIDE_QUICK_REPLIES,
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
                [("換個地點", "換個地點", "primary"), ("主選單", "主選單", None)],
            ),
            "目前尚未開啟定位查詢，請輸入地點，例如：YouBike 台中車站。",
            YOUBIKE_GUIDE_QUICK_REPLIES,
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
                [("換個區域", "換個區域", "primary"), ("主選單", "主選單", None)],
            ),
            "請輸入地點或區域，例如：台中車站停車場、西屯停車場。",
            PARKING_GUIDE_QUICK_REPLIES,
        )
    ]


def summarize_message(message) -> dict:
    quick_reply = getattr(message, "quick_reply", None)
    quick_reply_items = getattr(quick_reply, "items", None) or []
    quick_reply_texts = [
        item.action.text
        for item in quick_reply_items
        if getattr(item, "action", None) and getattr(item.action, "text", None)
    ]
    if isinstance(message, TextMessage):
        return {
            "type": "text",
            "text": message.text,
            "summary": message.text[:80],
            "quick_reply_count": len(quick_reply_items),
            "quick_reply_texts": quick_reply_texts,
        }
    if isinstance(message, FlexMessage):
        return {
            "type": "flex",
            "alt_text": message.alt_text,
            "summary": message.alt_text,
            "quick_reply_count": len(quick_reply_items),
            "quick_reply_texts": quick_reply_texts,
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
    quick_replies = [
        ("重新整理", f"查詢 {route}"),
        ("訂閱路線", f"訂閱{route}"),
        ("主選單", "主選單"),
    ]
    try:
        arrivals = get_bus_eta(route, destination=destination)
    except Exception as exc:
        app.logger.warning("Bus ETA lookup failed for %s: %s", route, exc)
        return [
            TextMessage(
                text=f"目前查不到 {route} 的即時資料，請確認路線是否正確，或稍後再試。",
                quick_reply=make_quick_reply(quick_replies),
            )
        ]

    if not arrivals:
        return [
            TextMessage(
                text=f"目前查不到 {route} 的即時資料，請確認路線是否正確，或稍後再試。",
                quick_reply=make_quick_reply(quick_replies),
            )
        ]

    fallback_text = format_bus_eta_text(route, arrivals)
    message = flex_or_text(
        f"{route} 公車即時到站資訊",
        lambda: bus_eta_bubble(route, arrivals),
        fallback_text,
        quick_replies,
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
        return [
            TextMessage(
                text="目前 YouBike 資料暫時無法取得，請稍後再試。",
                quick_reply=make_quick_reply(YOUBIKE_GUIDE_QUICK_REPLIES),
            )
        ]

    if not stations:
        return [
            flex_or_text(
                "目前查不到可用資料",
                lambda: empty_state_bubble("目前查不到可用資料", "請換個地點或稍後再試。", "YouBike"),
                format_youbike_text(text, stations),
                [("重新輸入", "找 YouBike"), ("使用說明", "使用說明"), ("主選單", "主選單")],
            )
        ]

    fallback_text = format_youbike_text(text, stations)
    return [
        flex_or_text(
            "YouBike 即時車位資訊",
            lambda: youbike_bubble(query, stations),
            fallback_text,
            [("重新查詢", f"YouBike {query}"), ("換個地點", "換個地點"), ("主選單", "主選單")],
        )
    ]


def build_parking_messages(text: str = "停車場") -> list:
    query = parse_parking_query(text)
    if text in ("停車", "停車場", "查停車", "查停車場", "附近停車場", "換個區域") or text.lower() == "parking":
        return build_parking_prompt_messages()

    try:
        lots = search_parking(text)
    except Exception as exc:
        app.logger.warning("Parking lookup failed: %s", exc)
        return [
            TextMessage(
                text="目前停車場資料暫時無法取得，請稍後再試。",
                quick_reply=make_quick_reply(PARKING_GUIDE_QUICK_REPLIES),
            )
        ]

    if not lots:
        return [
            flex_or_text(
                "目前查不到可用資料",
                lambda: empty_state_bubble("目前查不到可用資料", "請換個地點或稍後再試。", "停車"),
                "目前查不到台中停車場資料，請換個地點或稍後再試。",
                [("重新輸入", "查停車場"), ("使用說明", "使用說明"), ("主選單", "主選單")],
            )
        ]

    retry_text = f"{query}停車場" if query else "查停車場"
    return [
        flex_or_text(
            "台中停車場即時空位",
            lambda: parking_bubble(lots, query=query),
            format_parking_text(lots),
            [("重新查詢", retry_text), ("換個區域", "換個區域"), ("主選單", "主選單")],
        )
    ]


def build_retry_guide_messages() -> list:
    return [
        flex_or_text(
            "請選擇要重新查詢的項目",
            unknown_input_bubble,
            "請選擇要重新查詢的項目：查公車、找 YouBike、查停車場。",
            UNKNOWN_QUICK_REPLIES,
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
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能訂閱。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]
    if not route:
        return [TextMessage(text="請輸入要訂閱的路線，例如：訂閱 300", quick_reply=make_quick_reply(BUS_GUIDE_QUICK_REPLIES))]

    try:
        created, routes = subscription_repository.subscribe(user_id, route)
    except SubscriptionStorageError as exc:
        app.logger.warning("Subscribe failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法更新，請稍後再試。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]

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
            MAIN_QUICK_REPLIES,
        )
    ]


def build_unsubscribe_messages(user_id: str | None, route: str) -> list:
    if not user_id:
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能取消訂閱。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]
    if not route:
        return [TextMessage(text="請輸入要取消的路線，例如：取消訂閱 300", quick_reply=make_quick_reply(BUS_GUIDE_QUICK_REPLIES))]

    try:
        removed, routes = subscription_repository.unsubscribe(user_id, route)
    except SubscriptionStorageError as exc:
        app.logger.warning("Unsubscribe failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法更新，請稍後再試。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]

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
            MAIN_QUICK_REPLIES,
        )
    ]


def build_subscription_list_messages(user_id: str | None) -> list:
    if not user_id:
        return [TextMessage(text="無法取得 LINE 使用者 ID，暫時不能查看訂閱。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]

    try:
        routes = subscription_repository.list_routes(user_id)
    except SubscriptionStorageError as exc:
        app.logger.warning("List subscriptions failed: %s", exc)
        return [TextMessage(text="訂閱資料暫時無法讀取，請稍後再試。", quick_reply=make_quick_reply(MAIN_QUICK_REPLIES))]

    if not routes:
        title = "我的訂閱"
        body = "目前沒有訂閱路線。可輸入「訂閱 300」加入常用公車。"
        return [
            flex_or_text(
                title,
                lambda: subscription_status_bubble(title, body, []),
                body,
                MAIN_QUICK_REPLIES,
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
            MAIN_QUICK_REPLIES,
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
