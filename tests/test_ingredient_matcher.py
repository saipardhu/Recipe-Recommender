from backend.app.ingredient_matcher import (
    core_ingredients_available,
    ingredient_matches,
    is_pantry_staple,
    normalize_ingredient,
    recipe_core_ingredients,
)


def test_normalize_ingredient_handles_common_variants():
    assert normalize_ingredient("  Tomatoes ") == "tomato"
    assert normalize_ingredient("Chickpeas") == "chickpea"
    assert normalize_ingredient("egg-yolks") == "egg"
    assert normalize_ingredient("Potatoes") == "potato"


def test_pantry_staples_are_identified_after_normalization():
    assert is_pantry_staple("Rapeseed Oil")
    assert is_pantry_staple("black pepper")
    assert is_pantry_staple("garam masala")
    assert is_pantry_staple("turmeric powder")
    assert not is_pantry_staple("beef")


def test_ingredient_matches_exact_and_close_names():
    available = {"egg", "tomato", "beans"}

    assert ingredient_matches("egg yolks", available)
    assert ingredient_matches("greek yogurt", {"yogurt"})
    assert ingredient_matches("green beans", available)
    assert not ingredient_matches("potato", available)


def test_recipe_core_ingredients_uses_title_and_known_translations():
    assert recipe_core_ingredients(
        "Baingan Bharta",
        ["aubergine", "onion", "tomato", "garlic"],
    ) == ["aubergine"]
    assert recipe_core_ingredients(
        "Kidney Bean Curry",
        ["onion", "garlic", "kidney bean", "basmati rice"],
    ) == ["kidney bean"]


def test_core_ingredients_must_be_available():
    assert not core_ingredients_available(
        "Baingan Bharta",
        ["aubergine", "onion", "tomato", "garlic"],
        {"onion", "tomato", "garlic"},
    )
    assert core_ingredients_available(
        "Chana Masala",
        ["chickpea", "onion", "tomato puree", "garlic"],
        {"chickpea", "onion", "tomato puree", "garlic"},
    )
