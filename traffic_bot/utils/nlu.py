from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from services.bike_service import parse_youbike_query
from services.bus_service import parse_bus_destination, parse_bus_route
from services.parking_service import parse_parking_query


@dataclass(frozen=True)
class UserIntent:
    name: str
    confidence: float
    entities: dict[str, str | bool] = field(default_factory=dict)
    normalized_text: str = ""
    reply_style: str = "search"

    @property
    def query(self) -> str:
        return str(self.entities.get("query", "") or self.entities.get("location", "") or "")

    @property
    def route(self) -> str:
        return str(self.entities.get("route", "") or "")


KNOWN_LOCATIONS = (
    "台中車站",
    "逢甲",
    "西屯",
    "市政府",
    "靜宜",
    "一中",
    "勤美",
    "高鐵",
    "新烏日",
    "豐原",
    "沙鹿",
    "清水",
    "大里",
    "太平",
    "北屯",
    "南屯",
    "西區",
    "北區",
    "中區",
)

CAPABILITY_PATTERNS = (
    "可以做什麼",
    "能做什麼",
    "你會什麼",
    "有什麼功能",
    "我可以問什麼",
    "我可以查什麼",
    "可以查什麼",
    "能查什麼",
    "可以幫我做什麼",
    "你可以幫我做什麼",
)

PARKING_KEYWORDS = ("停車", "停車場", "車位", "停車位", "哪裡可以停", "空位", "有空位")
BIKE_KEYWORDS = ("youbike", "ubike", "腳踏車", "自行車", "單車", "共享單車", "借車", "還車")
BUS_KEYWORDS = ("公車", "路線", "到站", "多久", "下一班", "現在到哪", "我要搭", "往", "去")
QUESTION_KEYWORDS = ("附近", "哪裡", "哪里", "哪邊", "有嗎", "有沒有", "還有", "可以嗎", "嗎")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("臺", "台")
    normalized = normalized.replace("UBike", "YouBike").replace("ubike", "YouBike")
    normalized = re.sub(r"\s+", " ", normalized).strip(" ：:，,。！？!?")
    return normalized


def parse_user_intent(text: str) -> UserIntent:
    normalized = normalize_text(text)
    compact = _compact(normalized)

    if not normalized:
        return _intent("unknown", 0.1, normalized)

    route = _clean_route(parse_bus_route(normalized))
    destination = parse_bus_destination(normalized)

    if _has_any(compact, ("取消訂閱", "不要訂閱", "取消追蹤", "移除")) and route:
        return _intent("bus_unsubscribe", 0.98, normalized, route=route, destination=destination)

    if _has_any(compact, ("訂閱", "提醒", "追蹤")) and route:
        return _intent("bus_subscribe", 0.96, normalized, route=route, destination=destination)

    if compact in ("訂閱這條", "追蹤這條", "每天提醒這條"):
        return _intent("bus_subscribe", 0.72, normalized, needs_context=True)

    if compact in ("取消這條", "不要這條了", "取消追蹤這條"):
        return _intent("bus_unsubscribe", 0.72, normalized, needs_context=True)

    if compact in ("我的訂閱", "訂閱清單") or _has_any(compact, ("追蹤了哪些公車", "有訂閱什麼", "查看我的公車")):
        return _intent("subscription_list", 0.95, normalized)

    if compact in ("主選單", "回主選單", "選單", "menu"):
        return _intent("main_menu", 0.96, normalized)

    if _has_any(compact, CAPABILITY_PATTERNS):
        return _intent("capability_question", 0.95, normalized, reply_style="guide")

    if compact in ("使用說明", "help", "說明", "怎麼用"):
        return _intent("help", 0.95, normalized)

    if compact in ("服務狀態", "資料來源", "status") or _has_any(compact, ("系統正常嗎", "tdx正常嗎", "機器人正常嗎")):
        return _intent("status", 0.95, normalized)

    if compact in ("重新查詢", "重新輸入"):
        return _intent("clarify", 0.78, normalized, target_intent="retry", reply_style="clarify")

    if compact == "熱門路線":
        return _intent("popular_routes", 0.95, normalized)

    if compact in ("公車", "查公車", "bus", "重新整理"):
        return _intent("clarify", 0.9, normalized, target_intent="bus_search", reply_style="clarify")

    if compact in ("youbike", "找youbike", "腳踏車", "自行車", "單車", "找腳踏車"):
        return _intent("clarify", 0.9, normalized, target_intent="bike_search", reply_style="clarify")

    if compact in ("停車", "停車場", "查停車", "查停車場", "parking", "換個區域"):
        return _intent("clarify", 0.9, normalized, target_intent="parking_search", reply_style="clarify")

    if compact == "換個地點":
        return _intent("clarify", 0.9, normalized, target_intent="bike_search", reply_style="clarify")

    ranked = _rank_intents(normalized, route, destination)
    if ranked:
        return ranked[0]

    if _is_location_only(normalized):
        return _intent("clarify", 0.45, normalized, location=_extract_location(normalized), reply_style="clarify")

    if compact in ("hi", "hello", "嗨", "你好", "哈囉", "開始"):
        return _intent("greeting", 0.9, normalized, reply_style="guide")

    return _intent("unknown", 0.2, normalized, reply_style="clarify")


