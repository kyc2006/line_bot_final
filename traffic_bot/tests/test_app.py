from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from flex.bike import youbike_bubble
from flex.common import help_bubble
from flex.menu import main_menu_bubble
from flex.parking import parking_bubble
from repositories.subscription_repository import SubscriptionRepository
from scripts.setup_rich_menu import (
    LINE_DATA_API_BASE,
    build_rich_menu,
    generate_rich_menu_image,
    upload_image,
)
from services.bike_service import parse_youbike_query
from services.bus_service import parse_bus_route
from services.parking_service import parse_parking_query


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


class PlaceQueryParserTest(unittest.TestCase):
    def test_parse_youbike_query(self) -> None:
        cases = {
            "YouBike 台中車站": "台中車站",
            "ubike逢甲": "逢甲",
            "腳踏車 靜宜": "靜宜",
            "找 YouBike 台中車站": "台中車站",
            "附近 YouBike": "",
            "YouBike": "",
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_youbike_query(text), expected)

    def test_parse_parking_query(self) -> None:
        cases = {
            "停車場": "",
            "查停車": "",
            "台中車站停車場": "台中車站",
            "西屯停車場": "西屯",
            "逢甲停車場": "逢甲",
            "附近停車場": "",
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_parking_query(text), expected)


class FlexContentTest(unittest.TestCase):
    def test_parking_shows_numeric_remaining_when_available(self) -> None:
        bubble = parking_bubble(SAMPLE_PARKING, query="西屯")
        payload = json.dumps(bubble, ensure_ascii=False)
        self.assertIn("剩餘 42 格", payload)
        self.assertIn("總車位：120", payload)

    def test_parking_hides_missing_fields_without_placeholders(self) -> None:
        bubble = parking_bubble(
            [
                {
                    "name": "西屯停車場",
                    "available_spaces": None,
                    "total_spaces": 120,
                    "address": "台中市西屯區",
                    "status_text": "尚有車位",
                    "fare_description": "",
                    "open_time": "",
                    "source": "台中 OpenData",
                }
            ],
            query="西屯",
        )
        payload = json.dumps(bubble, ensure_ascii=False)
        self.assertNotIn("剩餘", payload)
        self.assertIn("資料更新中", payload)
        self.assertIn("暫無即時車位", payload)
        for forbidden in ("未提供", "OpenData 未提供", "TDX 尚未提供", "None", "null", "N/A"):
            self.assertNotIn(forbidden, payload)

    def test_footer_button_actions_are_dispatchable(self) -> None:
        parking_payload = json.dumps(parking_bubble(SAMPLE_PARKING, query="西屯"), ensure_ascii=False)
        bike_payload = json.dumps(youbike_bubble("台中車站", SAMPLE_STATIONS), ensure_ascii=False)
        menu_payload = json.dumps(main_menu_bubble(), ensure_ascii=False)
        self.assertIn('"text": "西屯停車場"', parking_payload)
        self.assertIn('"text": "換個區域"', parking_payload)
        self.assertIn('"text": "YouBike 台中車站"', bike_payload)
        self.assertIn('"text": "換個地點"', bike_payload)
        self.assertIn('"text": "查公車"', menu_payload)
        self.assertIn('"text": "找 YouBike"', menu_payload)
        self.assertIn('"text": "查停車場"', menu_payload)

    def test_menu_and_help_are_multi_page_carousels(self) -> None:
        menu = main_menu_bubble()
        help_menu = help_bubble()
        self.assertEqual(menu["type"], "carousel")
        self.assertGreaterEqual(len(menu["contents"]), 5)
        self.assertEqual(help_menu["type"], "carousel")
        self.assertGreaterEqual(len(help_menu["contents"]), 5)

    def test_rich_menu_uses_message_actions_without_token(self) -> None:
        menu = build_rich_menu()
        payload = json.dumps(menu, ensure_ascii=False)
        self.assertNotIn("LINE_CHANNEL_ACCESS_TOKEN", payload)
        for text in ("查公車", "找 YouBike", "查停車場", "我的訂閱", "服務狀態", "使用說明"):
            self.assertIn(f'"text": "{text}"', payload)

    def test_rich_menu_image_can_be_generated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "rich_menu.png"
            generate_rich_menu_image(image_path)
            self.assertTrue(image_path.exists())
            header = image_path.read_bytes()[:24]
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(int.from_bytes(header[16:20], "big"), 2500)
            self.assertEqual(int.from_bytes(header[20:24], "big"), 1686)

    def test_rich_menu_upload_uses_line_data_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "rich_menu.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
            with patch("scripts.setup_rich_menu.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                upload_image("token", "richmenu-test", image_path)

        self.assertEqual(
            mock_post.call_args.args[0],
            f"{LINE_DATA_API_BASE}/richmenu/richmenu-test/content",
        )


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
        self.assertGreaterEqual(payload["message_count"], 1)
        return payload["replies"][0]

    def test_static_and_subscription_inputs(self) -> None:
        expectations = {
            "主選單": "flex",
            "hi": "flex",
            "使用說明": "flex",
            "查公車": "flex",
            "熱門路線": "flex",
            "服務狀態": "flex",
            "YouBike": "flex",
            "找 YouBike": "flex",
            "找YouBike": "flex",
            "停車": "flex",
            "查停車場": "flex",
            "重新整理": "flex",
            "重新查詢": "flex",
            "換個地點": "flex",
            "換個區域": "flex",
            "訂閱300": "flex",
            "我的訂閱": "flex",
            "取消訂閱300": "flex",
        }

        for text, expected_type in expectations.items():
            with self.subTest(text=text):
                self.assertEqual(self.get_reply(text)["type"], expected_type)

    def test_quick_replies_are_attached_to_guided_flows(self) -> None:
        cases = {
            "主選單": ("查公車", "找 YouBike", "查停車場", "我的訂閱"),
            "查公車": ("300", "301", "306", "307"),
            "找 YouBike": ("YouBike 台中車站", "YouBike 逢甲", "YouBike 靜宜"),
            "查停車場": ("台中車站停車場", "西屯停車場", "逢甲停車場"),
            "換個地點": ("YouBike 台中車站", "換個地點", "主選單"),
            "換個區域": ("台中車站停車場", "市政府停車場", "主選單"),
        }

        for text, expected_texts in cases.items():
            with self.subTest(text=text):
                reply = self.get_reply(text)
                self.assertGreater(reply["quick_reply_count"], 0)
                for expected_text in expected_texts:
                    self.assertIn(expected_text, reply["quick_reply_texts"])

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
                    self.assertIn("查詢 300", reply["quick_reply_texts"])
                    self.assertIn("訂閱300", reply["quick_reply_texts"])

    def test_youbike_and_parking_inputs_return_flex(self) -> None:
        with (
            patch.object(app_module, "search_youbike", return_value=SAMPLE_STATIONS),
            patch.object(app_module, "search_parking", return_value=SAMPLE_PARKING),
        ):
            bike_reply = self.get_reply("YouBike台中車站")
            self.assertEqual(bike_reply["type"], "flex")
            self.assertIn("YouBike 台中車站", bike_reply["quick_reply_texts"])
            self.assertEqual(self.get_reply("ubike台中車站")["type"], "flex")
            self.assertEqual(self.get_reply("腳踏車台中車站")["type"], "flex")
            self.assertEqual(self.get_reply("停車場")["type"], "flex")
            parking_reply = self.get_reply("西屯停車場")
            self.assertEqual(parking_reply["type"], "flex")
            self.assertIn("西屯停車場", parking_reply["quick_reply_texts"])

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
