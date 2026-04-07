def calc_breakdown(price, mrp, coupon, bank_offers) -> dict:
    b = {
        "mrp": mrp or price or 0,
        "price": price or 0,
        "coupon_disc": 0,
        "coupon_text": None,
        "after_coupon": price or 0,
        "best_bank": None,
        "best_bank_disc": 0,
        "best_bank_is_emi": False,
        "effective": price or 0,
    }
    if not price:
        return b

    if coupon:
        if coupon["type"] == "percent":
            b["coupon_disc"] = int(price * coupon["value"] / 100)
            b["coupon_text"] = f"Apply {int(coupon['value'])}% Coupon on page"
        else:
            b["coupon_disc"] = int(coupon["value"])
            b["coupon_text"] = f"Apply ₹{int(coupon['value']):,} Coupon on page"
        b["after_coupon"] = price - b["coupon_disc"]

    ap = b["after_coupon"]
    for o in bank_offers:
        d = 0
        if o.get("final_price"):
            d = ap - o["final_price"]
            if d < 0:
                d = 0
        elif "discount_flat" in o:
            d = o["discount_flat"]
        elif "discount_pct" in o:
            d = int(ap * o["discount_pct"] / 100)
        if "max_discount" in o:
            d = min(d, o["max_discount"])
        if d > b["best_bank_disc"]:
            b["best_bank_disc"] = d
            b["best_bank"]      = o["bank"]
            b["best_bank_is_emi"] = o.get("is_emi", False)

    b["effective"] = ap - b["best_bank_disc"]
    return b
