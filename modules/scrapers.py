import re
import json
import logging
import requests
from bs4 import BeautifulSoup

from modules.headers import desktop_headers, mobile_headers, clean_price
from modules.bank_offers import extract_bank_offers_amazon, extract_flipkart_bank_offers_json

log = logging.getLogger(__name__)

# ── curl_cffi optional import ─────────────────────────────────────────────────
try:
    from curl_cffi import requests as cffi_requests
    _HAS_CFFI = True
except ImportError:
    _HAS_CFFI = False
    log.warning("curl_cffi not installed — Flipkart scraping may fail")


# ── Amazon ────────────────────────────────────────────────────────────────────

def scrape_amazon(url: str) -> dict:
    result = {
        "current_price": None,
        "mrp": None,
        "coupon": None,
        "bank_offers": [],
    }

    # PASS 1: Desktop
    try:
        s = requests.Session()
        s.headers.update(desktop_headers())
        resp = s.get(url, timeout=15)
        soup = BeautifulSoup(resp.content, "html.parser")

        if "captcha" not in resp.text.lower()[:2000]:
            for sel in [
                ".priceToPay .a-price-whole",
                ".a-price .a-offscreen",
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                "#corePriceDisplay_desktop_feature_div .a-price-whole",
                "span.a-price-whole",
            ]:
                el = soup.select_one(sel)
                if el:
                    p = clean_price(el.get_text())
                    if p and p > 0:
                        result["current_price"] = p
                        break

            for sel in [
                ".a-price.a-text-price .a-offscreen",
                ".basisPrice .a-offscreen",
                "#corePriceDisplay_desktop_feature_div .a-text-price .a-offscreen",
            ]:
                el = soup.select_one(sel)
                if el:
                    m = clean_price(el.get_text())
                    if m and m > 0:
                        result["mrp"] = m
                        break

            if not result["mrp"]:
                result["mrp"] = result["current_price"]

            for sel in [
                "#coupons-card-sub-heading-before-apply",
                'label[id^="couponText"]',
                ".promoPriceBlockMessage",
                "#couponBadgeRegularVpc",
            ]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if any(w in txt.lower() for w in ["coupon", "save", "%", "₹"]):
                        pct  = re.search(r"(\d+(?:\.\d+)?)\s*%", txt)
                        flat = re.search(r"(?:₹|Rs\.?)\s*(\d[\d,]*)", txt, re.I)
                        if pct:
                            result["coupon"] = {
                                "type": "percent",
                                "value": float(pct.group(1)),
                                "text": txt,
                            }
                        elif flat:
                            result["coupon"] = {
                                "type": "flat",
                                "value": int(flat.group(1).replace(",", "")),
                                "text": txt,
                            }
                        break

            if not result["coupon"]:
                for lbl in soup.find_all("label"):
                    t = lbl.get_text(strip=True)
                    if "coupon" in t.lower() and (
                        "apply" in t.lower() or "save" in t.lower()
                    ):
                        pct  = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
                        flat = re.search(r"(?:₹|Rs\.?)\s*(\d[\d,]*)", t, re.I)
                        if pct:
                            result["coupon"] = {
                                "type": "percent",
                                "value": float(pct.group(1)),
                                "text": t,
                            }
                        elif flat:
                            result["coupon"] = {
                                "type": "flat",
                                "value": int(flat.group(1).replace(",", "")),
                                "text": t,
                            }
                        break

            result["bank_offers"] = extract_bank_offers_amazon(soup)

    except Exception as e:
        log.error(f"scrape_amazon desktop: {e}")

    # PASS 2: Mobile (supplement bank offers)
    if len(result["bank_offers"]) < 2:
        try:
            s2 = requests.Session()
            s2.headers.update(mobile_headers())
            resp2 = s2.get(url, timeout=15)
            soup2 = BeautifulSoup(resp2.content, "html.parser")

            if "captcha" not in resp2.text.lower()[:2000]:
                mobile_offers = extract_bank_offers_amazon(soup2)
                existing = {o["bank"].lower() for o in result["bank_offers"]}
                for o in mobile_offers:
                    if o["bank"].lower() not in existing:
                        result["bank_offers"].append(o)

                if not result["current_price"]:
                    for sel in [
                        ".a-price .a-offscreen",
                        "#newPrice .a-offscreen",
                        'span[data-a-color="price"] .a-offscreen',
                    ]:
                        el = soup2.select_one(sel)
                        if el:
                            p = clean_price(el.get_text())
                            if p and p > 0:
                                result["current_price"] = p
                                break

        except Exception as e:
            log.error(f"scrape_amazon mobile: {e}")

    return result


