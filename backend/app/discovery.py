import json
import os
import urllib.parse
import urllib.request

from .models import PantryItem, Recipe


THEMEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1"
THEMEALDB_API_KEY = os.getenv("THEMEALDB_API_KEY", "1")
DEFAULT_DISCOVERED_TIME_MINUTES = 45
REQUEST_TIMEOUT_SECONDS = 8


def normalize(value: str) -> str:
    return value.strip().lower()


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def mealdb_url(path: str, params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(params)
    return f"{THEMEALDB_BASE_URL}/{THEMEALDB_API_KEY}/{path}?{query}"


def parse_meal_ingredients(meal: dict) -> list[str]:
    ingredients = []

    for index in range(1, 21):
        ingredient = normalize(meal.get(f"strIngredient{index}") or "")
        if ingredient:
            ingredients.append(ingredient)

    return ingredients


def recipe_from_mealdb(meal: dict) -> Recipe | None:
    meal_id = meal.get("idMeal")
    name = meal.get("strMeal")
    ingredients = parse_meal_ingredients(meal)

    if not meal_id or not name or not ingredients:
        return None

    # TheMealDB does not expose cooking time in the free response, so discovered
    # recipes use a neutral default until we add richer extraction.
    return Recipe(
        id=f"themealdb-{meal_id}",
        name=name,
        ingredients=ingredients,
        time_minutes=DEFAULT_DISCOVERED_TIME_MINUTES,
        url=meal.get("strSource") or f"https://www.themealdb.com/meal/{meal_id}",
    )


def pantry_match_score(recipe: Recipe, pantry: list[PantryItem]) -> float:
    available = {normalize(item.name) for item in pantry}
    required = [normalize(ingredient) for ingredient in recipe.ingredients]
    matched = [ingredient for ingredient in required if ingredient in available]

    return len(matched) / len(required)


def discover_recipes(
    pantry: list[PantryItem],
    min_match_score: float,
    existing_recipe_ids: set[str],
    limit: int,
) -> list[Recipe]:
    discovered: list[Recipe] = []
    seen_ids = set(existing_recipe_ids)

    for item in pantry:
        if len(discovered) >= limit:
            break

        ingredient = normalize(item.name).replace(" ", "_")
        filter_url = mealdb_url("filter.php", {"i": ingredient})

        try:
            meals = fetch_json(filter_url).get("meals") or []
        except Exception:
            continue

        for meal in meals[:8]:
            if len(discovered) >= limit:
                break

            meal_id = meal.get("idMeal")
            recipe_id = f"themealdb-{meal_id}"
            if not meal_id or recipe_id in seen_ids:
                continue

            lookup_url = mealdb_url("lookup.php", {"i": meal_id})
            try:
                details = fetch_json(lookup_url).get("meals") or []
            except Exception:
                continue

            recipe = recipe_from_mealdb(details[0]) if details else None
            if not recipe or pantry_match_score(recipe, pantry) < min_match_score:
                continue

            seen_ids.add(recipe.id)
            discovered.append(recipe)

    return discovered
