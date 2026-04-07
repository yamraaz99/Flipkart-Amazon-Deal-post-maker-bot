import os
import base64
import logging
import tempfile
import shutil
from io import BytesIO

import requests
from PIL import Image as PILImage
from html2image import Html2Image

from modules.templates import AMAZON_DEAL_TEMPLATE, FLIPKART_DEAL_TEMPLATE

log = logging.getLogger(__name__)

_PLACEHOLDER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mP8/58BAwAI/AL+hc2rNAAAAABJRU5ErkJggg=="
)


def _find_chrome() -> str | None:
    """
    Find Chrome/Chromium executable.
    Checks common paths + playwright's downloaded chromium.
    """
    # Common system paths
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
        # Playwright downloads chromium here
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]

    # Check direct paths first
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            log.info(f"Chrome found at: {path}")
            return path

    # Glob for playwright path (has version number in folder name)
    import glob
    playwright_paths = glob.glob(
        os.path.expanduser(
            "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"
        )
    )
    if playwright_paths:
        log.info(f"Chrome found via playwright: {playwright_paths[0]}")
        return playwright_paths[0]

    # Try shutil which
    for name in ["chromium", "chromium-browser", "google-chrome"]:
        path = shutil.which(name)
        if path:
            log.info(f"Chrome found via which: {path}")
            return path

    log.error("No Chrome/Chromium executable found!")
    return None


def _download_image_b64(url: str):
    """Download image and return (base64_str, width, height)."""
    try:
        r         = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img_bytes = r.content
        img       = PILImage.open(BytesIO(img_bytes))
        w, h      = img.size
        b64       = base64.b64encode(img_bytes).decode("utf-8")
        return b64, w, h
    except Exception:
        return _PLACEHOLDER_B64, 1, 1


def _fmt(n) -> str:
    return f"{int(n):,}" if n else "0"


def generate_deal_image(
    image_url: str,
    bd: dict,
    bank_offers: list,
    marketplace: str = "amazon",
):
    """Render deal card HTML to a cropped PNG and return a BytesIO buffer."""
    img_b64, orig_w, orig_h = _download_image_b64(image_url)

    aspect       = orig_w / orig_h if orig_h > 0 else 1
    is_landscape = aspect > 1.3

    if is_landscape:
        layout, canvas_width, img_max, pad = "stack", 750, 500, 28
    else:
        layout, canvas_width, img_max, pad = "side", 800, 350, 28

    tpl = dict(
        layout=layout,
        canvas_width=canvas_width,
        img_max=img_max,
        pad=pad,
        img_b64=img_b64,
        price_fmt=_fmt(bd["price"]),
        coupon_disc=bd["coupon_disc"],
        coupon_disc_fmt=_fmt(bd["coupon_disc"]),
        effective_fmt=_fmt(bd["effective"]),
        best_bank=bd.get("best_bank") or "Bank",
        best_bank_disc=bd.get("best_bank_disc", 0),
        best_bank_disc_fmt=_fmt(bd.get("best_bank_disc", 0)),
    )

    if marketplace == "flipkart":
        mrp_discount     = max(0, bd["mrp"] - bd["price"])
        has_any_discount = (
            mrp_discount > 0
            or bd["coupon_disc"] > 0
            or bd.get("best_bank_disc", 0) > 0
        )
        tpl.update(
            mrp_fmt=_fmt(bd["mrp"]),
            mrp_discount=mrp_discount,
            mrp_discount_fmt=_fmt(mrp_discount),
            show_mrp_discount=mrp_discount > 0,
            has_any_discount=has_any_discount,
        )
        html = FLIPKART_DEAL_TEMPLATE.render(**tpl)
    else:
        savings_count = 0
        total_savings = 0
        if bd["coupon_disc"] > 0:
            savings_count += 1
            total_savings += bd["coupon_disc"]
        if bd.get("best_bank_disc", 0) > 0:
            savings_count += 1
            total_savings += bd["best_bank_disc"]
        tpl.update(
            savings_count=savings_count,
            total_savings_fmt=_fmt(total_savings),
        )
        html = AMAZON_DEAL_TEMPLATE.render(**tpl)

    # Find Chrome executable
    chrome_path = _find_chrome()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Build Html2Image with chrome path if found
            hti_kwargs = dict(
                output_path=tmpdir,
                custom_flags=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--hide-scrollbars",
                    "--disable-dev-shm-usage",   # important for Render/Docker
                    "--disable-setuid-sandbox",
                ],
            )
            if chrome_path:
                hti_kwargs["browser_executable"] = chrome_path

            hti   = Html2Image(**hti_kwargs)
            fname = "deal.png"
            hti.screenshot(
                html_str=html,
                save_as=fname,
                size=(canvas_width, 900),
            )

            fpath  = os.path.join(tmpdir, fname)
            img    = PILImage.open(fpath).convert("RGB")
            pixels = img.load()
            w, h   = img.size

            # Auto-crop white bottom padding
            bottom = h
            for y in range(h - 1, 0, -1):
                row_white = all(
                    pixels[x, y][0] > 250
                    and pixels[x, y][1] > 250
                    and pixels[x, y][2] > 250
                    for x in range(0, w, 10)
                )
                if not row_white:
                    bottom = y + 15
                    break

            img = img.crop((0, 0, w, min(bottom, h)))
            buf = BytesIO()
            img.save(buf, format="PNG", quality=95)
            buf.seek(0)
            return buf

    except Exception as e:
        log.error(f"html2image render error: {e}")
        return None
