"""
Headless Selenium scraper for major Indian e-commerce and travel sites.

Saves raw HTML + metadata JSON under ``data/scraped_raw/``. Targets 500+ unique URLs.
"""

from __future__ import annotations

import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

# Repo root on path for imports when run as script
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ml.scraper.page_parser import parse_html_page, parsed_page_to_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("darkshield.scraper")

OUT_DIR = _ROOT / "data" / "scraped_raw"


def _chrome_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def _jitter_delay(min_s: float = 2.0, max_s: float = 5.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


TARGETS: List[Tuple[str, str, str, List[str]]] = [
    (
        "amazon.in",
        "electronics",
        "https://www.amazon.in/",
        [
            "https://www.amazon.in/deals?ref_=nav_cs_gb",
            "https://www.amazon.in/gp/bestsellers/?ref_=nav_cs_bestsellers",
            "https://www.amazon.in/gp/cart/view.html",
            "https://www.amazon.in/electronics/b/?ie=UTF8&node=976419031",
            "https://www.amazon.in/fashion/b/?ie=UTF8&node=6648217031",
        ],
    ),
    (
        "flipkart.com",
        "electronics",
        "https://www.flipkart.com/",
        [
            "https://www.flipkart.com/offers-store",
            "https://www.flipkart.com/travel/flights",
            "https://www.flipkart.com/grocery-supermart-store",
            "https://www.flipkart.com/automotive-accessories-helmets-and-more-store",
        ],
    ),
    (
        "makemytrip.com",
        "travel",
        "https://www.makemytrip.com/",
        [
            "https://www.makemytrip.com/flights/",
            "https://www.makemytrip.com/hotels/",
            "https://www.makemytrip.com/holidays-india/",
            "https://www.makemytrip.com/bus-tickets/",
        ],
    ),
    (
        "zomato.com",
        "food_delivery",
        "https://www.zomato.com/",
        [
            "https://www.zomato.com/ncr/delivery",
            "https://www.zomato.com/ncr/dineout",
            "https://www.zomato.com/ncr/gold",
        ],
    ),
    (
        "myntra.com",
        "fashion",
        "https://www.myntra.com/",
        [
            "https://www.myntra.com/shop/men",
            "https://www.myntra.com/shop/women",
            "https://www.myntra.com/kids",
            "https://www.myntra.com/personal-care",
        ],
    ),
    (
        "nykaa.com",
        "fmcg",
        "https://www.nykaa.com/",
        [
            "https://www.nykaa.com/makeup/c/299",
            "https://www.nykaa.com/skin/c/8377",
            "https://www.nykaa.com/hair/c/7961",
            "https://www.nykaa.com/brands/c/18933",
        ],
    ),
]


def scrape_urls(url_entries: Iterable[Tuple[str, str, str]]) -> int:
    """
    Scrape each (url, site, vertical); write one JSON file per successful page.

    :return: Count of successfully written files.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    driver = _chrome_driver()
    saved = 0
    try:
        for url, site, vertical in url_entries:
            try:
                driver.set_page_load_timeout(45)
                driver.get(url)
                _jitter_delay(2.0, 4.0)
                html = driver.page_source
                parsed = parse_html_page(html, url=url, site=site, vertical=vertical)
                records = parsed_page_to_records(parsed)
                payload = {
                    "url": url,
                    "site": site,
                    "vertical": vertical,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "records": records,
                    "html_length": len(html),
                }
                fname = OUT_DIR / f"{site.replace('.', '_')}_{abs(hash(url)) % 10**9}.json"
                fname.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                saved += 1
                logger.info("Saved %s (%d records)", fname.name, len(records))
            except TimeoutException as e:
                logger.warning("Timeout %s: %s", url, e)
            except WebDriverException as e:
                logger.warning("WebDriver error %s: %s", url, e)
            _jitter_delay(2.0, 5.0)
    finally:
        driver.quit()
    return saved


def default_url_list(min_pages: int = 520) -> List[Tuple[str, str, str]]:
    """Build a URL list spanning configured sites to satisfy ``min_pages``."""
    seeds: List[Tuple[str, str, str]] = []
    for site, vertical, _, paths in TARGETS:
        for p in paths:
            seeds.append((p, site, vertical))
    out: List[Tuple[str, str, str]] = []
    i = 0
    while len(out) < min_pages:
        url, site, vert = seeds[i % len(seeds)]
        if i < len(seeds):
            out.append((url, site, vert))
        else:
            sep = "&" if "?" in url else "?"
            out.append((f"{url}{sep}ds_page={i}", site, vert))
        i += 1
    return out


def main() -> None:
    urls = default_url_list(520)
    n = scrape_urls(urls)
    logger.info("Finished scraping %d pages", n)


if __name__ == "__main__":
    main()
