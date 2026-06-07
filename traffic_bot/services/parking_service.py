from __future__ import annotations

import requests

from config import Config
from services.tdx_client import TDXError, tdx_client


def _zh_tw(value: dict | None, fallback: str = "未提供") -> str:
    if not isinstance(value, dict):
        return fallback
    return value.get("Zh_tw") or value.get("En") or fallback


def _parking_id(item: dict) -> str:
    return item.get("CarParkID") or item.get("ParkingID") or item.get("ID") or ""


def _load_tdx_parking(limit: int) -> list[dict]:
    availability = tdx_client.get(
        "v1/Parking/OffStreet/ParkingAvailability/City/Taichung",
        params={"$top": 1000},
    )
    lots = tdx_client.get("v1/Parking/OffStreet/CarPark/City/Taichung", params={"$top": 1000})

    lot_map = {_parking_id(item): item for item in lots}
    results = []
    for item in availability:
        parking_id = _parking_id(item)
        lot = lot_map.get(parking_id, {})
        name = _zh_tw(
            item.get("CarParkName") or lot.get("CarParkName") or lot.get("ParkingName"),
            parking_id or "未提供名稱",
        )
        address = (
            lot.get("Address")
            or _zh_tw(lot.get("CarParkAddress"))
            or item.get("Address")
            or "未提供地址"
        )
        spaces = item.get("AvailableSpaces")
        if spaces is None:
            spaces = item.get("AvailableCar")

        results.append(
            {
                "name": name,
                "available_spaces": spaces if spaces is not None else "未提供",
                "address": address,
            }
        )

    if not results:
        return _load_opendata_parking(limit)

    results.sort(
        key=lambda row: (
            not isinstance(row["available_spaces"], int),
            -(row["available_spaces"] if isinstance(row["available_spaces"], int) else -1),
        )
    )
    return results[:limit]


def _load_opendata_parking(limit: int) -> list[dict]:
    response = requests.get(Config.TAICHUNG_PARKING_OPENDATA_URL, timeout=Config.REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data[:limit]:
        results.append(
            {
                "name": item.get("Position", "未提供名稱"),
                "available_spaces": f"即時剩餘數請以燈號參考：{item.get('AvailableCarRGB', '未提供')}",
                "address": item.get("KeyWord", "未提供地址"),
            }
        )
    return results


def search_parking(limit: int = 5) -> list[dict]:
    try:
        return _load_tdx_parking(limit)
    except TDXError:
        return _load_opendata_parking(limit)


def reply_parking() -> str:
    try:
        parking_lots = search_parking()
    except Exception:
        return "停車場查詢暫時無法使用，請稍後再試。"

    if not parking_lots:
        return "目前查不到台中停車場資料。"

    lines = ["台中停車場剩餘車位"]
    for index, lot in enumerate(parking_lots, start=1):
        lines.extend(
            [
                "",
                f"{index}. 停車場名稱：{lot['name']}",
                f"剩餘車位：{lot['available_spaces']}",
                f"地址：{lot['address']}",
            ]
        )
    return "\n".join(lines)
