import re
import requests
from urllib.parse import urlparse
from config import SHORT_DOMAINS


def resolve_url(url: str) -> str:
    """Follow redirects for known short-URL domains."""
    domain = urlparse(url).netloc
    if any(sd in domain for sd in SHORT_DOMAINS):
        try:
            r = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                stream=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            u = r.url
            r.close()
            return u
        except Exception:
            pass
    return url


def detect_marketplace(url: str):
    """Return (marketplace, pid, pos) or (None, None, None)."""
    if "amazon" in url or "amzn" in url:
        m = re.search(r"(?:/dp/|/gp/product/)([A-Z0-9]{10})", url)
        if m:
            return "amazon", m.group(1), 63
    elif "flipkart" in url or "fkrt" in url:
        m = re.search(r"(?:pid=|/p/)([A-Za-z0-9]{16})", url)
        if m:
            return "flipkart", m.group(1), 2
    return None, None, None


def make_clean_url(mkt: str, pid: str, url: str) -> str:
    """Build a canonical product URL."""
    if mkt == "amazon":
        tld = re.search(r"amazon\.([a-z.]+)", url)
        return f"https://www.amazon.{tld.group(1) if tld else 'in'}/dp/{pid}"
    return url
