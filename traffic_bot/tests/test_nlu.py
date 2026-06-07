from __future__ import annotations

import unittest

from utils.nlu import parse_user_intent, resolve_context


class NaturalLanguageIntentTest(unittest.TestCase):
    def test_parking_search_language(self) -> None:
        cases = {
            "台中車站附近哪裡可以停車": "台中車站",
            "逢甲附近有停車位嗎": "逢甲",
            "市政府附近還有停車位嗎": "市政府",
            "我現在在台中車站附近，哪裡可以停車？": "台中車站",
            "逢甲附近還有車位嗎？": "逢甲",
            "幫我找西屯有空位的停車場": "西屯",
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
            "台中車站附近有腳踏車可以借嗎": "台中車站",
        }
        for text, query in cases.items():
            with self.subTest(text=text):
                intent = parse_user_intent(text)
                self.assertEqual(intent.name, "bike_search")
                self.assertEqual(intent.query, query)

        nearby = parse_user_intent("我想找附近可以還 YouBike 的地方")
        self.assertEqual(nearby.name, "bike_search")

    def test_bus_search_and_subscription_language(self) -> None:
        expectations = {
            "300多久到": ("bus_search", "300"),
            "300還要多久": ("bus_search", "300"),
            "300現在到哪了": ("bus_search", "300"),
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
            "可以做什麼": "capability_question",
            "我可以查什麼": "capability_question",
            "你可以幫我做什麼": "capability_question",
            "系統正常嗎": "status",
            "我追蹤了哪些公車": "subscription_list",
            "YouBike": "clarify",
            "查停車": "clarify",
            "換個地點": "clarify",
            "換個區域": "clarify",
            "重新查詢": "clarify",
            "randomtext": "unknown",
        }
        for text, name in expectations.items():
            with self.subTest(text=text):
                self.assertEqual(parse_user_intent(text).name, name)

    def test_contextual_followups(self) -> None:
        parking = resolve_context(parse_user_intent("逢甲"), {"pending_intent": "parking_search"})
        self.assertEqual(parking.name, "parking_search")
        self.assertEqual(parking.query, "逢甲")

        bike = resolve_context(parse_user_intent("逢甲"), {"pending_intent": "bike_search"})
        self.assertEqual(bike.name, "bike_search")
        self.assertEqual(bike.query, "逢甲")

        subscribe = resolve_context(parse_user_intent("訂閱這條"), {"last_bus_route": "300"})
        self.assertEqual(subscribe.name, "bus_subscribe")
        self.assertEqual(subscribe.route, "300")


if __name__ == "__main__":
    unittest.main()
