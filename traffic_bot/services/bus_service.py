from __future__ import annotations

from urllib.parse import quote

from services.tdx_client import TDXError, tdx_client


STOP_STATUS = {
    0: "正常",
    1: "尚未發車",
    2: "交管不停靠",
    3: "末班車已過",
    4: "今日未營運",
}

DIRECTIONS = {
    0: "去程",
    1: "返程",
    2: "迴圈",
    255: "未知",
}


def _zh_tw(value: dict | None, fallback: str = "未提供") -> str:
    if not isinstance(value, dict):
        return fallback
    return value.get("Zh_tw") or value.get("En") or fallback


def _format_eta(seconds: int | None, stop_status: int | None) -> str:
    if seconds is None:
        return STOP_STATUS.get(stop_status, "未提供即時到站時間")
    if seconds <= 60:
        return "即將到站"
    minutes = round(seconds / 60)
    return f"約 {minutes} 分鐘"


def parse_bus_route(text: str) -> str:
    route = (
        text.replace("公車", "")
        .replace("路線", "")
        .replace("查詢", "")
        .replace("訂閱", "")
        .replace("取消", "")
        .strip()
    )
    return route


def get_bus_eta(route_name: str, limit: int = 3) -> list[dict]:
    route_name = route_name.strip()
    if not route_name:
        return []

    data = tdx_client.get(
        f"v2/Bus/EstimatedTimeOfArrival/City/Taichung/{quote(route_name)}",
        params={"$top": 100},
    )

    arrivals = []
    for item in data:
        estimate_time = item.get("EstimateTime")
        stop_status = item.get("StopStatus")
        if estimate_time is None and stop_status not in (0, 1):
            continue

        arrivals.append(
            {
                "route_name": _zh_tw(item.get("RouteName"), route_name),
                "stop_name": _zh_tw(item.get("StopName")),
                "direction": DIRECTIONS.get(item.get("Direction"), "未知"),
                "estimate_seconds": estimate_time,
                "arrival_text": _format_eta(estimate_time, stop_status),
                "stop_status": STOP_STATUS.get(stop_status, "未知"),
            }
        )

    arrivals.sort(
        key=lambda row: (
            row["estimate_seconds"] is None,
            row["estimate_seconds"] if row["estimate_seconds"] is not None else 999999,
        )
    )
    return arrivals[:limit]


def reply_bus_eta(route_name: str) -> str:
    try:
        arrivals = get_bus_eta(route_name)
    except TDXError as exc:
        return f"公車查詢暫時無法使用。\n原因：{exc}"
    except Exception:
        return "公車查詢發生未預期錯誤，請稍後再試。"

    if not arrivals:
        return f"查不到 {route_name} 公車的即時到站資料，請確認路線名稱是否正確。"

    lines = [f"台中公車 {route_name} 最近到站資訊"]
    for index, item in enumerate(arrivals, start=1):
        lines.extend(
            [
                "",
                f"{index}. 路線名稱：{item['route_name']}",
                f"站牌：{item['stop_name']}",
                f"下一班到站時間：{item['arrival_text']}",
                f"行駛方向：{item['direction']}",
            ]
        )
    return "\n".join(lines)
