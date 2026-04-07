def format_caption(
    title: str,
    url: str,
    bd: dict,
    avg_price,          # from api_thunder (kept for compatibility)
    regular_price=None, # new: average from api_price_history
) -> str:
    """
    Build the Telegram caption.

    Telegram bold uses *text* (MarkdownV2) or <b>text</b> (HTML).
    We use HTML parse_mode so the caller must pass parse_mode='HTML'.

    Output example:
        Lloyd 1.5 Ton 5 Star Split AC for ₹30,490 (<b>Effectively</b>)

        📌 <b>Apply ₹3,000 off with ICICI Credit Card</b>

        https://fkrt.cc/...

        *Regular price ₹28,500
    """
    effective   = bd["effective"]
    has_savings = bd["coupon_disc"] > 0 or bd.get("best_bank_disc", 0) > 0

    # ── Header line ───────────────────────────────────────────────────────────
    if has_savings:
        header = f"{title} for ₹{effective:,} (<b>Effectively</b>)"
    else:
        header = f"{title} for ₹{bd['price']:,}"

    # ── Savings / apply line ──────────────────────────────────────────────────
    parts = []
    if bd["coupon_disc"] > 0:
        parts.append(f"₹{bd['coupon_disc']:,} off coupon")
    if bd.get("best_bank_disc", 0) > 0:
        bank_str = bd["best_bank"]
        if bd.get("best_bank_is_emi"):
            bank_str += " EMI"
        parts.append(f"₹{bd['best_bank_disc']:,} off with {bank_str}")

    lines = [header, ""]

    if parts:
        apply_text = f"📌 <b>Apply {' + '.join(parts)}</b>"
        lines.append(apply_text)
        lines.append("")

    lines.append(url)

    # ── Regular price line (from price history average) ───────────────────────
    if regular_price and regular_price > 0:
        lines.append("")
        lines.append(f"<i>*Regular price ₹{regular_price:,}</i>")

    return "\n".join(lines)
