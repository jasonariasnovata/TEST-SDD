from src.auth.tokens import tokens_match


def test_matching_tokens():
    assert tokens_match("abc", "abc")


def test_mismatched_tokens():
    assert not tokens_match("abc", "abd")
