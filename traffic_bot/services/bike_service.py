from __future__ import annotations

from services.tdx_client import TDXError, tdx_client


def _zh_tw(value: dict | None, fallback: str = "未提供") -> str:
    if not isinstance(value, dict):
        return fallback
    return value.get("Zh_tw") or value.get("En") or fallback


def _normalize_keyword(keyword: str) -> str:
    return (
        keyword.replace("YouBike", "")
        .replace("youbike", "")
        .replace("Ubike", "")
        .replace("ubike", "")
        .replace("查詢", "")
        .strip()
    )


def _station_name(item: dict) -> str:
    return _zh_tw(item.get("StationName"), item.get("StationID", "未提供站名"))


def _station_key(item: dict) -> str:
    return item.get("StationUID") or item.get("StationID") or ""


def search_youbike(keyword: str, limit: int = 3) -> list[dict]:
    keyword = _normalize_keyword(keyword)
    if not keyword:
        return []

    stations = tdx_client.get("v2/Bike/Station/City/Taichung", params={"$top": 3000})
    availability = tdx_client.get("v2/Bike/Availability/City/Taichung", params={"$top": 3000})
    availability_map = {_station_key(item): item for item in availability}

    matches = []
    for station in stations:
        name = _station_name(station)
        if keyword not in name:
            continue

        status = availability_map.get(_station_key(station), {})
        matches.append(
            {
                "station_name": name,
                "available_rent": status.get("AvailableRentBikes", 0),
                "available_return": status.get("AvailableReturnBikes", 0),
                "service_status": status.get("ServiceStatus"),
            }
        )

    return matches[:limit]


def reply_youbike(keyword: str) -> str:
    try:
        stations = search_youbike(keyword)
    except TDXError as exc:
        return f"YouBike 查詢暫時無法使用。\n原因：{exc}"
    except Exception:
        return "YouBike 查詢發生未預期錯誤，請稍後再試。"

    query = _normalize_keyword(keyword)
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
            ]
        )
    return "\n".join(lines)
