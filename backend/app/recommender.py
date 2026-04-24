from .models import PantryItem, RecipeRecommendation
from .recipe_store import load_recipes


MIN_MATCH_SCORE = 0.6


def normalize(value: str) -> str:
    return value.strip().lower()


def recommend_recipes(pantry: list[PantryItem], limit: int = 5) -> list[RecipeRecommendation]:
    available = {normalize(item.name) for item in pantry}
    recommendations: list[RecipeRecommendation] = []

    for recipe in load_recipes():
        required = [normalize(ingredient) for ingredient in recipe.ingredients]
        matched = [ingredient for ingredient in required if ingredient in available]

        if not matched:
            continue

        missing = [ingredient for ingredient in required if ingredient not in available]
        match_score = len(matched) / len(required)

        if match_score < MIN_MATCH_SCORE:
            continue

        recommendations.append(
            RecipeRecommendation(
                id=recipe.id,
                name=recipe.name,
                ingredients=recipe.ingredients,
                time_minutes=recipe.time_minutes,
                url=recipe.url,
                matched_ingredients=matched,
                missing_ingredients=missing,
                match_score=round(match_score, 4),
            )
        )

    recommendations.sort(key=lambda recipe: (-recipe.match_score, recipe.time_minutes, recipe.name))
    return recommendations[:limit]
