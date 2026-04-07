def format_caption(title: str, url: str, bd: dict, avg_price) -> str:
    effective   = bd["effective"]
    has_savings = bd["coupon_disc"] > 0 or bd.get("best_bank_disc", 0) > 0

    if has_savings:
        header = f"{title} for ₹{effective:,} (Effectively)"
    else:
        header = f"{title} for ₹{bd['price']:,}"

    # Combined savings line
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
        lines.append(f"👉 Apply {' + '.join(parts)}")
        lines.append("")
    lines.append(url)

    return "\n".join(lines)
