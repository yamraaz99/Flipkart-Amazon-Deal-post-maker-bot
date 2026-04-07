# Deal Post Bot v6 — Codebase Reference

> Use this document when working with an AI assistant (Claude, GPT-4, etc.) to
> add features or fix bugs **without uploading the entire codebase each time**.
> Point the AI to the relevant module and paste only that file.

---

## Project layout

```
dealbot/
├── main.py               # Entry point — builds the Telegram app and registers handlers
├── config.py             # All constants, env vars, regex, colour maps
├── CODEBASE.md           # ← you are here
└── modules/
    ├── __init__.py
    ├── url_handler.py     # URL resolution, marketplace detection, clean URL builder
    ├── headers.py         # HTTP headers (desktop/mobile) + clean_price() helper
    ├── buyhatke_api.py    # Three async BuyHatke API wrappers
    ├── bank_offers.py     # Bank-offer extraction for Amazon (HTML) and Flipkart (JSON)
    ├── scrapers.py        # scrape_amazon() and scrape_flipkart() + Flipkart HTML fetch
    ├── groq_ai.py         # Groq LLM async title shortener
    ├── price_calculator.py# calc_breakdown() — coupon + bank discount maths
    ├── templates.py       # Jinja2 HTML templates for Amazon and Flipkart deal cards
    ├── image_generator.py # HTML → PNG via html2image, auto-crop, returns BytesIO
    ├── caption.py         # Plain-text Telegram caption formatter
    └── bot_handlers.py    # cmd_start + handle_message (the main orchestrator)
```

---

## Module-by-module reference

### `config.py`
| Symbol | Purpose |
|---|---|
| `BOT_TOKEN` | Read from `TELEGRAM_BOT_TOKEN` env var |
| `GROQ_API_KEY` | Read from `GROQ_API_KEY` env var |
| `EXT_ID / EXT_AUTH` | BuyHatke extension credentials |
| `SHORT_DOMAINS` | List of short-URL domains that need resolving |
| `BANK_RE` | Compiled regex matching Indian bank card names |
| `BANK_COLORS` | Dict mapping bank key → hex colour |
| `get_bank_color(name)` | Returns hex colour for a bank name string |

---

### `modules/url_handler.py`
| Function | Signature | What it does |
|---|---|---|
| `resolve_url` | `(url) → str` | Follows redirects for short URLs |
| `detect_marketplace` | `(url) → (mkt, pid, pos)` | Returns `("amazon"/"flipkart", pid, pos)` or `(None,None,None)` |
| `make_clean_url` | `(mkt, pid, url) → str` | Builds canonical `/dp/PID` or Flipkart URL |

---

### `modules/headers.py`
| Function | Returns |
|---|---|
| `desktop_headers()` | Dict with random desktop UA |
| `mobile_headers()` | Dict with fixed Pixel 8 Pro UA |
| `clean_price(txt)` | Strips `₹`, commas → `int` or `None` |

---

### `modules/buyhatke_api.py`
All three functions are **async**.

| Function | Endpoint | Returns |
|---|---|---|
| `api_product_details(url)` | BuyHatke chatBot | `dict` with `prod`, `title`, `image`, `price`, `mrp` |
| `api_thunder(pid, pos)` | BuyHatke thunder | `dict` with `avg` (historical average price) |
| `api_compare(pid, pos)` | bitbns comparePrice | `list` of competitor prices |

---

### `modules/bank_offers.py`
| Function | Input | Returns |
|---|---|---|
| `extract_bank_offers_amazon(soup)` | BeautifulSoup object | `list[dict]` — each dict has `bank`, `discount_flat/pct`, `is_emi`, `text` |
| `extract_flipkart_bank_offers_json(html_text)` | Raw HTML string | `list[dict]` sorted by `discount_flat` desc |

