import json
from functools import lru_cache
from pathlib import Path

from .models import Recipe


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.json"
INGREDIENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "ingredients.json"


@lru_cache(maxsize=1)
def load_recipes() -> list[Recipe]:
    # Recipe data is JSON-backed for the MVP; this boundary can later point to a
    # database without changing the recommender.
    with DATA_PATH.open(encoding="utf-8") as recipe_file:
        recipes = json.load(recipe_file)

    return [Recipe(**recipe) for recipe in recipes]


def save_new_recipes(recipes: list[Recipe]) -> list[Recipe]:
    existing_recipes = load_recipes()
    existing_ids = {recipe.id for recipe in existing_recipes}
    new_recipes = [recipe for recipe in recipes if recipe.id not in existing_ids]

    if not new_recipes:
        return []

    all_recipes = existing_recipes + new_recipes
    with DATA_PATH.open("w", encoding="utf-8") as recipe_file:
        json.dump([recipe.model_dump() for recipe in all_recipes], recipe_file, indent=2)
        recipe_file.write("\n")

    load_recipes.cache_clear()
    return new_recipes


def list_ingredients() -> list[str]:
    # Autocomplete should include both recipe ingredients and user-entered
    # ingredients that do not have recipes yet.
    ingredients = set(load_user_ingredients())
    ingredients.update({
        ingredient
        for recipe in load_recipes()
        for ingredient in recipe.ingredients
    })

    return sorted(ingredients)


def load_user_ingredients() -> list[str]:
    if not INGREDIENTS_PATH.exists():
        return []

    with INGREDIENTS_PATH.open(encoding="utf-8") as ingredients_file:
        return json.load(ingredients_file)


def add_ingredient(name: str) -> str:
    ingredient = name.strip().lower()
    if not ingredient:
        raise ValueError("Ingredient name cannot be empty.")

    # Store user additions separately from recipe-derived ingredients so we do
    # not mutate recipe data just because someone typed a new pantry item.
    ingredients = set(load_user_ingredients())
    ingredients.add(ingredient)

    INGREDIENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INGREDIENTS_PATH.open("w", encoding="utf-8") as ingredients_file:
        json.dump(sorted(ingredients), ingredients_file, indent=2)
        ingredients_file.write("\n")

    return ingredient
