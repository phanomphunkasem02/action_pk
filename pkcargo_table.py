"""Parse PK Cargo vendor tables without assuming currency column positions."""
import re


def _label(value):
    return re.sub(r"\s+", "", str(value)).replace("฿", "บาท").replace("¥", "หยวน")


ALIASES = {
    "price_cny": ("ราคาสินค้า", "ราคา(หยวน)", "ราคา(หยวน/ชิ้น)"),
    "qty": ("จำนวน",),
    "ship_cny": ("ค่าขนส่ง", "ค่าขนส่ง(หยวน)", "ส่งจีน(หยวน)"),
    "total_cny": ("รวม(หยวน)",),
    "discount_thb": ("ส่วนลด(บาท)", "ส่วนลด(฿)", "ส่วนลด(ฺ)", "ส่วนลด(฿.)", "ส่วนลด(฿)"),
    "total_thb": ("รวม(บาท)",),
    "extra_cny": ("เพิ่มเงิน(หยวน)", "ชำระเพิ่ม(หยวน)"),
    "item_note": ("หมายเหตุ",),
}


def vendor_columns(headers, cell_count, totals=False):
    labels = [_label(h) for h in headers]
    columns = {}
    for field, aliases in ALIASES.items():
        hits = [i for i, h in enumerate(labels) if h in {_label(a) for a in aliases}]
        if len(hits) > 1:
            raise ValueError("Duplicate vendor table heading: " + field)
        if hits:
            columns[field] = hits[0]
    required = {"price_cny", "qty", "ship_cny", "total_cny", "total_thb", "extra_cny", "item_note"}
    if totals:
        required -= {"extra_cny", "item_note"}
    if labels:
        if not required.issubset(columns):
            raise ValueError("Unrecognized vendor table headings: " + repr(headers))
    elif cell_count in (8, 9):
        fields = ["name", "price_cny", "qty", "ship_cny", "total_cny"]
        if cell_count == 9:
            fields.append("discount_thb")
        fields += ["total_thb", "extra_cny", "item_note"]
        columns = {field: i for i, field in enumerate(fields)}
    else:
        raise ValueError("Unrecognized vendor table width: " + str(cell_count))
    checked = {field: index for field, index in columns.items() if not totals or field in required or field == "discount_thb"}
    if max(checked.values()) >= cell_count:
        raise ValueError("Vendor row does not match table headings")
    return {field:index for field,index in columns.items() if index < cell_count}


def parse_vendor_cells(cells, headers=(), totals=False):
    columns = vendor_columns(headers, len(cells), totals)
    result = {field: str(cells[index]).strip() for field, index in columns.items() if field != "name"}
    result.setdefault("discount_thb", "0.00")
    result.setdefault("extra_cny", "0.00")
    result.setdefault("item_note", "-")
    for field in ("price_cny", "ship_cny", "total_cny", "extra_cny"):
        if "฿" in result[field] or "บาท" in result[field]:
            raise ValueError("THB in CNY vendor field: " + field)
    for field in ("total_thb", "discount_thb"):
        if "¥" in result[field] or "หยวน" in result[field]:
            raise ValueError("CNY in THB vendor field: " + field)
    return result


def table_headers(table, by):
    rows = table.find_elements(by.XPATH, ".//thead/tr")
    if not rows:
        rows = table.find_elements(by.XPATH, ".//tr[th]")
    if not rows:
        return []
    return [cell.text.strip() for cell in rows[-1].find_elements(by.XPATH, "./th | ./td")]