**Offer dict shape:**
```python
{
  "bank": "HDFC Credit Cards",
  "discount_flat": 1500,      # or "discount_pct": 10
  "max_discount": 2000,       # optional cap
  "final_price": 8500,        # optional (Amazon "Buy for" cards)
  "coupon_in_card": 0,        # optional
  "is_emi": False,
  "text": "raw snippet..."
}
```

---

### `modules/scrapers.py`
| Function | Returns |
|---|---|
| `scrape_amazon(url)` | `{"current_price", "mrp", "coupon", "bank_offers"}` |
| `scrape_flipkart(url)` | same shape |
| `_fetch_flipkart_html(url)` | Raw HTML string (curl_cffi → requests fallback) |

**Coupon dict shape:**
```python
{"type": "percent" | "flat", "value": float | int, "text": str}
```

---

### `modules/groq_ai.py`
| Function | Notes |
|---|---|
| `async shorten_title_groq(full_title)` | Calls Groq `llama-3.1-8b-instant`; returns original if API key missing or title ≤ 70 chars |

---

### `modules/price_calculator.py`
| Function | Signature |
|---|---|
| `calc_breakdown(price, mrp, coupon, bank_offers)` | `→ dict` |

**Breakdown dict keys:**
```
mrp, price, coupon_disc, coupon_text,
after_coupon, best_bank, best_bank_disc,
best_bank_is_emi, effective
```

---

### `modules/templates.py`
Two **Jinja2** `Template` objects:

| Template | Marketplace | Key variables |
|---|---|---|
| `AMAZON_DEAL_TEMPLATE` | Amazon | `price_fmt`, `coupon_disc`, `savings_count`, `total_savings_fmt`, `best_bank`, `best_bank_disc`, `effective_fmt` |
| `FLIPKART_DEAL_TEMPLATE` | Flipkart | `mrp_fmt`, `mrp_discount_fmt`, `coupon_disc`, `best_bank_disc`, `effective_fmt`, `has_any_discount`, `show_mrp_discount` |

Both templates also receive `img_b64`, `canvas_width`, `img_max`, `pad`, `layout`.

---

### `modules/image_generator.py`
| Function | Signature | Returns |
|---|---|---|
| `generate_deal_image(image_url, bd, bank_offers, marketplace)` | `marketplace="amazon"\|"flipkart"` | `BytesIO` PNG or `None` on error |

**Internal helpers:**
- `_download_image_b64(url)` → `(b64_str, width, height)`
- `_fmt(n)` → comma-formatted string e.g. `"12,499"`

**Image flow:**
1. Download product image → base64
2. Choose layout (`side` for portrait, `stack` for landscape)
3. Render Jinja2 template → HTML string
4. `Html2Image.screenshot()` → PNG file (900 px tall canvas)
5. Auto-crop white rows from bottom
6. Return cropped `BytesIO`

---

### `modules/caption.py`
| Function | Returns |
|---|---|
| `format_caption(title, url, bd, avg_price)` | Multi-line Telegram caption string |

**Caption structure:**
```
{title} for ₹{effective} (Effectively)   ← or without "Effectively" if no discounts

👉 Apply ₹X off coupon + ₹Y off with HDFC Credit Cards

{clean_product_url}
```

---

### `modules/bot_handlers.py`
| Function | Trigger |
|---|---|
| `cmd_start` | `/start` command |
| `handle_message` | Any text/caption containing an Amazon or Flipkart URL |

