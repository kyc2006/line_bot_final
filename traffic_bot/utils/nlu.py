from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from services.bus_service import parse_bus_destination, parse_bus_route
from services.bike_service import parse_youbike_query
from services.parking_service import parse_parking_query


@dataclass(frozen=True)
class UserIntent:
    name: str
    confidence: float
    entities: dict[str, str] = field(default_factory=dict)
    normalized_text: str = ""

    @property
    def query(self) -> str:
        return self.entities.get("query", "")

    @property
    def route(self) -> str:
        return self.entities.get("route", "")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("臺", "台")
    normalized = re.sub(r"\s+", " ", normalized).strip(" ：:，,。！？!?")
    return normalized


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text)).lower()


def _intent(name: str, confidence: float, normalized: str, **entities: str) -> UserIntent:
    clean_entities = {key: value for key, value in entities.items() if value}
    return UserIntent(name=name, confidence=confidence, entities=clean_entities, normalized_text=normalized)


def parse_user_intent(text: str) -> UserIntent:
    normalized = normalize_text(text)
    compact = _compact(normalized)
    lower = normalized.lower()

    if not normalized:
        return _intent("unknown", 0.1, normalized)

    route = parse_bus_route(normalized)
    destination = parse_bus_destination(normalized)

    if _has_any(compact, ("取消訂閱", "不要訂閱", "取消追蹤", "移除")) and route:
        return _intent("bus_unsubscribe", 0.95, normalized, route=route, destination=destination)

    if _has_any(compact, ("訂閱", "提醒", "追蹤")) and route:
        return _intent("bus_subscribe", 0.94, normalized, route=route, destination=destination)

    if compact in ("我的訂閱", "訂閱清單") or _has_any(compact, ("追蹤了哪些公車", "有訂閱什麼", "查看我的公車")):
        return _intent("subscription_list", 0.94, normalized)

    if compact in ("主選單", "回主選單", "選單", "menu") or _has_any(compact, ("可以做什麼", "能做什麼")):
        return _intent("main_menu", 0.95, normalized)

    if compact in ("使用說明", "help", "說明", "怎麼用"):
        return _intent("help", 0.95, normalized)

    if compact in ("服務狀態", "資料來源", "status") or _has_any(compact, ("系統正常嗎", "tdx正常嗎", "機器人正常嗎")):
        return _intent("status", 0.95, normalized)

    if compact in ("重新查詢", "重新輸入"):
        return _intent("retry_guide", 0.82, normalized)

    if compact in ("公車", "查公車", "bus", "重新整理"):
        return _intent("bus_guide", 0.9, normalized)

    if compact == "熱門路線":
        return _intent("popular_routes", 0.95, normalized)

    if _looks_like_bike_query(compact, lower):
        query = _extract_bike_query(normalized)
        if query:
            return _intent("bike_search", 0.9, normalized, query=query)
        return _intent("bike_guide", 0.88, normalized)

    if _looks_like_parking_query(compact):
        query = _extract_parking_query(normalized)
        if query:
            return _intent("parking_search", 0.9, normalized, query=query)
        return _intent("parking_guide", 0.86, normalized)

    if route:
        return _intent("bus_search", 0.92 if compact == route.lower() else 0.86, normalized, route=route, destination=destination)

    if "公車" in compact:
        return _intent("bus_guide", 0.75, normalized)

    if compact in ("hi", "hello", "嗨", "你好", "哈囉", "開始"):
        return _intent("greeting", 0.9, normalized)

    return _intent("unknown", 0.2, normalized)


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _looks_like_bike_query(compact: str, lower: str) -> bool:
    return (
        "youbike" in lower
        or "ubike" in lower
        or "腳踏車" in compact
        or "自行車" in compact
        or "共享單車" in compact
        or compact == "換個地點"
    )


def _looks_like_parking_query(compact: str) -> bool:
    return (
        "停車" in compact
        or "車位" in compact
        or "parking" in compact
        or compact == "換個區域"
    )


def _extract_bike_query(text: str) -> str:
    if _compact(text) == "換個地點":
        return ""
    query = parse_youbike_query(text)
    query = _remove_place_fillers(query)
    return query


def _extract_parking_query(text: str) -> str:
    if _compact(text) == "換個區域":
        return ""
    query = parse_parking_query(text)
    query = _remove_place_fillers(query)
    return query


def _remove_place_fillers(query: str) -> str:
    result = normalize_text(query)
    for keyword in (
        "附近",
        "哪裡",
        "哪里",
        "哪邊",
        "可以",
        "有嗎",
        "有沒有",
        "幫我",
        "一下",
        "我想",
        "找附近的",
        "還有",
        "有沒有",
        "有",
        "嗎",
        "借",
        "位",
    ):
        result = result.replace(keyword, " ")
    result = re.sub(r"\s+", " ", result).strip(" ：:，,。！？!?的")
    if result in ("附近", "附近的"):
        return ""
    return result
