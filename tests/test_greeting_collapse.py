import pytest

from src.app.greeting import greet


def test_r1_repeated_spaces_collapse():
    assert greet("ada   lovelace") == "Hello, Ada Lovelace!"


def test_r2_tabs_collapse():
    assert greet("ada\tlovelace") == "Hello, Ada Lovelace!"


def test_r3_empty_still_raises():
    with pytest.raises(ValueError):
        greet("   ")
