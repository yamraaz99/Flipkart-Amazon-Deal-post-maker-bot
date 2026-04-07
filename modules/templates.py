from jinja2 import Template

AMAZON_DEAL_TEMPLATE = Template("""
<img src="data:image/png;base64,{{ img_b64 }}" alt="product" />
{% if coupon_disc > 0 %}
<div class="coupon-box">
  <strong>Coupon Discount</strong>
  Save ₹{{ coupon_disc_fmt }} with coupon
  <button>Apply</button>
</div>
{% endif %}
<table>
  <tr><td>Items:</td><td>₹{{ price_fmt }}.00</td></tr>
  <tr><td>Delivery:</td><td>0.00</td></tr>
  <tr><td>Total:</td><td>₹{{ price_fmt }}.00</td></tr>
  {% if savings_count > 0 %}
  <tr class="savings-row">
    <td>Savings ({{ savings_count }}): ▲</td>
    <td>−₹{{ total_savings_fmt }}.00</td>
  </tr>
  {% if best_bank_disc > 0 %}
  <tr><td>{{ best_bank }} Discount:</td><td>−₹{{ best_bank_disc_fmt }}.00</td></tr>
  {% endif %}
  {% if coupon_disc > 0 %}
  <tr><td>Your Coupon Savings</td><td>−₹{{ coupon_disc_fmt }}.00</td></tr>
  {% endif %}
  {% endif %}
  <tr class="order-total"><td><strong>Order Total:</strong></td><td><strong>₹{{ effective_fmt }}.00</strong></td></tr>
</table>
""")

FLIPKART_DEAL_TEMPLATE = Template("""
<img src="data:image/png;base64,{{ img_b64 }}" alt="product" />
<table>
  <tr><td>MRP (incl. of all taxes)</td><td>₹{{ mrp_fmt }}</td></tr>
  {% if has_any_discount %}
  <tr><td colspan="2"><strong>Discounts ▲</strong></td></tr>
  {% if show_mrp_discount %}
  <tr><td>MRP Discount</td><td>−₹{{ mrp_discount_fmt }}</td></tr>
  {% endif %}
  {% if coupon_disc > 0 %}
  <tr><td>Coupons for you</td><td>−₹{{ coupon_disc_fmt }}</td></tr>
  {% endif %}
  {% if best_bank_disc > 0 %}
  <tr><td>Bank Offer Discount</td><td>−₹{{ best_bank_disc_fmt }}</td></tr>
  {% endif %}
  <tr class="total-row"><td>Total Amount ▲</td><td><strong>₹{{ effective_fmt }}</strong></td></tr>
  {% else %}
  <tr><td><strong>Selling Price</strong></td><td><strong>₹{{ effective_fmt }}</strong></td></tr>
  {% endif %}
</table>
""")
