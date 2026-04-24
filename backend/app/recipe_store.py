import json
from functools import lru_cache
from pathlib import Path

from .models import Recipe


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.json"
INGREDIENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "ingredients.json"


@lru_cache(maxsize=1)
def load_recipes() -> list[Recipe]:
    with DATA_PATH.open(encoding="utf-8") as recipe_file:
        recipes = json.load(recipe_file)

    return [Recipe(**recipe) for recipe in recipes]


def list_ingredients() -> list[str]:
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

    ingredients = set(load_user_ingredients())
    ingredients.add(ingredient)

    INGREDIENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INGREDIENTS_PATH.open("w", encoding="utf-8") as ingredients_file:
        json.dump(sorted(ingredients), ingredients_file, indent=2)
        ingredients_file.write("\n")

    return ingredient
