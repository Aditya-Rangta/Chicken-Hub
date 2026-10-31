DEFAULT_GST_PERCENT = 5.0

# Coupon rules (clearly defined):
#   percent -> value is a percentage taken off the SUBTOTAL
#   flat    -> value is a fixed rupee amount taken off the SUBTOTAL
#   min_subtotal -> coupon works only if subtotal is at least this amount
# Discount can never be more than the subtotal. GST is charged AFTER discount.
COUPONS = {
    "WELCOME10": {"type": "percent", "value": 10, "min_subtotal": 200,
                  "description": "10% off on orders of Rs. 200 or more"},
    "CHICKEN50": {"type": "flat", "value": 50, "min_subtotal": 400,
                  "description": "Flat Rs. 50 off on orders of Rs. 400 or more"},
}


class CouponError(ValueError):
    """Raised when a coupon code is wrong or its rule is not satisfied."""


def apply_coupon(code, subtotal):
    """Return the discount amount for `code`. Raise CouponError if not valid."""
    code = (code or "").strip().upper()
    if code not in COUPONS:
        raise CouponError("Invalid coupon code.")
    rule = COUPONS[code]
    if subtotal < rule["min_subtotal"]:
        raise CouponError(f"{code} needs a minimum order of Rs. {rule['min_subtotal']}.")
    if rule["type"] == "percent":
        discount = subtotal * rule["value"] / 100
    else:
        discount = rule["value"]
    return round(min(discount, subtotal), 2)


def calculate_bill(subtotal, gst_percent=DEFAULT_GST_PERCENT, coupon_code=None):
    """
    Work out the full bill.
    Returns a dict: subtotal, discount, taxable, tax, total, coupon_code, gst_percent
    """
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative.")
    if gst_percent < 0 or gst_percent > 100:
        raise ValueError("GST percent must be between 0 and 100.")
    subtotal = round(subtotal, 2)
    discount = 0.0
    code = None
    if coupon_code:
        discount = apply_coupon(coupon_code, subtotal)   # may raise CouponError
        code = coupon_code.strip().upper()
    taxable = round(subtotal - discount, 2)
    tax = round(taxable * gst_percent / 100, 2)
    total = round(taxable + tax, 2)
    return {"subtotal": subtotal, "discount": discount, "taxable": taxable,
            "tax": tax, "total": total, "coupon_code": code,
            "gst_percent": gst_percent}


def rupees(amount):
    """Format a number as money, e.g. 1234.5 -> '₹1,234.50'."""
    return f"₹{amount:,.2f}"


def format_receipt(order, restaurant="CHICKEN HUB", width=42):
    """
    Build a readable text receipt.
    `order` is a dict with: order_no, created_at, customer_name, items (list of dicts with
    item_name, unit_price, quantity), subtotal, discount, tax, total, coupon_code, gst_percent.
    """
    def row(label, value):
        return label + value.rjust(width - len(label))

    line = "=" * width
    dash = "-" * width
    out = [line, restaurant.center(width), "Fast Food Restaurant".center(width),
           "(College project - not a real brand)".center(width), line,
           row("Order No:", order["order_no"]),
           row("Date:", order["created_at"]),
           row("Customer:", order.get("customer_name") or "Guest"),
           dash, f"{'Item':<18} {'Qty':>3} {'Price':>8} {'Amount':>10}", dash]
    for it in order["items"]:
        amount = it["unit_price"] * it["quantity"]
        out.append(f"{it['item_name'][:18]:<18} {it['quantity']:>3} "
                   f"{it['unit_price']:>8.2f} {amount:>10.2f}")
    out.append(dash)
    out.append(row("Subtotal:", rupees(order["subtotal"])))
    if order["discount"] > 0:
        out.append(row(f"Discount ({order['coupon_code']}):", "-" + rupees(order["discount"])))
    out.append(row(f"GST ({order['gst_percent']:g}%):", rupees(order["tax"])))
    out.append(line)
    out.append(row("TOTAL:", rupees(order["total"])))
    out.append(line)
    out.append("Thank you! Visit again.".center(width))
    return "\n".join(out)
