PANTRY_STAPLES = {
    "black pepper",
    "oil",
    "olive oil",
    "pepper",
    "rapeseed oil",
    "salt",
    "vegetable oil",
    "water",
}

ALIASES = {
    "carrots": "carrot",
    "egg yolk": "egg",
    "egg yolks": "egg",
    "eggs": "egg",
    "green beans": "beans",
    "peas": "pea",
    "potatoes": "potato",
    "tomatoes": "tomato",
}


def normalize_ingredient(value: str) -> str:
    ingredient = value.strip().lower()
    ingredient = " ".join(ingredient.replace("-", " ").split())

    if ingredient in ALIASES:
        return ALIASES[ingredient]

    if ingredient.endswith("oes"):
        return ingredient[:-2]

    if ingredient.endswith("ies"):
        return f"{ingredient[:-3]}y"

    if ingredient.endswith("s") and not ingredient.endswith("ss"):
        return ingredient[:-1]

    return ingredient


def is_pantry_staple(ingredient: str) -> bool:
    return normalize_ingredient(ingredient) in PANTRY_STAPLES


def ingredient_matches(required: str, available: set[str]) -> bool:
    normalized_required = normalize_ingredient(required)

    if normalized_required in available:
        return True

    return any(
        normalized_required in ingredient or ingredient in normalized_required
        for ingredient in available
    )
