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
    url = "https://searchnew.bitbns.com/buyhatke/comparePrice"
    params = {"PID": pid, "pos": pos, "trst": 1}

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(
                url,
                params=params,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://buyhatke.com/",
                },
            )

            if r.status_code != 200:
                log.warning(
                    f"api_compare: HTTP {r.status_code} for pid={pid}, pos={pos}, "
                    f"body={r.text[:200]!r}"
                )
                return []

            text = (r.text or "").strip()
            if not text:
                log.warning(f"api_compare: empty response for pid={pid}, pos={pos}")
                return []

            ctype = r.headers.get("content-type", "")
            if "json" not in ctype.lower():
                log.warning(
                    f"api_compare: non-JSON content-type={ctype!r} "
                    f"for pid={pid}, pos={pos}, body={text[:200]!r}"
                )
                return []

            try:
                data = r.json()
            except Exception as je:
                log.warning(
                    f"api_compare: invalid JSON for pid={pid}, pos={pos}, "
                    f"body={text[:200]!r}, error={je}"
                )
                return []

            result = data.get("data", [])
            return result if isinstance(result, list) else []

    except Exception as e:
        log.error(f"api_compare: {e}")
        return []


async def api_price_history(pid: str, pos: int) -> int | None:
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
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(
                url,
                params=params,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                },
            )
            if r.status_code != 200:
                log.warning(
                    f"api_price_history: HTTP {r.status_code} for pid={pid}, pos={pos}, "
                    f"body={r.text[:200]!r}"
                )
                return None

            text = (r.text or "").strip()
            if not text:
                log.warning(f"api_price_history: empty response for pid={pid}, pos={pos}")
                return None

            data_part = text.split("&~&~")[0]

            prices = []
            for record in data_part.split("~*~*"):
                record = record.strip()
                if not record:
                    continue

                parts = record.split("~")
                if len(parts) < 2:
                    continue

                try:
                    price_val = int(parts[1].strip())
                    if price_val > 0:
                        prices.append(price_val)
                except ValueError:
                    continue

            if not prices:
                log.warning(f"api_price_history: no valid prices for pid={pid}, pos={pos}")
                return None

            avg = round(sum(prices) / len(prices))
            log.info(f"api_price_history: pid={pid}, pos={pos}, points={len(prices)}, avg={avg}")
            return avg

    except Exception as e:
        log.error(f"api_price_history: {e}")
        return None
