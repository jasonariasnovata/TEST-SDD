import pytest

from src.app.greeting import greet


def test_greets_trimmed_name():
    assert greet("  Ada ") == "Hello, Ada!"


def test_rejects_empty_name():
    with pytest.raises(ValueError):
        greet("   ")
