from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from flex.parking import parking_bubble
from services import parking_service


class ParkingDisplayTest(unittest.TestCase):
    def test_zero_remaining_spaces_are_visible(self) -> None:
        bubble = parking_bubble(
            [
                {
                    "name": "市政公園停車場",
                    "available_spaces": 0,
                    "total_spaces": 120,
                    "status_text": "已滿",
                    "address": "台中市西屯區",
                    "update_time": "2026-06-08T14:32:00+08:00",
                }
            ],
            query="市政府",
        )
        payload = json.dumps(bubble, ensure_ascii=False)
        self.assertIn("剩餘 0 格", payload)
        self.assertIn("已滿", payload)
        self.assertIn("總車位：120 格｜使用率 100%", payload)

    def test_remaining_spaces_are_primary_information(self) -> None:
        bubble = parking_bubble(
            [
                {
                    "name": "市政公園停車場",
                    "available_spaces": 42,
                    "total_spaces": 120,
                    "status_text": "尚有車位",
                }
            ],
            query="市政府",
        )
        payload = json.dumps(bubble, ensure_ascii=False)
        self.assertIn("剩餘 42 格", payload)
        self.assertIn("尚有車位", payload)
        self.assertNotIn("資料更新中", payload)

    def test_missing_numeric_fields_hide_placeholder_text(self) -> None:
        bubble = parking_bubble(
            [
                {
                    "name": "市政公園停車場",
                    "available_spaces": None,
                    "total_spaces": 120,
                    "status_text": "",
                    "address": "台中市西屯區",
                }
            ],
            query="市政府",
        )
        payload = json.dumps(bubble, ensure_ascii=False)
        for forbidden in ("資料更新中", "None", "null", "N/A", "未提供"):
            self.assertNotIn(forbidden, payload)

    def test_tdx_availability_mapping_keeps_zero(self) -> None:
        availability = [
            {
                "CarParkID": "P001",
                "AvailableSpaces": 0,
                "TotalSpaces": 100,
                "UpdateTime": "2026-06-08T14:32:00+08:00",
            }
        ]
        lots = [
            {
                "CarParkID": "P001",
                "CarParkName": {"Zh_tw": "市政公園停車場"},
                "Address": "台中市西屯區",
            }
        ]
        with patch.object(parking_service.tdx_client, "get", side_effect=[availability, lots]):
            result = parking_service._load_tdx_parking()

        self.assertEqual(result[0]["available_spaces"], 0)
        self.assertEqual(result[0]["status_text"], "已滿")

    def test_tdx_nested_availability_mapping(self) -> None:
        availability = [
            {
                "CarParkID": "P001",
                "AvailableSpacesDetail": [
                    {"SpaceType": 1, "AvailableSpaces": 20},
                    {"SpaceType": 2, "AvailableSpaces": 22},
                ],
                "TotalSpaces": 100,
            }
        ]
        lots = [{"CarParkID": "P001", "CarParkName": {"Zh_tw": "市政公園停車場"}}]
        with patch.object(parking_service.tdx_client, "get", side_effect=[availability, lots]):
            result = parking_service._load_tdx_parking()

        self.assertEqual(result[0]["available_spaces"], 42)
        self.assertEqual(result[0]["status_text"], "尚有車位")


if __name__ == "__main__":
    unittest.main()
