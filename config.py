import os
import re
import logging

# ── Bot credentials ──────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── BuyHatke extension creds ─────────────────────────────────────────────────
EXT_ID   = "7242722"
EXT_AUTH = "788970602"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Short-URL domains that need resolving ────────────────────────────────────
SHORT_DOMAINS = [
    "amzn.to", "amzn.in", "bit.ly",
    "fkrt.site", "fkrt.cc", "fkrt.co", "fkrt.to",
    "dl.flipkart.com",
]

# ── Bank name regex ──────────────────────────────────────────────────────────
BANK_RE = re.compile(
    r"((?:SBI|HDFC|ICICI|Axis|Kotak|RBL|HSBC|Yes\sBank|IndusInd|Federal|"
    r"BOB|Citi|AMEX|Amazon\sPay|OneCard|AU|Flipkart\sAxis|BOBCARD)"
    r"(?:\sBank)?\s*(?:Credit|Debit)?\s*Card[s]?)",
    re.I,
)

# ── Bank brand colours ───────────────────────────────────────────────────────
BANK_COLORS = {
    "sbi": "#0d6efd",
    "hdfc": "#004b8d",
    "icici": "#f37920",
    "axis": "#97144d",
    "kotak": "#ed1c24",
    "rbl": "#21409a",
    "hsbc": "#db0011",
    "yes bank": "#0066b3",
    "indusind": "#8b1a4a",
    "federal": "#f7a800",
    "bob": "#f47920",
    "citi": "#003ea4",
    "amex": "#006fcf",
    "amazon pay": "#ff9900",
    "onecard": "#000000",
    "au": "#ec1c24",
    "flipkart axis": "#2874f0",
    "bobcard": "#f47920",
}

def get_bank_color(bank_name: str) -> str:
    name = bank_name.lower()
    for key, color in BANK_COLORS.items():
        if key in name:
            return color
    return "#666666"
