from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from repositories.subscription_repository import SubscriptionRepository


SAMPLE_ARRIVALS = [
    {
        "route_name": "300",
        "stop_name": "臺中車站",
        "destination": "靜宜大學",
        "estimate_seconds": 180,
        "arrival_text": "約 3 分鐘",
        "stop_status": "正常",
    }
]

SAMPLE_STATIONS = [
    {
        "station_name": "YouBike 逢甲大學",
        "available_rent": 0,
        "available_return": 8,
        "status_text": "車輛不足",
    }
]

SAMPLE_PARKING = [
    {
        "name": "市政公園停車場",
        "available_spaces": 0,
        "total_spaces": 120,
        "status_text": "已滿",
    }
]


class MessageDispatcherIntentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        app_module.subscription_repository = SubscriptionRepository(
            Path(self.temp_dir.name) / "subscriptions.json"
        )
        app_module.Config.TEST_TOKEN = ""
        self.client = app_module.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def get_payload(self, text: str) -> dict:
        response = self.client.get("/test", query_string={"text": text})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_test_endpoint_reports_bus_intent(self) -> None:
        with patch.object(app_module, "get_bus_eta", return_value=SAMPLE_ARRIVALS):
            payload = self.get_payload("300多久到")

        self.assertEqual(payload["parsed_intent"], "bus_search")
        self.assertEqual(payload["extracted_entities"]["route"], "300")
        self.assertEqual(payload["replies"][0]["type"], "flex")
        self.assertGreater(payload["quick_reply_count"], 0)
        self.assertIn("查詢 300", payload["replies"][0]["quick_reply_texts"])

    def test_test_endpoint_reports_bike_intent(self) -> None:
        with patch.object(app_module, "search_youbike", return_value=SAMPLE_STATIONS):
            payload = self.get_payload("逢甲附近有YouBike嗎")

        self.assertEqual(payload["parsed_intent"], "bike_search")
        self.assertEqual(payload["extracted_entities"]["query"], "逢甲")
        self.assertEqual(payload["replies"][0]["type"], "flex")
        self.assertIn("YouBike 逢甲", payload["replies"][0]["quick_reply_texts"])

    def test_test_endpoint_reports_parking_intent(self) -> None:
        with patch.object(app_module, "search_parking", return_value=SAMPLE_PARKING):
            payload = self.get_payload("市政府附近還有停車位嗎")

        self.assertEqual(payload["parsed_intent"], "parking_search")
        self.assertEqual(payload["extracted_entities"]["query"], "市政府")
        self.assertEqual(payload["replies"][0]["type"], "flex")
        self.assertIn("市政府停車場", payload["replies"][0]["quick_reply_texts"])

    def test_retry_and_guided_buttons_dispatch(self) -> None:
        expectations = {
            "主選單": "main_menu",
            "換個地點": "bike_guide",
            "換個區域": "parking_guide",
            "重新查詢": "retry_guide",
        }
        for text, intent_name in expectations.items():
            with self.subTest(text=text):
                payload = self.get_payload(text)
                self.assertEqual(payload["parsed_intent"], intent_name)
                self.assertGreater(payload["quick_reply_count"], 0)

    def test_subscription_language_dispatches(self) -> None:
        payload = self.get_payload("幫我訂閱300")
        self.assertEqual(payload["parsed_intent"], "bus_subscribe")
        self.assertEqual(payload["extracted_entities"]["route"], "300")
        self.assertEqual(payload["replies"][0]["type"], "flex")

        payload = self.get_payload("取消追蹤300")
        self.assertEqual(payload["parsed_intent"], "bus_unsubscribe")
        self.assertEqual(payload["extracted_entities"]["route"], "300")

    def test_unknown_language_dispatches_to_guide(self) -> None:
        payload = self.get_payload("randomtext")
        self.assertEqual(payload["parsed_intent"], "unknown")
        self.assertEqual(payload["replies"][0]["type"], "flex")
        self.assertEqual(payload["replies"][0]["alt_text"], "台中交通小幫手查詢提示")


if __name__ == "__main__":
    unittest.main()
