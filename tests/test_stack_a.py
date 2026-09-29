from src.app.greeting import greet


def test_stack_a_lowercase():
    assert greet("ada") == "Hello, Ada!"
