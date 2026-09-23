def greet(name: str) -> str:
    """Return a greeting for a display name."""
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be empty")
    return f"Hello, {cleaned}!"
