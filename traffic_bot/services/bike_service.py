from __future__ import annotations

import re

from services.tdx_client import TDXError, tdx_client


def _text(value, fallback: str = "未提供") -> str:
    if isinstance(value, dict):
        return value.get("Zh_tw") or value.get("En") or fallback
    if value is None:
        return fallback
    return str(value) or fallback


def _canonical(value: str) -> str:
    return re.sub(r"\s+", "", value.lower().replace("臺", "台"))


def _to_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_youbike_query(text: str) -> str:
    query = text.strip()
    query = re.sub(r"(?i)youbike|ubike", " ", query)
    for keyword in ("腳踏車", "自行車", "公共自行車", "找", "查詢", "查", "站點"):
        query = query.replace(keyword, " ")
    query = re.sub(r"\s+", " ", query).strip(" ：:，,。")
    if query in ("附近", "附近的", "附近其他"):
        return ""
    return query


def _station_name(item: dict) -> str:
    return _text(item.get("StationName"), item.get("StationID", "未提供站名"))


def _station_key(item: dict) -> str:
    return item.get("StationUID") or item.get("StationID") or ""


def _service_status_label(status: int | None, rent: int | None, returns: int | None) -> str:
    base = {
        0: "停止營運",
        1: "正常營運",
        2: "暫停營運",
    }.get(status, "資料更新中")
    if base != "正常營運":
        return base
    if rent == 0:
        return "車輛不足"
    if returns == 0:
        return "空位不足"
    return base


def search_youbike(keyword: str, limit: int = 6) -> list[dict]:
    keyword = parse_youbike_query(keyword)
    if not keyword:
        return []

    stations = tdx_client.get("v2/Bike/Station/City/Taichung", params={"$top": 3000})
    availability = tdx_client.get("v2/Bike/Availability/City/Taichung", params={"$top": 3000})
    if not isinstance(stations, list) or not isinstance(availability, list):
        raise TDXError("YouBike API 回傳格式異常。")

    availability_map = {_station_key(item): item for item in availability}
    query_key = _canonical(keyword)

    matches = []
    for station in stations:
        name = _station_name(station)
        address = _text(station.get("StationAddress"), "")
        haystack = _canonical(f"{name} {address} {station.get('StationID', '')}")
        if query_key not in haystack:
            continue

        status = availability_map.get(_station_key(station), {})
        rent = _to_int(status.get("AvailableRentBikes"))
        returns = _to_int(status.get("AvailableReturnBikes"))
        matches.append(
            {
                "station_name": name,
                "available_rent": rent if rent is not None else "資料更新中",
                "available_return": returns if returns is not None else "資料更新中",
                "service_status": _to_int(status.get("ServiceStatus")),
                "status_text": _service_status_label(_to_int(status.get("ServiceStatus")), rent, returns),
                "address": address or "TDX 尚未提供此欄位",
                "update_time": status.get("UpdateTime") or status.get("SrcUpdateTime") or "",
                "capacity": station.get("BikesCapacity") or "TDX 尚未提供此欄位",
            }
        )

    return matches[:limit]


def format_youbike_text(keyword: str, stations: list[dict]) -> str:
    query = parse_youbike_query(keyword)
    if not query:
        return "目前尚未開啟定位查詢，請輸入地點，例如：YouBike 台中車站。"
    if not stations:
        return f"查不到「{query or keyword}」附近的 YouBike 站點，請試試更短的站名關鍵字。"

    lines = [f"YouBike「{query}」查詢結果"]
    for index, station in enumerate(stations, start=1):
        lines.extend(
            [
                "",
                f"{index}. 站點名稱：{station['station_name']}",
                f"可借車輛數：{station['available_rent']}",
                f"可還車位數：{station['available_return']}",
                f"狀態：{station.get('status_text', '資料更新中')}",
            ]
        )
    return "\n".join(lines)


def reply_youbike(keyword: str) -> str:
    try:
        stations = search_youbike(keyword)
    except TDXError:
        return "目前 YouBike 資料暫時無法取得，請稍後再試。"
    except Exception:
        return "目前 YouBike 資料暫時無法取得，請稍後再試。"

    return format_youbike_text(keyword, stations)
