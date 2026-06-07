from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from repositories.subscription_repository import SubscriptionRepository
from services.bus_service import parse_bus_route


SAMPLE_ARRIVALS = [
    {
        "route_name": "300",
        "stop_name": "臺中車站",
        "direction": "去程",
        "destination": "靜宜大學",
        "estimate_seconds": 180,
        "arrival_text": "約 3 分鐘",
        "stop_status": "正常",
        "update_time": "2026-06-08T14:32:00+08:00",
    }
]

SAMPLE_STATIONS = [
    {
        "station_name": "YouBike 台中車站",
        "available_rent": 12,
        "available_return": 8,
        "service_status": 1,
        "status_text": "正常營運",
        "address": "台中市中區台灣大道一段",
        "update_time": "2026-06-08T14:32:00+08:00",
    }
]

SAMPLE_PARKING = [
    {
        "name": "台中車站停車場",
        "available_spaces": 42,
        "total_spaces": 120,
        "address": "台中市中區",
        "status_text": "尚有車位",
        "update_time": "2026-06-08T14:32:00+08:00",
    }
]


class BusRouteParserTest(unittest.TestCase):
    def test_parse_common_bus_queries(self) -> None:
        cases = {
            "300": "300",
            "300公車": "300",
            "公車300": "300",
            "查300": "300",
            "300 到站": "300",
            "查詢 300": "300",
            "查詢 300 到站": "300",
            "查詢300到站": "300",
            "公車 300 往台中車站": "300",
            "300 往靜宜大學": "300",
            "幫我查 300": "300",
            "我要搭 300": "300",
            "300多久到": "300",
            "300還有多久": "300",
            "300 即時動態": "300",
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_bus_route(text), expected)

    def test_parse_empty_when_no_route(self) -> None:
        self.assertEqual(parse_bus_route("使用說明"), "")


class TestEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.subscription_file = Path(self.temp_dir.name) / "subscriptions.json"
        app_module.subscription_repository = SubscriptionRepository(self.subscription_file)
        app_module.Config.TEST_TOKEN = ""
        app_module.Config.INTERNAL_API_TOKEN = ""
        self.client = app_module.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def get_reply(self, text: str) -> dict:
        response = self.client.get("/test", query_string={"text": text})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        return payload["replies"][0]

    def test_static_and_subscription_inputs(self) -> None:
        expectations = {
            "主選單": "flex",
            "hi": "flex",
            "使用說明": "flex",
            "服務狀態": "flex",
            "訂閱300": "flex",
            "我的訂閱": "flex",
            "取消訂閱300": "flex",
        }

        for text, expected_type in expectations.items():
            with self.subTest(text=text):
                self.assertEqual(self.get_reply(text)["type"], expected_type)

    def test_bus_inputs_return_flex(self) -> None:
        bus_inputs = [
            "300",
            "300公車",
            "公車300",
            "查300",
            "查詢300到站",
            "查詢 300 到站",
            "300多久到",
            "幫我查 300 多久到",
        ]

        with patch.object(app_module, "get_bus_eta", return_value=SAMPLE_ARRIVALS):
            for text in bus_inputs:
                with self.subTest(text=text):
                    reply = self.get_reply(text)
                    self.assertEqual(reply["type"], "flex")
                    self.assertEqual(reply["alt_text"], "300 公車即時到站資訊")

    def test_youbike_and_parking_inputs_return_flex(self) -> None:
        with (
            patch.object(app_module, "search_youbike", return_value=SAMPLE_STATIONS),
            patch.object(app_module, "search_parking", return_value=SAMPLE_PARKING),
        ):
            self.assertEqual(self.get_reply("YouBike台中車站")["type"], "flex")
            self.assertEqual(self.get_reply("ubike台中車站")["type"], "flex")
            self.assertEqual(self.get_reply("腳踏車台中車站")["type"], "flex")
            self.assertEqual(self.get_reply("停車場")["type"], "flex")
            self.assertEqual(self.get_reply("查停車")["type"], "flex")

    def test_unknown_input_returns_flex_hint(self) -> None:
        reply = self.get_reply("@@@")
        self.assertEqual(reply["type"], "flex")
        self.assertEqual(reply["alt_text"], "台中交通小幫手查詢提示")

    def test_internal_push_requires_token(self) -> None:
        app_module.Config.INTERNAL_API_TOKEN = "secret"
        self.assertEqual(self.client.post("/internal/push-daily").status_code, 401)

        with (
            patch.object(app_module.subscription_repository, "all", return_value={}),
            patch.object(app_module, "line_bot_api"),
        ):
            response = self.client.post(
                "/internal/push-daily",
                headers={"X-Internal-Token": "secret"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["pushed_messages"], 0)


if __name__ == "__main__":
    unittest.main()
