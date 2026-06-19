import unittest

from scraper import select_new_order_urls


class SelectNewOrderUrlsTests(unittest.TestCase):
    def test_stops_immediately_when_latest_order_already_exists(self):
        page = [
            ("https://member.pkcargo.com/shops/11490", "new"),
            ("https://member.pkcargo.com/shops/11489", "new"),
        ]

        new_urls, reached_existing = select_new_order_urls(
            page, {"https://member.pkcargo.com/shops/11490"}
        )

        self.assertEqual(new_urls, [])
        self.assertTrue(reached_existing)

    def test_refreshes_existing_order_when_net_total_changed(self):
        page = [
            ("https://member.pkcargo.com/shops/11490", "new", 20661.30),
            ("https://member.pkcargo.com/shops/11489", "new", 1782.00),
        ]
        existing = {
            "https://member.pkcargo.com/shops/11490": {
                "summary": {"net_thb": "0.00 บาท", "grand_net": None}
            },
            "https://member.pkcargo.com/shops/11489": {
                "summary": {"net_thb": "1,782.00 บาท", "grand_net": None}
            },
        }

        new_urls, reached_existing = select_new_order_urls(page, existing)

        self.assertEqual(new_urls, [page[0]])
        self.assertTrue(reached_existing)

    def test_stops_when_existing_order_net_total_is_unchanged(self):
        page = [
            ("https://member.pkcargo.com/shops/11490", "new", 20661.30),
            ("https://member.pkcargo.com/shops/11489", "new", 1782.00),
        ]
        existing = {
            "https://member.pkcargo.com/shops/11490": {
                "summary": {"net_thb": "20,661.30 บาท", "grand_net": None}
            }
        }

        new_urls, reached_existing = select_new_order_urls(page, existing)

        self.assertEqual(new_urls, [])
        self.assertTrue(reached_existing)

    def test_returns_only_orders_before_first_existing_order(self):
        page = [
            ("https://member.pkcargo.com/shops/11492", "new"),
            ("https://member.pkcargo.com/shops/11491", "new"),
            ("https://member.pkcargo.com/shops/11490", "old"),
            ("https://member.pkcargo.com/shops/11489", "old"),
        ]

        new_urls, reached_existing = select_new_order_urls(
            page, {"https://member.pkcargo.com/shops/11490"}
        )

        self.assertEqual(new_urls, page[:2])
        self.assertTrue(reached_existing)

    def test_keeps_whole_page_when_history_is_not_reached(self):
        page = [
            ("https://member.pkcargo.com/shops/11500", "new"),
            ("https://member.pkcargo.com/shops/11499", "new"),
        ]

        new_urls, reached_existing = select_new_order_urls(
            page, {"https://member.pkcargo.com/shops/11490"}
        )

        self.assertEqual(new_urls, page)
        self.assertFalse(reached_existing)


if __name__ == "__main__":
    unittest.main()
