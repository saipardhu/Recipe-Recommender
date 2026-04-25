from backend.app.ingredient_matcher import (
    ingredient_matches,
    is_pantry_staple,
    normalize_ingredient,
)


def test_normalize_ingredient_handles_common_variants():
    assert normalize_ingredient("  Tomatoes ") == "tomato"
    assert normalize_ingredient("egg-yolks") == "egg"
    assert normalize_ingredient("Potatoes") == "potato"


def test_pantry_staples_are_identified_after_normalization():
    assert is_pantry_staple("Rapeseed Oil")
    assert is_pantry_staple("black pepper")
    assert not is_pantry_staple("beef")


def test_ingredient_matches_exact_and_close_names():
    available = {"egg", "tomato", "beans"}

    assert ingredient_matches("egg yolks", available)
    assert ingredient_matches("green beans", available)
    assert not ingredient_matches("potato", available)
