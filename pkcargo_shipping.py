"""Shipping-only refreshes: never replace saved products or financial totals."""
from copy import deepcopy
from datetime import datetime


def page_jobs(urls, page, full_pages=5):
    mode = "full" if page <= full_pages else "shipping"
    return [tuple(info) + (mode,) for info in urls]


def merge_shipping(existing, patch):
    if not existing or existing.get("detail_url") != patch.get("detail_url"):
        raise ValueError("Shipping refresh requires an existing matching order")
    result = deepcopy(existing)
    vendors = {v.get("vendor_id"): v for v in result.get("vendors", [])}
    for incoming in patch.get("vendors", []):
        vendor = vendors.get(incoming.get("vendor_id"))
        if vendor is None:
            raise ValueError("Shipping vendor does not match saved order")
        vendor["tracking_numbers"] = deepcopy(incoming["tracking_numbers"])
    for key in ("status", "shipping_type", "shipping_scraped_at"):
        if patch.get(key) not in (None, "", "-"):
            result[key] = patch[key]
    return result


def scrape_shipping_patch(scraper, url, list_status="-"):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    d = scraper.driver
    d.get(url)
    heading = WebDriverWait(d, 15).until(
        EC.presence_of_element_located((By.XPATH, "//h5[contains(text(), 'ออเดอร์เลขที่')]"))
    )
    blocks = d.find_elements(By.XPATH, "//div[contains(@id, 'vendor-')]")
    if not blocks:
        raise ValueError("No vendor blocks found; preserving saved shipping")
    pending = []
    for block in blocks:
        links = {}
        for link in block.find_elements(By.CSS_SELECTOR, "a[href*='/forwarders/items/track']"):
            href = link.get_attribute("href")
            links[href] = link.text.strip()
        pending.append((block.get_attribute("id"), links))
    shipping = d.find_elements(By.XPATH, "//div[contains(text(), 'รูปแบบขนส่ง')]")
    patch = {
        "order_id": heading.text.replace("ออเดอร์เลขที่ :", "").strip(),
        "detail_url": url, "_shipping_only": True,
        "status": list_status,
        "shipping_type": shipping[0].text.replace("รูปแบบขนส่ง:", "").strip() if shipping else "-",
        "shipping_scraped_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "vendors": [],
    }
    for vendor_id, links in pending:
        tracking = []
        for href, tracking_id in links.items():
            data = scraper.scrape_tracking_page(href)
            if not data:
                raise ValueError("Tracking fetch failed; preserving saved shipping")
            data["tracking_id"] = data.get("tracking_id") or tracking_id
            tracking.append(data)
        patch["vendors"].append({"vendor_id": vendor_id, "tracking_numbers": tracking})
    return patch
