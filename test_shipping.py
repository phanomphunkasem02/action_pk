import unittest
import pkcargo_shipping as shipping


class ShippingRefreshTests(unittest.TestCase):
    def test_page_boundary_and_300_jobs(self):
        jobs = [job for page in range(1, 11)
                for job in shipping.page_jobs([("url", "status", 123)] * 30, page)]
        self.assertEqual(len(jobs), 300)
        self.assertEqual(sum(job[-1] == "full" for job in jobs), 150)
        self.assertEqual(sum(job[-1] == "shipping" for job in jobs), 150)
        self.assertEqual(jobs[149][-1], "full")
        self.assertEqual(jobs[150][-1], "shipping")

    def test_only_shipping_changes_and_vendor_order_is_irrelevant(self):
        old = {"order_id": "PN-1", "detail_url": "url", "summary": {"net_thb": 100},
               "scraped_at": "old", "vendors": [
                   {"vendor_id": "v1", "products": [{"price": 100}], "table_totals": {"total": 100}, "tracking_numbers": []},
                   {"vendor_id": "v2", "products": [{"qty": 2}], "tracking_numbers": [{"tracking_id": "old"}]}]}
        incoming = {"detail_url": "url", "shipping_scraped_at": "new", "status": "shipped",
                    "vendors": [{"vendor_id": "v2", "tracking_numbers": [{"tracking_id": "new", "weight": 2}]},
                                {"vendor_id": "v1", "tracking_numbers": []}]}
        merged = shipping.merge_shipping(old, incoming)
        self.assertEqual(merged["summary"], old["summary"])
        self.assertEqual(merged["scraped_at"], "old")
        for i in range(2):
            self.assertEqual(merged["vendors"][i]["products"], old["vendors"][i]["products"])
        self.assertEqual(merged["vendors"][0]["table_totals"], {"total": 100})
        self.assertEqual(merged["vendors"][1]["tracking_numbers"][0]["tracking_id"], "new")
        self.assertEqual(old["vendors"][1]["tracking_numbers"][0]["tracking_id"], "old")

    def test_missing_order_and_unknown_vendor_are_not_written(self):
        with self.assertRaises(ValueError):
            shipping.merge_shipping(None, {"detail_url": "url"})
        old = {"detail_url": "url", "vendors": [{"vendor_id": "v1", "tracking_numbers": ["old"]}]}
        with self.assertRaises(ValueError):
            shipping.merge_shipping(old, {"detail_url": "url", "vendors": [{"vendor_id": "v2", "tracking_numbers": []}]})
        self.assertEqual(old["vendors"][0]["tracking_numbers"], ["old"])

    def test_cannot_overwrite_financial_fields_from_patch(self):
        old = {"detail_url": "url", "summary": {"net_thb": 100}, "vendors": []}
        merged = shipping.merge_shipping(old, {"detail_url": "url", "summary": {}, "vendors": []})
        self.assertEqual(merged["summary"], {"net_thb": 100})
