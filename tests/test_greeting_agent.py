from src.app.greeting import greet


def test_title_case_single_word():
    assert greet("grace") == "Hello, Grace!"
