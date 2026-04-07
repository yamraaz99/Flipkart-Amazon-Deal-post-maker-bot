import re
import json
import logging
import httpx
from config import EXT_ID, EXT_AUTH

log = logging.getLogger(__name__)


async def api_product_details(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"https://ext1.buyhatke.com/extension-apis/chatBot/"
                f"fetchProductDetails?extId={EXT_ID}&extAuth={EXT_AUTH}",
                json={"url": url},
                headers={"Content-Type": "application/json"},
            )
            d = r.json()
            return d.get("data", {}) if d.get("status") == 1 else {}
    except Exception as e:
        log.error(f"api_product_details: {e}")
        return {}


async def api_thunder(pid: str, pos: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://ext1.buyhatke.com/extension-apis/thunder/getPidData",
                json={"pos": pos, "pids": [pid]},
                headers={"Content-Type": "application/json"},
            )
            d = r.json()
            if d.get("status"):
                raw   = d.get("data", {})
                entry = raw.get(f"{pos}:{pid}", raw)
                if isinstance(entry, str):
                    entry = json.loads(entry)
                return entry if isinstance(entry, dict) else {}
    except Exception as e:
        log.error(f"api_thunder: {e}")
    return {}


async def api_compare(pid: str, pos: int) -> list:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://searchnew.bitbns.com/buyhatke/comparePrice",
                params={"PID": pid, "pos": pos, "trst": 1},
            )
            # Guard: empty or non-JSON response
            if not r.text or not r.text.strip():
                log.warning("api_compare: empty response")
                return []
            return r.json().get("data", [])
    except Exception as e:
        log.error(f"api_compare: {e}")
        return []


async def api_price_history(pid: str, pos: int) -> int | None:
    """
    Fetch price history from BuyHatke graph API and return the
    average (mean) of all recorded prices, rounded to nearest ₹.

    API  : https://graph.bitbns.com/getPredictedData.php
    Params: type=log, indexName=interest_centers, logName=info,
            mainFL=1, pos=<pos>, pid=<pid>

    Response format (plain text, no JSON):
        2025-05-30 16:17:05~299~*~*2025-05-31 02:25:55~299~*~* ...
        &~&~<min>&~&~<max>
    Each record is separated by ~*~* and has the shape:
        YYYY-MM-DD HH:MM:SS~<price>
    """
    url = "https://graph.bitbns.com/getPredictedData.php"
    params = {
        "type": "log",
        "indexName": "interest_centers",
        "logName": "info",
        "mainFL": "1",
        "pos": str(pos),
        "pid": pid,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            text = r.text.strip()

        if not text:
            return None

        # Strip trailing metadata  &~&~min&~&~max
        data_part = text.split("&~&~")[0]

        # Each entry: "YYYY-MM-DD HH:MM:SS~<price>"
        prices = []
        for record in data_part.split("~*~*"):
            record = record.strip()
            if not record:
                continue
            # Price is the second token after splitting on "~"
            parts = record.split("~")
            if len(parts) >= 2:
                try:
                    price_val = int(parts[1])
                    if price_val > 0:
                        prices.append(price_val)
                except ValueError:
                    continue

        if not prices:
            return None

        avg = round(sum(prices) / len(prices))
        log.info(
            f"Price history for {pid}: {len(prices)} data points, "
            f"avg=₹{avg:,}"
        )
        return avg

    except Exception as e:
        log.error(f"api_price_history: {e}")
        return None
