from __future__ import annotations

import re

import requests
from requests import RequestException

from config import Config
from services.tdx_client import TDXError, tdx_client


def _text(value, fallback: str = "") -> str:
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
        return ""
    if spaces <= 0:
        return "已滿"
    if spaces <= 20:
        return "車位緊張"
    return "尚有車位"


def _opendata_status(rgb: str | None) -> str:
    return {
        "G": "尚有車位",
        "Y": "車位緊張",
        "R": "已滿",
        "B": "",
    }.get(str(rgb or "").upper(), "")


def _to_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_int(*values) -> int | None:
    for value in values:
        parsed = _to_int(value)
        if parsed is not None:
            return parsed
    return None


def _sum_available_details(details) -> int | None:
    if not isinstance(details, list):
        return None
    total = 0
    found = False
    for detail in details:
        if not isinstance(detail, dict):
            continue
        spaces = _first_int(
            detail.get("AvailableSpaces"),
            detail.get("AvailableCar"),
            detail.get("AvailableCarCount"),
            detail.get("AvailableSpace"),
            detail.get("Vacancy"),
        )
        if spaces is not None:
            total += spaces
            found = True
    return total if found else None


def _available_spaces(item: dict) -> int | None:
    return _first_int(
        item.get("AvailableSpaces"),
        item.get("AvailableCar"),
        item.get("AvailableCarCount"),
        item.get("AvailableSpace"),
        item.get("AvailableParkingSpaces"),
        item.get("SurplusSpace"),
        item.get("LeftSpace"),
        item.get("Vacancy"),
        item.get("Vacancies"),
        _sum_available_details(item.get("AvailableSpacesDetail")),
        _sum_available_details(item.get("ParkingAvailabilities")),
    )


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
            parking_id or "停車場",
        )
        address = (
            _text(lot.get("Address"), "")
            or _text(lot.get("CarParkAddress"), "")
            or _text(item.get("Address"), "")
        )
        spaces = _available_spaces(item)
        total_spaces = _first_int(
            item.get("TotalSpaces"),
            item.get("TotalCar"),
            item.get("TotalSpace"),
            item.get("ParkingSpaces"),
            lot.get("TotalSpaces"),
            lot.get("TotalCar"),
            lot.get("TotalSpace"),
            lot.get("CarParkCapacity"),
            lot.get("ParkingSpaces"),
        )

        results.append(
            {
                "name": name,
                "available_spaces": spaces,
                "total_spaces": total_spaces,
                "address": address,
                "status_text": _parking_status(spaces),
                "update_time": item.get("UpdateTime") or item.get("SrcUpdateTime") or "",
                "fare_description": _text(lot.get("FareDescription"), ""),
                "open_time": _text(
                    lot.get("OperationTime") or lot.get("BusinessHours"),
                    "",
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
        available_spaces = _first_int(
            item.get("AvailableCar"),
            item.get("availableCar"),
            item.get("AvailableSpaces"),
            item.get("availableSpaces"),
            item.get("SurplusSpace"),
            item.get("LeftSpace"),
            item.get("Vacancy"),
        )
        total_car = _first_int(
            item.get("TotalCar"),
            item.get("totalCar"),
            item.get("TotalSpaces"),
            item.get("totalSpaces"),
        )
        available_rgb = item.get("AvailableCarRGB")
        results.append(
            {
                "name": item.get("Position") or "停車場",
                "available_spaces": available_spaces,
                "total_spaces": total_car,
                "address": item.get("KeyWord", ""),
                "status_text": _parking_status(available_spaces) or _opendata_status(available_rgb),
                "update_time": "",
                "fare_description": "",
                "open_time": "",
                "signal": available_rgb or "",
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
        detail_lines = ["", f"{index}. 停車場名稱：{lot['name']}"]
        if isinstance(lot.get("available_spaces"), int):
            detail_lines.append(f"剩餘車位：{lot['available_spaces']} 格")
        if lot.get("total_spaces") not in (None, ""):
            detail_lines.append(f"總車位：{lot.get('total_spaces')}")
        if lot.get("status_text"):
            detail_lines.append(f"狀態：{lot.get('status_text')}")
        if lot.get("address") not in (None, ""):
            detail_lines.append(f"地址：{lot['address']}")
        if lot.get("fare_description"):
            detail_lines.append(f"收費：{lot['fare_description']}")
        if lot.get("open_time"):
            detail_lines.append(f"營業時間：{lot['open_time']}")
        lines.extend(
            detail_lines
        )
    return "\n".join(lines)


def reply_parking() -> str:
    try:
        parking_lots = search_parking()
    except Exception:
        return "停車場查詢暫時無法使用，請稍後再試。"

    return format_parking_text(parking_lots)
