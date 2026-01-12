# stock_checker.py

import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PAGE_LOAD_DELAY = 5


def build_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/google-chrome"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)


def set_store_and_load_product(driver: webdriver.Chrome, store_id: str, product_url: str) -> None:
    driver.get("https://www.microcenter.com")
    time.sleep(PAGE_LOAD_DELAY)

    driver.add_cookie(
        {
            "name": "storeSelected",
            "value": str(store_id),
            "domain": ".microcenter.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
        }
    )

    driver.get(product_url)
    time.sleep(PAGE_LOAD_DELAY)


def _to_text(page_source: str) -> str:
    if not page_source:
        return ""

    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", page_source)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)

    s = s.replace("&nbsp;", " ")
    s = s.replace("&amp;", "&")

    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_new_qty(page_source: str) -> int | None:
    """
    Extracts:
      9 NEW IN STOCK
      25+ NEW IN STOCK
    Returns integer (25 for 25+).
    """
    if not page_source:
        return None

    pattern_html = (
        r"(\d+)\s*\+?\s*"
        r"(?:<[^>]+>\s*)*NEW\s*"
        r"(?:<[^>]+>\s*)*IN\s*"
        r"(?:<[^>]+>\s*)*STOCK"
    )

    m = re.search(pattern_html, page_source, flags=re.IGNORECASE | re.DOTALL)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None

    t = _to_text(page_source)
    m2 = re.search(r"\b(\d+)\s*\+?\s*NEW\s+IN\s+STOCK\b", t, flags=re.IGNORECASE)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None

    return None


def _extract_open_box_info(page_source: str) -> tuple[int | None, bool]:
    """
    Open box is considered available only if the page shows an offer line like:
      Open Box: from ...
      1 Open Box: from ...

    This avoids false positives from hidden text.
    """
    t = _to_text(page_source)
    if not t:
        return None, False

    offer_near = re.search(r"\bOpen\s*Box\b.{0,80}\bfrom\b", t, flags=re.IGNORECASE)
    if not offer_near:
        return None, False

    m_qty = re.search(r"\b(\d+)\s+Open\s*Box\b", t, flags=re.IGNORECASE)
    if m_qty:
        try:
            return int(m_qty.group(1)), True
        except Exception:
            return None, True

    return None, True


def check_stock(driver: webdriver.Chrome, product: dict, store_id: str) -> tuple[bool, int | None, bool, int | None]:
    """
    Returns:
      (new_in_stock_bool, new_qty_or_none, open_box_available_bool, open_box_qty_or_none)

    Important:
    open box availability is independent of new stock.
    """
    product_url = product.get("url", "")
    if not product_url:
        raise ValueError("product['url'] is missing")

    set_store_and_load_product(driver, store_id, product_url)

    page_source = driver.page_source or ""

    in_stock_markers = [
        "'inStock':'True'",
        '"inStock":"True"',
        '"inStock":true',
        '"inStock": true',
    ]

    new_in_stock = any(marker in page_source for marker in in_stock_markers)
    new_qty = _extract_new_qty(page_source) if new_in_stock else None

    open_box_qty, open_box_available = _extract_open_box_info(page_source)

    return bool(new_in_stock), new_qty, bool(open_box_available), open_box_qty
