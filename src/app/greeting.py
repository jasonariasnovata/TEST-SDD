def greet(name: str) -> str:
    """Return a greeting for a display name, in title case, with single spaces."""
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("name must not be empty")
    return f"Hello, {cleaned.title()}!"
