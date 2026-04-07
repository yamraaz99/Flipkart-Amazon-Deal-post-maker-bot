import re
import json
import logging
from config import BANK_RE

log = logging.getLogger(__name__)


# ── Amazon ────────────────────────────────────────────────────────────────────

def extract_bank_offers_amazon(soup) -> list:
    """Extract bank offers from Amazon product pages."""
    offers = []
    seen   = set()

    # METHOD 1: "Buy for" carousel cards
    for card in soup.select(
        "#poExpander .a-carousel-card, "
        "#ppd .a-carousel-card, "
        ".a-carousel-card, "
        '[data-feature-name="buyNowFitWidget"] .a-box, '
        '[data-feature-name="buyNowFit498Widget"] .a-box'
    ):
        text = card.get_text(" ", strip=True)
        buy_match = re.search(r"Buy\s+for\s*(?:₹|Rs\.?)\s*([\d,]+)", text, re.I)
        if not buy_match:
            continue
        final_price  = int(buy_match.group(1).replace(",", ""))
        coupon_match = re.search(r"Coupon\s*[-−]?\s*(?:₹|Rs\.?)\s*([\d,]+)", text, re.I)
        coupon_amt   = int(coupon_match.group(1).replace(",", "")) if coupon_match else 0
        bank_match   = BANK_RE.search(text)
        if not bank_match:
            continue
        bank_name = bank_match.group(1).strip()
        if bank_name.lower() in seen:
            continue
        seen.add(bank_name.lower())
        bank_disc_match = re.search(
            re.escape(bank_name) + r".*?[-−]\s*(?:₹|Rs\.?)\s*([\d,]+)",
            text, re.I,
        )
        bank_disc = (
            int(bank_disc_match.group(1).replace(",", ""))
            if bank_disc_match else 0
        )
        is_emi = bool(re.search(r"\bEMI\b", text, re.I))
        offers.append({
            "bank": bank_name,
            "discount_flat": bank_disc,
            "coupon_in_card": coupon_amt,
            "final_price": final_price,
            "is_emi": is_emi,
            "text": text[:150],
        })

    # METHOD 2: Offer list items
    selectors = (
        "#poExpander li, #soWidget li, "
        "#itembox-InstallmentCalculator li, "
        '[data-csa-c-content-id*="offer"] li, '
        ".a-unordered-list .a-list-item"
    )
    for item in soup.select(selectors):
        txt = item.get_text(" ", strip=True)
        if len(txt) < 15 or len(txt) > 400:
            continue
        bm = BANK_RE.search(txt)
        if not bm:
            continue
        bank = bm.group(1).strip()
        if bank.lower() in seen:
            continue
        seen.add(bank.lower())
        offer = {"bank": bank, "text": txt[:150], "is_emi": False}
        pct = re.search(
            r"(\d+)\s*%\s*(?:instant\s*)?(?:discount|off|cashback|savings)",
            txt, re.I,
        )
        flat = re.search(
            r"(?:₹|Rs\.?|INR)\s*([\d,]+)\s*(?:instant\s*)?(?:discount|off|cashback|savings)",
            txt, re.I,
        )
        cap = re.search(
            r"(?:up\s*to|upto|max\.?)\s*(?:₹|Rs\.?|INR)\s*([\d,]+)",
            txt, re.I,
        )
        if pct:
            offer["discount_pct"] = int(pct.group(1))
        if flat:
            offer["discount_flat"] = int(flat.group(1).replace(",", ""))
        if cap:
            offer["max_discount"] = int(cap.group(1).replace(",", ""))
        if re.search(r"\bEMI\b", txt, re.I):
            offer["is_emi"] = True
        offers.append(offer)

    return offers


# ── Flipkart ──────────────────────────────────────────────────────────────────

def extract_flipkart_bank_offers_json(html_text: str) -> list:
    """
    Extract Flipkart bank offers from embedded NepOffers JSON.
    Flipkart SSR embeds offer pill data as JSON objects in the HTML.
    Pattern: {"type":"NepOffers","bankCardType":"BANK_OFFER_PILL"...}
    """
    pattern = re.compile(r'{"type":"NepOffers","bankCardType":"BANK_OFFER_PILL"')
    offers  = []
    seen    = set()

    for match in pattern.finditer(html_text):
        fragment = html_text[match.start():]

        # Extract balanced JSON block by counting braces
        depth   = 0
        end_idx = -1
        for i, ch in enumerate(fragment[:10000]):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break

        if end_idx == -1:
            continue
        try:
            obj = json.loads(fragment[: end_idx + 1])
        except (json.JSONDecodeError, ValueError):
            continue

        bank          = obj.get("offerTitle", "").strip()
        discount_text = obj.get("discountedPriceText", "").strip()
        if not bank or not discount_text:
            continue

        # Card type from nested contentList
        card_type = ""
        try:
            content_list = obj["offerSubTitleRC"]["value"]["contentList"]
            card_type = " • ".join(
                x["contentValue"]
                for x in content_list
                if x.get("contentType") == "TEXT"
            )
        except (KeyError, TypeError):
            pass

        card_type_clean = card_type.split("•")[0].strip() if card_type else ""
        full_bank       = f"{bank} {card_type_clean}".strip() if card_type_clean else bank
        dedup_key       = full_bank.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        disc_match = re.search(r"[\d,]+", discount_text.replace("₹", ""))
        disc_amt   = int(disc_match.group().replace(",", "")) if disc_match else 0
        if disc_amt <= 0:
            continue

        is_emi = bool(re.search(r"\bemi\b", card_type, re.I))
        offers.append({
            "bank": full_bank,
            "discount_flat": disc_amt,
            "is_emi": is_emi,
            "text": f"{discount_text} {bank} {card_type}"[:150],
        })

    offers.sort(key=lambda x: x.get("discount_flat", 0), reverse=True)
    log.info(f"Flipkart JSON extraction: {len(offers)} bank offers found")
    return offers
