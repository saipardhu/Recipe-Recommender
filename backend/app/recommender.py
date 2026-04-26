from .discovery import discover_recipes
from .ingredient_matcher import (
    core_ingredients_available,
    ingredient_matches,
    is_pantry_staple,
    normalize_ingredient,
)
from .models import PantryItem, Recipe, RecipeRecommendation
from .recipe_store import load_recipes, save_new_recipes
from .web_discovery import discover_web_recipes


# MVP quality gate: do not recommend recipes when the pantry only covers a weak
# fraction of required ingredients.
MIN_MATCH_SCORE = 0.6


def normalize(value: str) -> str:
    return normalize_ingredient(value)


def normalize_cuisine(value: str | None) -> str | None:
    cuisine = (value or "").strip().lower()
    return cuisine or None


def recipe_matches_cuisine(recipe: Recipe, cuisine: str | None) -> bool:
    normalized_cuisine = normalize_cuisine(cuisine)
    if not normalized_cuisine:
        return True

    return normalize_cuisine(recipe.cuisine) == normalized_cuisine


def score_recipe(
    recipe: Recipe,
    pantry: list[PantryItem],
    cuisine: str | None = None,
) -> RecipeRecommendation | None:
    if not recipe_matches_cuisine(recipe, cuisine):
        return None

    available = {normalize(item.name) for item in pantry}
    if not core_ingredients_available(
        recipe.name,
        recipe.ingredients,
        available,
        recipe.core_ingredients,
    ):
        return None

    required = [
        normalize(ingredient)
        for ingredient in recipe.ingredients
        if not is_pantry_staple(ingredient)
    ]
    matched = [ingredient for ingredient in required if ingredient_matches(ingredient, available)]

    if not matched:
        return None

    missing = [ingredient for ingredient in required if not ingredient_matches(ingredient, available)]
    match_score = len(matched) / len(required) if required else 0

    if match_score < MIN_MATCH_SCORE:
        return None

    # Keep match details in the response so the UI can explain why each
    # recipe was recommended and what the user is missing.
    return RecipeRecommendation(
        id=recipe.id,
        name=recipe.name,
        cuisine=recipe.cuisine,
        ingredients=recipe.ingredients,
        time_minutes=recipe.time_minutes,
        url=recipe.url,
        matched_ingredients=matched,
        missing_ingredients=missing,
        match_score=round(match_score, 4),
    )


def rank_recommendations(recipes: list[RecipeRecommendation]) -> list[RecipeRecommendation]:
    # Prefer stronger pantry matches, then faster recipes, then stable name
    # ordering for predictable results.
    return sorted(recipes, key=lambda recipe: (-recipe.match_score, recipe.time_minutes, recipe.name))


def recommend_recipes(
    pantry: list[PantryItem],
    limit: int = 5,
    cuisine: str | None = None,
) -> list[RecipeRecommendation]:
    local_recipes = load_recipes()
    recommendations = [
        recommendation
        for recommendation in (score_recipe(recipe, pantry, cuisine) for recipe in local_recipes)
        if recommendation
    ]
    recommendations = rank_recommendations(recommendations)

    if len(recommendations) < limit:
        discovered = discover_recipes(
            pantry=pantry,
            min_match_score=MIN_MATCH_SCORE,
            existing_recipe_ids={recipe.id for recipe in local_recipes},
            limit=limit - len(recommendations),
            cuisine=cuisine,
        )
        saved_recipes = save_new_recipes(discovered)
        discovered_recommendations = [
            recommendation
            for recommendation in (score_recipe(recipe, pantry, cuisine) for recipe in saved_recipes)
            if recommendation
        ]
        recommendations = rank_recommendations(recommendations + discovered_recommendations)

    if len(recommendations) < limit:
        latest_recipe_ids = {recipe.id for recipe in local_recipes}
        latest_recipe_ids.update(recommendation.id for recommendation in recommendations)
        web_discovered = discover_web_recipes(
            pantry=pantry,
            min_match_score=MIN_MATCH_SCORE,
            existing_recipe_ids=latest_recipe_ids,
            limit=limit - len(recommendations),
            cuisine=cuisine,
        )
        saved_recipes = save_new_recipes(web_discovered)
        web_recommendations = [
            recommendation
            for recommendation in (score_recipe(recipe, pantry, cuisine) for recipe in saved_recipes)
            if recommendation
        ]
        recommendations = rank_recommendations(recommendations + web_recommendations)

    return recommendations[:limit]
