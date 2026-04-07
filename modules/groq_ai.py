import logging
import httpx
from config import GROQ_API_KEY

log = logging.getLogger(__name__)


async def shorten_title_groq(full_title: str) -> str:
    """Use Groq LLM to clean up verbose product titles."""
    if not GROQ_API_KEY:
        return full_title
    if len(full_title) <= 70:
        return full_title

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You shorten e-commerce product titles. "
                                "Keep: brand, key specs (size, capacity, star rating, "
                                "color), product type. "
                                "Remove: model codes, marketing buzzwords, AI features, "
                                "pipe-separated feature lists, processor names. "
                                "Max ~80 characters. Return ONLY the title, nothing else."
                            ),
                        },
                        {"role": "user", "content": full_title},
                    ],
                    "temperature": 0,
                    "max_tokens": 100,
                },
            )
            data     = resp.json()
            shortened = (
                data["choices"][0]["message"]["content"]
                .strip()
                .strip('"')
                .strip("'")
            )
            if shortened and len(shortened) > 10:
                log.info(f"Title shortened: {len(full_title)} → {len(shortened)} chars")
                return shortened
    except Exception as e:
        log.warning(f"Groq title shorten failed: {e}")

    return full_title
