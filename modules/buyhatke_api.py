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
            return r.json().get("data", [])
    except Exception as e:
        log.error(f"api_compare: {e}")
        return []