**handle_message flow:**
```
1. Extract URL from message
2. resolve_url() → detect_marketplace()
3. Phase 1 (parallel): api_product_details + api_thunder + api_compare
4. Phase 2 (parallel): scrape_amazon/flipkart + shorten_title_groq
5. calc_breakdown()
6. generate_deal_image()
7. format_caption()
8. reply_photo (or reply_text if image failed)
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | BotFather token |
| `GROQ_API_KEY` | ⚠️ optional | Enables AI title shortening |

---

## Dependencies (`requirements.txt`)

```
python-telegram-bot>=20
httpx
requests
beautifulsoup4
fake-useragent
Pillow
html2image
jinja2
curl_cffi          # optional but recommended for Flipkart
```

---

## How to add a new feature (vibe-coding guide)

1. **Identify the module** from the table above.
2. **Paste only that module** into your AI chat.
3. Describe the change. Example prompts:
   - *"In `modules/caption.py`, add a line showing the historical average price if `avg_price > 0`."*
   - *"In `modules/bank_offers.py → extract_bank_offers_amazon`, also capture cashback offers."*
   - *"In `modules/scrapers.py → scrape_flipkart`, add a CSS-selector fallback for the new `.Nx9bqj` price class."*
4. Drop the updated module back into the `modules/` folder — nothing else changes.

---

## Common fix locations

| Symptom | File to edit |
|---|---|
| Price not scraped on Amazon | `modules/scrapers.py` → `scrape_amazon()` selector lists |
| Price not scraped on Flipkart | `modules/scrapers.py` → `scrape_flipkart()` + regex patterns |
| Bank offers missing (Amazon) | `modules/bank_offers.py` → `extract_bank_offers_amazon()` |
| Bank offers missing (Flipkart) | `modules/bank_offers.py` → `extract_flipkart_bank_offers_json()` |
| Deal card image looks wrong | `modules/templates.py` + `modules/image_generator.py` |
| Caption format change | `modules/caption.py` |
| New bot command | `modules/bot_handlers.py` + register in `main.py` |
| New marketplace | New scraper function in `modules/scrapers.py`, update `url_handler.py` detection |

---

## Render free-tier deployment

### How it works
Render free web services require a **bound HTTP port** or they kill the process.
`main.py` runs two coroutines concurrently via `asyncio.gather`:

| Coroutine | Purpose |
|---|---|
| `_run_health_server()` | Tiny `aiohttp` web server on `$PORT` (default 8080) — answers `GET /` and `GET /health` with `200 OK` |
| `_run_bot()` | Normal `python-telegram-bot` polling loop |

### Deploy steps
1. Push the repo to GitHub.
2. On Render → **New → Web Service** → connect repo.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python main.py`
5. Add env vars: `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`
6. Plan: **Free**

### Keep-alive (optional)
Render free sleeps after 15 min of no HTTP traffic.  
Use [UptimeRobot](https://uptimerobot.com) (free) to ping `https://<your-app>.onrender.com/health` every 5 minutes.

---

## Caption format (as of v6.1)

```
{title} for ₹{effective} (<b>Effectively</b>)     ← "Effectively" bold, HTML

📌 <b>Apply ₹X off coupon + ₹Y off with BANK</b>  ← whole line bold

{clean_product_url}

<i>*Regular price ₹{avg}</i>                       ← italic, only shown if data available
```

`parse_mode="HTML"` is passed to every `reply_photo` / `reply_text` call.

---

## New API: `api_price_history(pid, pos)`

**File**: `modules/buyhatke_api.py`  
**Endpoint**: `https://graph.bitbns.com/getPredictedData.php`  
**Params**: `type=log`, `indexName=interest_centers`, `logName=info`, `mainFL=1`, `pos`, `pid`

**Response**: plain-text, records separated by `~*~*`, each record = `YYYY-MM-DD HH:MM:SS~<price>`  
Trailing metadata `&~&~min&~&~max` is stripped before parsing.

**Returns**: `int` (mean of all prices) or `None` if fetch fails.

Called in Phase 1 of `handle_message` alongside the other three API calls (no extra latency — all run in parallel).

### Where to edit
| What | File |
|---|---|
| Change "Regular price" label text | `modules/caption.py` → last block |
| Change how average is computed (e.g. median, last-30-days) | `modules/buyhatke_api.py` → `api_price_history()` |
| Remove Regular price line entirely | Delete `regular_price=regular_price` arg in `bot_handlers.py` |
