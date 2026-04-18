from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def numfmt(value):
    if value in (None, ""):
        return "-"

    if isinstance(value, bool):
        return value

    try:
        dec_value = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return value

    if dec_value == dec_value.to_integral_value():
        return f"{dec_value:,.0f}"

    return f"{dec_value:,.2f}".rstrip("0").rstrip(".")
