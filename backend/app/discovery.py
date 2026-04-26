import json
import os
import urllib.parse
import urllib.request

from .models import PantryItem, Recipe
from .ingredient_matcher import (
    core_ingredients_available,
    ingredient_matches,
    is_pantry_staple,
    normalize_ingredient,
    recipe_core_ingredients,
)


THEMEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1"
THEMEALDB_API_KEY = os.getenv("THEMEALDB_API_KEY", "1")
DEFAULT_DISCOVERED_TIME_MINUTES = 45
REQUEST_TIMEOUT_SECONDS = 3
MAX_CANDIDATES_PER_INGREDIENT = 20
MAX_CANDIDATES_PER_CUISINE = 80
MAX_DISCOVERY_FAILURES = 2


def normalize(value: str) -> str:
    return normalize_ingredient(value)


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
        cuisine=meal.get("strArea") or None,
        core_ingredients=recipe_core_ingredients(name, ingredients),
        ingredients=ingredients,
        time_minutes=DEFAULT_DISCOVERED_TIME_MINUTES,
        url=meal.get("strSource") or f"https://www.themealdb.com/meal/{meal_id}",
    )


def pantry_match_score(recipe: Recipe, pantry: list[PantryItem]) -> float:
    available = {normalize_ingredient(item.name) for item in pantry}
    if not core_ingredients_available(
        recipe.name,
        recipe.ingredients,
        available,
        recipe.core_ingredients,
    ):
        return 0

    required = [
        normalize_ingredient(ingredient)
        for ingredient in recipe.ingredients
        if not is_pantry_staple(ingredient)
    ]
    matched = [ingredient for ingredient in required if ingredient_matches(ingredient, available)]

    return len(matched) / len(required) if required else 0


def collect_candidate_meals(pantry: list[PantryItem], cuisine: str | None) -> list[dict]:
    candidates: list[dict] = []
    seen_meal_ids: set[str] = set()

    def add_candidates(meals: list[dict], max_items: int) -> None:
        for meal in meals[:max_items]:
            meal_id = meal.get("idMeal")
            if meal_id and meal_id not in seen_meal_ids:
                seen_meal_ids.add(meal_id)
                candidates.append(meal)

    # For a hard cuisine filter, search the cuisine/area index first. This is
    # broader than ingredient search and catches recipes whose primary indexed
    # ingredient is not one of the user's pantry items.
    if cuisine:
        cuisine_url = mealdb_url("filter.php", {"a": cuisine})
        meals = fetch_json(cuisine_url).get("meals") or []
        add_candidates(meals, MAX_CANDIDATES_PER_CUISINE)

    for item in pantry:
        ingredient = normalize(item.name).replace(" ", "_")
        filter_url = mealdb_url("filter.php", {"i": ingredient})
        meals = fetch_json(filter_url).get("meals") or []
        add_candidates(meals, MAX_CANDIDATES_PER_INGREDIENT)

    return candidates


def discover_recipes(
    pantry: list[PantryItem],
    min_match_score: float,
    existing_recipe_ids: set[str],
    limit: int,
    cuisine: str | None = None,
) -> list[Recipe]:
    discovered: list[Recipe] = []
    seen_ids = set(existing_recipe_ids)
    cuisine_filter = cuisine.strip().lower() if cuisine else None
    failures = 0

    try:
        candidate_meals = collect_candidate_meals(pantry, cuisine)
    except Exception:
        return discovered

    for meal in candidate_meals:
        if len(discovered) >= limit or failures >= MAX_DISCOVERY_FAILURES:
            break

        meal_id = meal.get("idMeal")
        recipe_id = f"themealdb-{meal_id}"
        if not meal_id or recipe_id in seen_ids:
            continue

        lookup_url = mealdb_url("lookup.php", {"i": meal_id})
        try:
            details = fetch_json(lookup_url).get("meals") or []
        except Exception:
            failures += 1
            continue

        recipe = recipe_from_mealdb(details[0]) if details else None
        if (
            recipe
            and cuisine_filter
            and (recipe.cuisine or "").strip().lower() != cuisine_filter
        ):
            continue

        if not recipe or pantry_match_score(recipe, pantry) < min_match_score:
            continue

        seen_ids.add(recipe.id)
        discovered.append(recipe)

    return discovered
