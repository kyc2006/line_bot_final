from __future__ import annotations

import re
from urllib.parse import quote

from services.tdx_client import TDXError, tdx_client


STOP_STATUS = {
    0: "正常",
    1: "尚未發車",
    2: "交管不停靠",
    3: "末班已過",
    4: "今日未營運",
}

DIRECTIONS = {
    0: "去程",
    1: "返程",
    2: "迴圈",
    255: "未知",
}

ROUTE_PATTERN = re.compile(r"[A-Za-z\u4e00-\u9fff]*\d+[A-Za-z0-9\u4e00-\u9fff]*")
BUS_KEYWORDS = (
    "幫我",
    "我要搭",
    "想搭",
    "搭乘",
    "搭",
    "公車",
    "路線",
    "查詢",
    "查",
    "多久到",
    "還有多久",
    "到站",
    "即時",
    "動態",
    "資訊",
    "預估",
    "時間",
)


def _zh_tw(value: dict | None, fallback: str = "未提供") -> str:
    if not isinstance(value, dict):
        return fallback
    return value.get("Zh_tw") or value.get("En") or fallback


def format_eta_status(seconds: int | None, stop_status: int | None) -> str:
    if seconds is None:
        return STOP_STATUS.get(stop_status, "資料更新中")
    if seconds <= 60:
        return "即將進站"
    minutes = round(seconds / 60)
    return f"約 {minutes} 分鐘"


def parse_bus_route(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""

    normalized = normalized.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    normalized = re.sub(r"\s+", " ", normalized)
    route_area = re.split(r"\s*往\s*", normalized, maxsplit=1)[0]
    route_area = route_area.replace("取消訂閱", " ").replace("訂閱", " ")

    for keyword in BUS_KEYWORDS:
        route_area = route_area.replace(keyword, " ")

    route_area = re.sub(r"\s+", " ", route_area).strip(" ：:，,。")
    if not route_area:
        return ""

    match = ROUTE_PATTERN.search(route_area)
    if match:
        return match.group(0).strip(" ：:，,。")

    return ""


def parse_bus_destination(text: str) -> str:
    normalized = text.strip()
    match = re.search(r"往\s*([^\s，,。！？!?]+)", normalized)
    if not match:
        return ""
    return match.group(1).strip(" ：:，,。")


def _matches_destination(item: dict, destination: str) -> bool:
    if not destination:
        return True
    fields = (
        item.get("destination", ""),
        item.get("direction", ""),
        item.get("stop_name", ""),
    )
    return any(destination in str(field) for field in fields)


def get_bus_eta(route_name: str, limit: int = 6, destination: str = "") -> list[dict]:
    route_name = route_name.strip()
    if not route_name:
        return []

    data = tdx_client.get(
        f"v2/Bus/EstimatedTimeOfArrival/City/Taichung/{quote(route_name)}",
        params={"$top": 300},
    )

    arrivals = []
    for item in data:
        estimate_time = item.get("EstimateTime")
        stop_status = item.get("StopStatus")

        arrivals.append(
            {
                "route_name": _zh_tw(item.get("RouteName"), route_name),
                "stop_name": _zh_tw(item.get("StopName")),
                "direction": DIRECTIONS.get(item.get("Direction"), "未知"),
                "destination": _zh_tw(
                    item.get("DestinationStopName")
                    or item.get("DestinationStationName")
                    or item.get("TripHeadSign"),
                    "",
                ),
                "estimate_seconds": estimate_time,
                "arrival_text": format_eta_status(estimate_time, stop_status),
                "stop_status": STOP_STATUS.get(stop_status, "未知"),
                "update_time": item.get("UpdateTime") or item.get("SrcUpdateTime") or "",
            }
        )

    arrivals.sort(
        key=lambda row: (
            row["estimate_seconds"] is None,
            row["estimate_seconds"] if row["estimate_seconds"] is not None else 999999,
        )
    )
    if destination:
        destination_matches = [item for item in arrivals if _matches_destination(item, destination)]
        if destination_matches:
            return destination_matches[:limit]
    return arrivals[:limit]


def format_bus_eta_text(route_name: str, arrivals: list[dict]) -> str:
    if not arrivals:
        return "目前查不到這條公車的即時資料，請確認路線是否正確，或稍後再試。"

    lines = [f"🚌 {route_name} 公車即時到站"]
    update_time = arrivals[0].get("update_time")
    if update_time:
        lines.append(f"🔄 資料更新時間：{update_time}")

    for index, item in enumerate(arrivals, start=1):
        lines.extend(
            [
                "",
                f"{index}. 🚌 路線：{item['route_name']}",
                f"📍 站牌：{item['stop_name']}",
                f"⏱ 到站：{item['arrival_text']}",
                f"方向：{item['destination'] or item['direction']}",
            ]
        )
    return "\n".join(lines)


def reply_bus_eta(route_name: str, destination: str = "") -> str:
    if not route_name:
        return "請輸入要查詢的公車路線，例如：300、公車 300、查 300 到站"

    try:
        arrivals = get_bus_eta(route_name, destination=destination)
    except TDXError:
        return "目前查不到這條公車的即時資料，請確認路線是否正確，或稍後再試。"
    except Exception:
        return "目前查不到這條公車的即時資料，請確認路線是否正確，或稍後再試。"

    if not arrivals:
        return "目前查不到這條公車的即時資料，請確認路線是否正確，或稍後再試。"

    return format_bus_eta_text(route_name, arrivals)