def resolve_context(intent: UserIntent, context: dict | None) -> UserIntent:
    context = context or {}
    pending_intent = str(context.get("pending_intent") or "")
    location = str(intent.entities.get("location") or intent.query or "")

    if intent.name in ("bus_subscribe", "bus_unsubscribe") and intent.entities.get("needs_context"):
        route = str(context.get("last_bus_route") or "")
        if route:
            return _intent(intent.name, 0.9, intent.normalized_text, route=route)
        return _intent("clarify", 0.65, intent.normalized_text, target_intent="bus_search", reply_style="clarify")

    if intent.name == "clarify" and location and pending_intent in ("parking_search", "bike_search"):
        if pending_intent == "parking_search":
            return _intent("parking_search", 0.88, intent.normalized_text, location=location, query=location, from_context=True)
        return _intent("bike_search", 0.88, intent.normalized_text, location=location, query=location, from_context=True)

    if intent.name == "clarify" and pending_intent == "bus_search":
        route = _clean_route(parse_bus_route(intent.normalized_text))
        if route:
            return _intent("bus_search", 0.9, intent.normalized_text, route=route)

    return intent


def _rank_intents(normalized: str, route: str, destination: str) -> list[UserIntent]:
    compact = _compact(normalized)
    location = _extract_location(normalized)
    candidates: list[tuple[str, float, dict[str, str | bool]]] = []

    bus_score = 0.0
    if route:
        bus_score += 0.62
    if _has_any(compact, BUS_KEYWORDS):
        bus_score += 0.2
    if _has_any(compact, ("多久到", "還要多久", "下一班", "到哪了", "到哪")):
        bus_score += 0.2
    if destination:
        bus_score += 0.08
    if bus_score >= 0.45:
        candidates.append(("bus_search", min(bus_score, 0.95), {"route": route, "destination": destination}))
    elif _has_any(compact, ("公車", "多久到", "到站")):
        candidates.append(("clarify", 0.66, {"target_intent": "bus_search"}))

    bike_score = _score_for(compact, BIKE_KEYWORDS, 0.52)
    if location:
        bike_score += 0.16
    if _has_any(compact, QUESTION_KEYWORDS):
        bike_score += 0.12
    bike_query = _extract_bike_query(normalized) or location
    if bike_score >= 0.5:
        candidates.append(
            (
                "bike_search",
                min(bike_score, 0.92),
                {"location": bike_query, "query": bike_query},
            )
        )

    parking_score = _score_for(compact, PARKING_KEYWORDS, 0.52)
    if location:
        parking_score += 0.18
    if _has_any(compact, QUESTION_KEYWORDS):
        parking_score += 0.12
    if _has_any(compact, ("有空位", "還有車位", "哪裡可以停")):
        parking_score += 0.1
    parking_query = _extract_parking_query(normalized) or location
    if parking_score >= 0.5:
        candidates.append(
            (
                "parking_search",
                min(parking_score, 0.94),
                {
                    "location": parking_query,
                    "query": parking_query,
                    "need_available_space": True,
                },
            )
        )

    candidates.sort(key=lambda item: item[1], reverse=True)
    return [
        _intent(name, score, normalized, **{key: value for key, value in entities.items() if value})
        for name, score, entities in candidates
    ]


def _clean_route(route: str) -> str:
    match = re.search(r"[A-Za-z]?\d{1,4}[A-Za-z]?", route or "")
    return match.group(0) if match else route


def _extract_location(text: str) -> str:
    normalized = normalize_text(text)
    compact = _compact(normalized)
    for place in KNOWN_LOCATIONS:
        if _compact(place) in compact:
            return place

    query = _remove_place_fillers(parse_parking_query(normalized))
    if query and query != normalized and len(query) <= 12:
        return query
    return ""


def _extract_bike_query(text: str) -> str:
    query = parse_youbike_query(text)
    return _remove_place_fillers(query)


def _extract_parking_query(text: str) -> str:
    query = parse_parking_query(text)
    return _remove_place_fillers(query)


def _remove_place_fillers(query: str) -> str:
    result = normalize_text(query)
    for keyword in (
        "我現在在",
        "我要去",
        "我想找",
        "我想",
        "想找",
        "幫我找",
        "幫我",
        "幫",
        "你",
        "做什麼",
        "YouBike",
        "youbike",
        "附近的",
        "附近",
        "哪裡",
        "哪里",
        "哪邊",
        "地方",
        "可以",
        "有嗎",
        "有沒有",
        "還有",
        "有",
        "嗎",
        "借",
        "還",
        "空",
        "位",
        "的",
    ):
        result = result.replace(keyword, " ")
    result = re.sub(r"\s+", " ", result).strip(" ：:，,。！？!?的")
    if result in ("附近", "附近的"):
        return ""
    return result


def _is_location_only(text: str) -> bool:
    compact = _compact(text)
    if not compact:
        return False
    return bool(_extract_location(text)) and not _has_any(compact, PARKING_KEYWORDS + BIKE_KEYWORDS + BUS_KEYWORDS)


def _score_for(compact: str, keywords: tuple[str, ...], weight: float) -> float:
    matched = sum(1 for keyword in keywords if keyword.lower() in compact)
    if not matched:
        return 0.0
    return min(weight + (matched - 1) * 0.08, 0.72)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text)).lower()


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _intent(
    name: str,
    confidence: float,
    normalized: str,
    reply_style: str = "search",
    **entities: str | bool,
) -> UserIntent:
    clean_entities = {key: value for key, value in entities.items() if value not in ("", None, False)}
    return UserIntent(
        name=name,
        confidence=round(confidence, 2),
        entities=clean_entities,
        normalized_text=normalized,
        reply_style=reply_style,
    )
