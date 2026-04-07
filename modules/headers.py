import re
from fake_useragent import UserAgent


def desktop_headers() -> dict:
    ua = UserAgent(
        fallback=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    )
    return {
        "User-Agent": ua.random,
        "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
    }


def mobile_headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Mobile Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
    }


def clean_price(txt) -> int | None:
    """Strip currency symbols and return integer price."""
    if not txt:
        return None
    c = re.sub(r"[^\d.]", "", str(txt).split(".")[0])
    try:
        return int(c) if c else None
    except ValueError:
        return None
