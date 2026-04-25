from backend.app.models import PantryItem, Recipe
from backend.app.recommender import recommend_recipes, score_recipe


def pantry(*names: str) -> list[PantryItem]:
    return [PantryItem(name=name, quantity="1") for name in names]


def recipe(recipe_id: str, ingredients: list[str], time_minutes: int = 30) -> Recipe:
    return Recipe(
        id=recipe_id,
        name=recipe_id.replace("-", " ").title(),
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


def test_recommend_recipes_backfills_and_saves_discovered_recipes(monkeypatch):
    local_recipe = recipe("local-fast", ["tomato", "onion", "garlic"], time_minutes=20)
    discovered_recipe = recipe("discovered", ["tomato", "onion", "cheese"], time_minutes=45)
    saved = []

    monkeypatch.setattr("backend.app.recommender.load_recipes", lambda: [local_recipe])
    monkeypatch.setattr(
        "backend.app.recommender.discover_recipes",
        lambda **kwargs: [discovered_recipe],
    )

    def fake_save_new_recipes(recipes: list[Recipe]) -> list[Recipe]:
        saved.extend(recipes)
        return recipes

    monkeypatch.setattr("backend.app.recommender.save_new_recipes", fake_save_new_recipes)

    recommendations = recommend_recipes(pantry("tomato", "onion", "garlic", "cheese"), limit=5)

    assert [item.id for item in recommendations] == ["local-fast", "discovered"]
    assert saved == [discovered_recipe]
