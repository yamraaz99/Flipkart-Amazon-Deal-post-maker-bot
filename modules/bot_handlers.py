import re
import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from modules.url_handler      import resolve_url, detect_marketplace, make_clean_url
from modules.buyhatke_api     import api_product_details, api_thunder, api_compare
from modules.scrapers          import scrape_amazon, scrape_flipkart
from modules.groq_ai           import shorten_title_groq
from modules.price_calculator  import calc_breakdown
from modules.image_generator   import generate_deal_image
from modules.caption           import format_caption

log = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me any Amazon or Flipkart link.\n"
        "I'll generate a deal post with price breakdown & offers!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg   = update.message
    text  = msg.text or msg.caption or ""
    url_m = re.search(r"(https?://[^\s]+)", text)
    if not url_m:
        return
    raw_url = url_m.group(1)
    if not any(k in raw_url for k in ["amazon", "amzn", "flipkart", "fkrt"]):
        return

    status = await msg.reply_text("⏳ Processing...")

    try:
        resolved = resolve_url(raw_url)
        mkt, pid, pos = detect_marketplace(resolved)
        if not mkt or not pid:
            await status.edit_text("❌ Couldn't detect product.")
            return

        product_url = make_clean_url(mkt, pid, resolved)
        await status.edit_text("🔍 Fetching data...")

        # Phase 1: parallel API calls
        details, thunder, compare = await asyncio.gather(
            api_product_details(resolved),
            api_thunder(pid, pos),
            api_compare(pid, pos),
            return_exceptions=True,
        )

        if isinstance(details, Exception): details = {}
        if isinstance(thunder, Exception): thunder = {}
        if isinstance(compare, Exception): compare = []

        raw_title = details.get("prod") or details.get("title") or "Product"
        await status.edit_text("🛒 Scraping & preparing...")

        # Phase 2: parallel scrape + title shorten
        scrape_fn = scrape_amazon if mkt == "amazon" else scrape_flipkart
        scraped_result, short_title = await asyncio.gather(
            asyncio.to_thread(scrape_fn, product_url),
            shorten_title_groq(raw_title),
            return_exceptions=True,
        )

        if isinstance(scraped_result, Exception):
            log.error(f"Scrape failed: {scraped_result}")
            scraped_result = {"current_price": None, "mrp": None,
                              "coupon": None, "bank_offers": []}
        if isinstance(short_title, Exception):
            log.warning(f"Title shorten failed: {short_title}")
            short_title = raw_title

        scraped   = scraped_result
        image_url = details.get("image", "")
        price     = scraped.get("current_price") or details.get("price") or 0
        if not price and thunder.get("avg"):
            price = int(thunder["avg"])

        mrp = scraped.get("mrp") or details.get("mrp") or price
        if mrp < price:
            mrp = price

        avg_p = thunder.get("avg", 0)
        bd    = calc_breakdown(price, mrp, scraped.get("coupon"), scraped.get("bank_offers", []))

        await status.edit_text("🎨 Generating deal card...")

        deal_img = generate_deal_image(image_url, bd, scraped.get("bank_offers", []), marketplace=mkt)
        caption  = format_caption(short_title, product_url, bd, avg_p)

        if deal_img:
            await msg.reply_photo(photo=deal_img, caption=caption)
        else:
            await msg.reply_text(caption, disable_web_page_preview=True)

        await status.delete()

    except Exception as e:
        log.error(f"Error: {e}", exc_info=True)
        await status.edit_text(f"❌ Error: {str(e)[:100]}")
