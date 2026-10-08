"""Read the separate cancellation list; never infer cancellation from absence."""
import re
from copy import deepcopy
from datetime import datetime
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://member.pkcargo.com"
CARDS = "/html/body/div[1]/div[2]/div[3]/div[3]/div/div[2]/div"


def status_patch(card_text, detail_url, status, timestamp):
    normalized = re.sub(r"^สถานะ\s*:\s*", "", str(status).strip())
    if normalized not in ("ยกเลิกออเดอร์", "ยกเลิกสั่งซื้อ"):
        raise ValueError("Not a whole-order cancellation")
    match = re.search(r"PN-\d+#S(\d+)\b", card_text)
    if not match or detail_url != BASE_URL + "/shops/" + match.group(1):
        raise ValueError("Cancellation order ID and URL do not match")
    return {"_status_only": True, "order_id": match.group(0),
            "detail_url": detail_url, "status": "สถานะ: " + normalized,
            "status_scraped_at": timestamp}


def merge_status(existing, patch):
    if not existing:
        raise ValueError("Cancelled order is not in saved history; skipping")
    checked = status_patch(patch["order_id"], patch["detail_url"],
                           patch["status"], patch["status_scraped_at"])
    if (existing.get("order_id") != checked["order_id"]
            or existing.get("detail_url") != checked["detail_url"]):
        raise ValueError("Cancellation does not match saved order")
    result = deepcopy(existing)
    result["status"] = checked["status"]
    result["status_scraped_at"] = checked["status_scraped_at"]
    return result


def collect_cancelled_orders(scraper, log):
    # Lazy imports keep validation/tests independent of Selenium.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    patches = {}
    page, last_page = 1, 1
    timestamp = datetime.now().isoformat()
    while page <= last_page:
        scraper.driver.get(BASE_URL + "/shops?s=cancel&page=" + str(page))
        WebDriverWait(scraper.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//h5[contains(.,'รายการสั่งสินค้า')]")))
        parsed = urlparse(scraper.driver.current_url)
        if parsed.netloc != "member.pkcargo.com" or parsed.path != "/shops" or parse_qs(parsed.query).get("s") != ["cancel"]:
            raise ValueError("Cancellation page redirected or login expired")
        cards = scraper.driver.find_elements(By.XPATH, CARDS)
        if not cards:
            empty = scraper.driver.find_elements(By.XPATH, "//*[contains(text(),'ไม่มีข้อมูล')]")
            if page != 1 or not empty:
                raise ValueError("Cancellation page layout changed or missing cards")
            return []
        for link in scraper.driver.find_elements(By.XPATH, "//ul[contains(@class,'pagination')]//a"):
            target = urlparse(link.get_attribute("href") or "")
            number = parse_qs(target.query).get("page", ["1"])[0]
            if target.netloc == "member.pkcargo.com" and target.path == "/shops" and number.isdigit():
                last_page = max(last_page, int(number))
        if last_page > 1000:
            raise ValueError("Unexpected cancellation pagination")
        page_ids = set()
        for card in cards:
            status = card.find_element(By.XPATH, "./div/div[1]/div/div[2]").text
            url = card.find_element(By.XPATH, ".//div/div[2]/div[3]/a").get_attribute("href")
            try:
                patch = status_patch(card.text, url, status, timestamp)
            except ValueError as e:
                # Historical source cards can have a heading for a different URL.
                # Never guess which saved order to cancel.
                log(f"[CANCEL-SKIP] {url}: {e}")
                continue
            page_ids.add(patch["order_id"])
            patches[patch["order_id"]] = patch
        if not page_ids:
            raise ValueError("Cancellation page has no valid order identities/statuses")
        if page > 1 and not page_ids.difference(previous_ids):
            raise ValueError("Cancellation pagination repeated a page")
        previous_ids = set(patches)
        log(f"[CANCEL] Page {page}/{last_page}: {len(cards)} orders (status only)")
        page += 1
    return list(patches.values())
