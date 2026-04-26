from backend.app.discovery import collect_candidate_meals, discover_recipes, recipe_from_mealdb
from backend.app.models import PantryItem


def test_recipe_from_mealdb_captures_cuisine_area():
    recipe = recipe_from_mealdb(
        {
            "idMeal": "123",
            "strMeal": "Demo Curry",
            "strArea": "Indian",
            "strSource": "https://example.com/demo",
            "strIngredient1": "Tomato",
            "strIngredient2": "Onion",
        }
    )

    assert recipe is not None
    assert recipe.cuisine == "Indian"
    assert recipe.core_ingredients == ["tomato"]


def test_collect_candidate_meals_searches_cuisine_before_ingredients(monkeypatch):
    called_urls = []

    def fake_fetch_json(url):
        called_urls.append(url)
        if "filter.php?a=Indian" in url:
            return {"meals": [{"idMeal": "1", "strMeal": "Area Meal"}]}
        if "filter.php?i=tomato" in url:
            return {"meals": [{"idMeal": "2", "strMeal": "Ingredient Meal"}]}
        return {"meals": []}

    monkeypatch.setattr("backend.app.discovery.fetch_json", fake_fetch_json)

    meals = collect_candidate_meals([PantryItem(name="tomato", quantity="2")], "Indian")

    assert [meal["idMeal"] for meal in meals] == ["1", "2"]
    assert "filter.php?a=Indian" in called_urls[0]


def test_discover_recipes_scores_area_candidates(monkeypatch):
    def fake_fetch_json(url):
        if "filter.php?a=Indian" in url:
            return {"meals": [{"idMeal": "1", "strMeal": "Area Curry"}]}
        if "filter.php?i=tomato" in url:
            return {"meals": []}
        if "lookup.php?i=1" in url:
            return {
                "meals": [
                    {
                        "idMeal": "1",
                        "strMeal": "Area Curry",
                        "strArea": "Indian",
                        "strSource": "https://example.com/area-curry",
                        "strIngredient1": "Tomato",
                        "strIngredient2": "Onion",
                        "strIngredient3": "Garlic",
                    }
                ]
            }
        return {"meals": []}

    monkeypatch.setattr("backend.app.discovery.fetch_json", fake_fetch_json)

    recipes = discover_recipes(
        pantry=[
            PantryItem(name="tomato", quantity="2"),
            PantryItem(name="onion", quantity="1"),
            PantryItem(name="garlic", quantity="1"),
        ],
        min_match_score=0.6,
        existing_recipe_ids=set(),
        limit=5,
        cuisine="Indian",
    )

    assert [recipe.name for recipe in recipes] == ["Area Curry"]
    assert recipes[0].cuisine == "Indian"
    assert recipes[0].core_ingredients == ["tomato"]
