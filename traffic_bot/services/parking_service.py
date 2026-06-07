from __future__ import annotations

import re

import requests
from requests import RequestException

from config import Config
from services.tdx_client import TDXError, tdx_client


def _text(value, fallback: str = "未提供") -> str:
    if isinstance(value, dict):
        return value.get("Zh_tw") or value.get("En") or fallback
    if value is None:
        return fallback
    return str(value) or fallback


def _canonical(value: str) -> str:
    return re.sub(r"\s+", "", value.lower().replace("臺", "台"))


def parse_parking_query(text: str) -> str:
    query = text.strip()
    for keyword in ("停車場", "停車", "查詢", "查", "找", "車位", "空位"):
        query = query.replace(keyword, " ")
    query = re.sub(r"\s+", " ", query).strip(" ：:，,。")
    if query in ("附近", "附近的"):
        return ""
    return query


def _parking_id(item: dict) -> str:
    return item.get("CarParkID") or item.get("ParkingID") or item.get("ID") or ""


def _parking_status(spaces: int | None) -> str:
    if spaces is None:
        return "資料更新中"
    if spaces <= 0:
        return "已滿"
    if spaces <= 10:
        return "車位緊張"
    return "尚有車位"


def _opendata_status(rgb: str | None) -> str:
    return {
        "G": "尚有車位",
        "Y": "車位緊張",
        "R": "已滿",
        "B": "資料更新中",
    }.get(str(rgb or "").upper(), "資料更新中")


def _to_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_tdx_parking() -> list[dict]:
    availability = tdx_client.get(
        "v1/Parking/OffStreet/ParkingAvailability/City/Taichung",
        params={"$top": 1000},
    )
    lots = tdx_client.get("v1/Parking/OffStreet/CarPark/City/Taichung", params={"$top": 1000})
    if not isinstance(availability, list) or not isinstance(lots, list):
        raise TDXError("停車場 API 回傳格式異常。")

    lot_map = {_parking_id(item): item for item in lots}
    results = []
    for item in availability:
        parking_id = _parking_id(item)
        lot = lot_map.get(parking_id, {})
        name = _text(
            item.get("CarParkName") or lot.get("CarParkName") or lot.get("ParkingName"),
            parking_id or "未提供名稱",
        )
        address = (
            _text(lot.get("Address"), "")
            or _text(lot.get("CarParkAddress"), "")
            or _text(item.get("Address"), "")
            or "TDX 尚未提供此欄位"
        )
        spaces = _to_int(item.get("AvailableSpaces"))
        if spaces is None:
            spaces = _to_int(item.get("AvailableCar"))
        total_spaces = (
            _to_int(item.get("TotalSpaces"))
            or _to_int(lot.get("TotalSpaces"))
            or _to_int(lot.get("CarParkCapacity"))
        )

        results.append(
            {
                "name": name,
                "available_spaces": spaces if spaces is not None else "未提供",
                "total_spaces": total_spaces or "未提供",
                "address": address,
                "status_text": _parking_status(spaces),
                "update_time": item.get("UpdateTime") or item.get("SrcUpdateTime") or "",
                "fare_description": _text(lot.get("FareDescription"), "TDX 尚未提供此欄位"),
                "open_time": _text(
                    lot.get("OperationTime") or lot.get("BusinessHours"),
                    "TDX 尚未提供此欄位",
                ),
                "source": "TDX",
            }
        )

    if not results:
        return _load_opendata_parking()

    results.sort(
        key=lambda row: (
            not isinstance(row["available_spaces"], int),
            -(row["available_spaces"] if isinstance(row["available_spaces"], int) else -1),
        )
    )
    return results


def _load_opendata_parking() -> list[dict]:
    try:
        response = requests.get(Config.TAICHUNG_PARKING_OPENDATA_URL, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (RequestException, ValueError) as exc:
        raise TDXError("台中停車場 OpenData 暫時無法取得。") from exc
    if not isinstance(data, list):
        raise TDXError("台中停車場 OpenData 回傳格式異常。")

    results = []
    for item in data:
        total_car = _to_int(item.get("TotalCar"))
        available_rgb = item.get("AvailableCarRGB")
        results.append(
            {
                "name": item.get("Position", "未提供名稱"),
                "available_spaces": f"燈號 {available_rgb or '未提供'}",
                "total_spaces": total_car or "未提供",
                "address": item.get("KeyWord", "未提供地址"),
                "status_text": _opendata_status(available_rgb),
                "update_time": "",
                "fare_description": "OpenData 尚未提供此欄位",
                "open_time": "OpenData 尚未提供此欄位",
                "source": "台中 OpenData",
            }
        )
    return results


def _filter_lots(lots: list[dict], query: str) -> list[dict]:
    if not query:
        return lots
    query_key = _canonical(query)
    return [
        lot
        for lot in lots
        if query_key in _canonical(f"{lot.get('name', '')} {lot.get('address', '')}")
    ]


def search_parking(keyword: str = "", limit: int = 6) -> list[dict]:
    query = parse_parking_query(keyword)
    try:
        lots = _load_tdx_parking()
    except TDXError:
        lots = _load_opendata_parking()
    return _filter_lots(lots, query)[:limit]


def format_parking_text(parking_lots: list[dict]) -> str:
    if not parking_lots:
        return "目前查不到台中停車場資料。"

    lines = ["台中停車場剩餘車位"]
    for index, lot in enumerate(parking_lots, start=1):
        lines.extend(
            [
                "",
                f"{index}. 停車場名稱：{lot['name']}",
                f"剩餘車位：{lot['available_spaces']}",
                f"總車位：{lot.get('total_spaces', '未提供')}",
                f"狀態：{lot.get('status_text', '資料更新中')}",
                f"地址：{lot['address']}",
            ]
        )
    return "\n".join(lines)


def reply_parking() -> str:
    try:
        parking_lots = search_parking()
    except Exception:
        return "停車場查詢暫時無法使用，請稍後再試。"

    return format_parking_text(parking_lots)
