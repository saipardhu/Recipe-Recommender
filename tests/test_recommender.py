from backend.app.models import PantryItem, Recipe
from backend.app.recommender import recommend_recipes, score_recipe


def pantry(*names: str) -> list[PantryItem]:
    return [PantryItem(name=name, quantity="1") for name in names]


def recipe(
    recipe_id: str,
    ingredients: list[str],
    time_minutes: int = 30,
    cuisine: str | None = None,
    core_ingredients: list[str] | None = None,
) -> Recipe:
    return Recipe(
        id=recipe_id,
        name=recipe_id.replace("-", " ").title(),
        cuisine=cuisine,
        core_ingredients=core_ingredients or [],
        ingredients=ingredients,
        time_minutes=time_minutes,
        url=f"https://example.com/{recipe_id}",
    )


def test_score_recipe_filters_below_sixty_percent_match():
    candidate = recipe("weak-match", ["beef", "onion", "garlic", "potato", "carrot"])

    assert score_recipe(candidate, pantry("beef", "onion")) is None


def test_score_recipe_ignores_basic_staples_in_threshold():
    candidate = recipe("staple-heavy", ["beef", "onion", "salt", "pepper", "water"])
    recommendation = score_recipe(candidate, pantry("beef", "onion"))

    assert recommendation is not None
    assert recommendation.match_score == 1.0
    assert recommendation.missing_ingredients == []


def test_score_recipe_rejects_missing_core_ingredient():
    candidate = recipe("baingan-bharta", ["aubergine", "onion", "tomato", "garlic"])

    assert score_recipe(candidate, pantry("onion", "tomato", "garlic")) is None


def test_score_recipe_uses_explicit_core_ingredients_first():
    candidate = recipe(
        "custom-curry",
        ["tomato", "onion", "garlic", "chickpea"],
        core_ingredients=["chickpea"],
    )

    assert score_recipe(candidate, pantry("tomato", "onion", "garlic")) is None
    assert score_recipe(candidate, pantry("tomato", "onion", "garlic", "chickpeas")) is not None


def test_recommend_recipes_backfills_and_saves_discovered_recipes(monkeypatch):
    local_recipe = recipe("local-fast", ["tomato", "onion", "garlic"], time_minutes=20)
    discovered_recipe = recipe("discovered", ["tomato", "onion", "cheese"], time_minutes=45)
    saved = []

    monkeypatch.setattr("backend.app.recommender.load_recipes", lambda: [local_recipe])
    monkeypatch.setattr(
        "backend.app.recommender.discover_recipes",
        lambda **kwargs: [discovered_recipe],
    )
    monkeypatch.setattr("backend.app.recommender.discover_web_recipes", lambda **kwargs: [])

    def fake_save_new_recipes(recipes: list[Recipe]) -> list[Recipe]:
        saved.extend(recipes)
        return recipes

    monkeypatch.setattr("backend.app.recommender.save_new_recipes", fake_save_new_recipes)

    recommendations = recommend_recipes(pantry("tomato", "onion", "garlic", "cheese"), limit=5)

    assert [item.id for item in recommendations] == ["local-fast", "discovered"]
    assert saved == [discovered_recipe]


def test_recommend_recipes_applies_cuisine_as_hard_filter(monkeypatch):
    indian_recipe = recipe("indian-curry", ["tomato", "onion", "garlic"], cuisine="Indian")
    italian_recipe = recipe("italian-pasta", ["tomato", "onion", "garlic"], cuisine="Italian")

    monkeypatch.setattr(
        "backend.app.recommender.load_recipes",
        lambda: [indian_recipe, italian_recipe],
    )
    monkeypatch.setattr("backend.app.recommender.discover_recipes", lambda **kwargs: [])
    monkeypatch.setattr("backend.app.recommender.discover_web_recipes", lambda **kwargs: [])
    monkeypatch.setattr("backend.app.recommender.save_new_recipes", lambda recipes: recipes)

    recommendations = recommend_recipes(
        pantry("tomato", "onion", "garlic"),
        cuisine="Indian",
    )

    assert [item.id for item in recommendations] == ["indian-curry"]
    assert recommendations[0].cuisine == "Indian"


def test_recommend_recipes_passes_cuisine_to_discovery(monkeypatch):
    captured = {}

    monkeypatch.setattr("backend.app.recommender.load_recipes", lambda: [])

    def fake_discover_recipes(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("backend.app.recommender.discover_recipes", fake_discover_recipes)
    monkeypatch.setattr("backend.app.recommender.discover_web_recipes", lambda **kwargs: [])
    monkeypatch.setattr("backend.app.recommender.save_new_recipes", lambda recipes: recipes)

    recommend_recipes(pantry("tomato", "onion"), cuisine="Mexican")

    assert captured["cuisine"] == "Mexican"


def test_recommend_recipes_uses_web_discovery_after_mealdb(monkeypatch):
    web_recipe = recipe(
        "indianhealthyrecipes-chana-masala",
        ["chickpea", "tomato", "onion", "garlic"],
        cuisine="Indian",
        core_ingredients=["chickpea"],
    )
    captured = {}
    saved = []

    monkeypatch.setattr("backend.app.recommender.load_recipes", lambda: [])
    monkeypatch.setattr("backend.app.recommender.discover_recipes", lambda **kwargs: [])

    def fake_discover_web_recipes(**kwargs):
        captured.update(kwargs)
        return [web_recipe]

    def fake_save_new_recipes(recipes: list[Recipe]) -> list[Recipe]:
        saved.extend(recipes)
        return recipes

    monkeypatch.setattr("backend.app.recommender.discover_web_recipes", fake_discover_web_recipes)
    monkeypatch.setattr("backend.app.recommender.save_new_recipes", fake_save_new_recipes)

    recommendations = recommend_recipes(
        pantry("chickpeas", "tomato", "onion", "garlic"),
        cuisine="Indian",
    )

    assert captured["cuisine"] == "Indian"
    assert saved == [web_recipe]
    assert [item.id for item in recommendations] == ["indianhealthyrecipes-chana-masala"]
