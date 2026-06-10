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
