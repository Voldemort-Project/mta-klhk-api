def string_to_float(value: str) -> float:
    try:
        value = value.replace(".", "").replace(",", ".")
        return float(value)
    except (ValueError, AttributeError):
        return None