# ── Flipkart helpers ──────────────────────────────────────────────────────────

def _fetch_flipkart_html(url: str) -> str:
    """Fetch Flipkart page; curl_cffi for TLS fingerprinting, requests fallback."""

    # Attempt 1: curl_cffi
    if _HAS_CFFI:
        try:
            sess = cffi_requests.Session(impersonate="chrome120")
            for attempt in range(2):
                try:
                    resp = sess.get(url, timeout=25)
                    if resp.status_code == 200 and len(resp.text) > 5000:
                        log.info(f"Flipkart fetched via curl_cffi ({len(resp.text)} bytes)")
                        html = resp.text
                        sess.close()
                        return html
                except Exception:
                    if attempt < 1:
                        import time
                        time.sleep(1)
            sess.close()
        except Exception as e:
            log.warning(f"curl_cffi Flipkart failed: {e}")

    # Attempt 2: requests fallback
    try:
        s = requests.Session()
        s.headers.update(desktop_headers())
        resp = s.get(url, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 5000:
            log.info(f"Flipkart fetched via requests fallback ({len(resp.text)} bytes)")
            return resp.text
    except Exception as e:
        log.warning(f"requests Flipkart fallback failed: {e}")

    return ""


# ── Flipkart ──────────────────────────────────────────────────────────────────

def scrape_flipkart(url: str) -> dict:
    result = {
        "current_price": None,
        "mrp": None,
        "coupon": None,
        "bank_offers": [],
    }

    html_text = _fetch_flipkart_html(url)
    if not html_text:
        log.error("scrape_flipkart: empty HTML — page fetch failed")
        return result

    soup = BeautifulSoup(html_text, "html.parser")

    # Price from ld+json
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.text)
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") == "Product":
                offers = data.get("offers", {})
                if isinstance(offers, list) and offers:
                    result["current_price"] = clean_price(str(offers[0].get("price")))
                elif isinstance(offers, dict):
                    result["current_price"] = clean_price(str(offers.get("price")))
        except Exception:
            continue

    # Price fallback: regex on raw HTML
    if not result["current_price"]:
        for pat in [r'"sellingPrice"\s*:\s*(\d+)', r'"finalPrice"\s*:\s*(\d+)']:
            m = re.search(pat, html_text)
            if m:
                val = int(m.group(1))
                if val > 0:
                    result["current_price"] = val
                    break

    # MRP from CSS selectors
    for sel in ["div.yRaY8j", "div._3I9_wc"]:
        el = soup.select_one(sel)
        if el:
            result["mrp"] = clean_price(el.get_text())
            break

    # MRP fallback: regex
    if not result["mrp"]:
        for pat in [r'"mrp"\s*:\s*(\d+)', r'"maximumRetailPrice"\s*:\s*(\d+)']:
            m = re.search(pat, html_text)
            if m:
                val = int(m.group(1))
                if val > 0:
                    result["mrp"] = val
                    break

    if not result["mrp"]:
        result["mrp"] = result["current_price"]

    # Bank offers from embedded NepOffers JSON
    result["bank_offers"] = extract_flipkart_bank_offers_json(html_text)

    log.info(
        f"Flipkart scrape: price={result['current_price']}, "
        f"mrp={result['mrp']}, bank_offers={len(result['bank_offers'])}"
    )

    del html_text, soup
    return result
