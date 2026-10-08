"""Cancellation regression tests: no login and no live data writes."""
import ast
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/python/pkcargo_status.py"
if not MODULE.exists():
    MODULE = ROOT / "pkcargo_status.py"
spec = importlib.util.spec_from_file_location("cancel_status", MODULE)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)

class CancellationTests(unittest.TestCase):
    def make_patch(self, number=12300):
        return status.status_patch(f"เลขที่ออเดอร์: PN-1275#S{number}",
                                   f"{status.BASE_URL}/shops/{number}",
                                   "สถานะ: ยกเลิกออเดอร์", "2026-10-08T10:00:00")

    def test_status_only_preserves_products_costs_shipping_and_manual_fields(self):
        change = self.make_patch()
        old = {"order_id": change["order_id"], "detail_url": change["detail_url"],
               "status": "สถานะ: รอชำระเงิน", "summary": {"net_thb": 500},
               "vendors": [{"products": [{"quantity": 2, "cost": 250}],
                            "tracking_numbers": ["abc"]}], "manualCancelled": False}
        result = status.merge_status(old, {**change, "summary": {}, "vendors": []})
        self.assertEqual(result["status"], "สถานะ: ยกเลิกออเดอร์")
        self.assertEqual({k:v for k,v in result.items() if k not in ("status", "status_scraped_at")},
                         {k:v for k,v in old.items() if k != "status"})
        self.assertEqual(old["status"], "สถานะ: รอชำระเงิน")
        self.assertNotIn("_status_only", result)

    def test_rejects_partial_unknown_wrong_url_and_unknown_orders(self):
        for label in ("สถานะ: มีสินค้ายกเลิก", "สถานะ: กำลังสั่งสินค้า", "-", "ยกเลิก"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                status.status_patch("PN-1275#S12300", status.BASE_URL+"/shops/12300", label, "now")
        for url in (status.BASE_URL+"/shops/12301", "https://example.com/shops/12300"):
            with self.assertRaises(ValueError):
                status.status_patch("PN-1275#S12300", url, "ยกเลิกออเดอร์", "now")
        with self.assertRaises(ValueError):
            status.merge_status(None, self.make_patch())
        with self.assertRaises(ValueError):
            status.merge_status({"order_id":"PN-1275#S12300","detail_url":"other"}, self.make_patch())

    def test_all_pages_use_href_even_when_page_numbers_are_hidden(self):
        class Element:
            def __init__(self, text="", url=""):
                self.text, self.url = text, url
            def get_attribute(self, name):
                return self.url
            def find_element(self, by, selector):
                if selector.startswith("./div/div[1]"):
                    return Element("สถานะ: ยกเลิกออเดอร์")
                return Element(url=self.url)
        class Driver:
            def __init__(self):
                self.visited = []
            def get(self, url):
                self.current_url = url
                self.visited.append(url)
            def find_elements(self, by, selector):
                if selector == status.CARDS:
                    n = 10000 + len(self.visited)
                    return [Element(f"เลขที่ออเดอร์: PN-1275#S{n}", status.BASE_URL+f"/shops/{n}")]
                if "pagination" in selector:
                    return [Element(url=status.BASE_URL+"/shops?s=cancel&page=12")]
                return []
        class Wait:
            def __init__(self, *args):
                pass
            def until(self, condition):
                return True
        modules = {
            "selenium.webdriver.support": SimpleNamespace(expected_conditions=SimpleNamespace(presence_of_element_located=lambda x:x)),
            "selenium.webdriver.common.by": SimpleNamespace(By=SimpleNamespace(XPATH="xpath")),
            "selenium.webdriver.support.ui": SimpleNamespace(WebDriverWait=Wait),
            "selenium.webdriver.support.expected_conditions": SimpleNamespace(presence_of_element_located=lambda x:x)
        }
        driver = Driver()
        with patch.dict(sys.modules, modules):
            result = status.collect_cancelled_orders(SimpleNamespace(driver=driver), lambda message:None)
        self.assertEqual(len(result), 12)
        self.assertEqual(driver.visited[-1], status.BASE_URL+"/shops?s=cancel&page=12")

    def test_save_applies_cancellation_after_normal_scrape_without_creating_stubs(self):
        source = ROOT / "scripts/python/scraper.py"
        if not source.exists():
            source = ROOT / "scraper.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "save_to_json")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/"orders.json"
            saved = {"order_id":"PN-1275#S12300", "detail_url":status.BASE_URL+"/shops/12300",
                     "status":"รอชำระเงิน", "date":"01/10/2026", "vendors":[{"products":[{"quantity":2}]}]}
            target.write_text(json.dumps([saved]), encoding="utf-8")
            scope = {"os":os, "json":json, "DATA_PATH":str(target), "datetime":datetime,
                     "merge_status":status.merge_status, "log":lambda message:None}
            exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), scope)
            scope["save_to_json"]([saved, self.make_patch(), self.make_patch(12308)])
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["status"], "สถานะ: ยกเลิกออเดอร์")
            self.assertEqual(result[0]["vendors"], saved["vendors"])
            target.write_text("bad json", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                scope["save_to_json"]([self.make_patch()])
            self.assertEqual(target.read_text(encoding="utf-8"), "bad json")

if __name__ == "__main__":
    unittest.main()
