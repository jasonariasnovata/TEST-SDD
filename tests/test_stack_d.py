from src.app.greeting import greet


def test_stack_d_two_words():
    assert greet("ada lovelace") == "Hello, Ada Lovelace!"
