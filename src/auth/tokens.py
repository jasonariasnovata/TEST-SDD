import hmac


def tokens_match(expected: str, provided: str) -> bool:
    """Constant-time comparison so token checks don't leak timing information."""
    return hmac.compare_digest(expected.encode(), provided.encode())
