def string_to_float(value: str) -> float:
    try:
        value = value.replace(".", "").replace(",", ".")
        return float(value)
    except (ValueError, AttributeError):
        return None


def format_rupiah(amount: int) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")
