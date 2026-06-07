from __future__ import annotations

import unittest

from utils.nlu import parse_user_intent


class NaturalLanguageIntentTest(unittest.TestCase):
    def test_parking_search_language(self) -> None:
        cases = {
            "台中車站附近哪裡可以停車": "台中車站",
            "逢甲附近有停車位嗎": "逢甲",
            "市政府附近還有停車位嗎": "市政府",
        }
        for text, query in cases.items():
            with self.subTest(text=text):
                intent = parse_user_intent(text)
                self.assertEqual(intent.name, "parking_search")
                self.assertEqual(intent.query, query)

    def test_bike_search_language(self) -> None:
        cases = {
            "逢甲附近有YouBike嗎": "逢甲",
            "靜宜附近哪裡可以借腳踏車": "靜宜",
            "幫我找台中車站附近的YouBike": "台中車站",
        }
        for text, query in cases.items():
            with self.subTest(text=text):
                intent = parse_user_intent(text)
                self.assertEqual(intent.name, "bike_search")
                self.assertEqual(intent.query, query)

    def test_bus_search_and_subscription_language(self) -> None:
        expectations = {
            "300多久到": ("bus_search", "300"),
            "幫我查300": ("bus_search", "300"),
            "我要搭300": ("bus_search", "300"),
            "幫我訂閱300": ("bus_subscribe", "300"),
            "取消追蹤300": ("bus_unsubscribe", "300"),
        }
        for text, (name, route) in expectations.items():
            with self.subTest(text=text):
                intent = parse_user_intent(text)
                self.assertEqual(intent.name, name)
                self.assertEqual(intent.route, route)

    def test_guides_and_status_language(self) -> None:
        expectations = {
            "可以做什麼": "main_menu",
            "系統正常嗎": "status",
            "我追蹤了哪些公車": "subscription_list",
            "YouBike": "bike_guide",
            "查停車": "parking_guide",
            "換個地點": "bike_guide",
            "換個區域": "parking_guide",
            "重新查詢": "retry_guide",
            "randomtext": "unknown",
        }
        for text, name in expectations.items():
            with self.subTest(text=text):
                self.assertEqual(parse_user_intent(text).name, name)


if __name__ == "__main__":
    unittest.main()
