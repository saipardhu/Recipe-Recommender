PANTRY_STAPLES = {
    "black pepper",
    "cardamom",
    "chaat masala",
    "amchur",
    "ajwain",
    "asafoetida",
    "bay leaf",
    "black mustard",
    "chilli",
    "chilli powder",
    "chili",
    "chili powder",
    "cilantro",
    "cinnamon",
    "cinnamon stick",
    "clove",
    "coriander",
    "coriander powder",
    "coriander leave",
    "coriander seed",
    "cumin",
    "cumin powder",
    "cumin seed",
    "curry leaf",
    "fennel seed",
    "garam masala",
    "ginger",
    "ginger garlic paste",
    "ginger paste",
    "green chilli",
    "green chili",
    "ghee",
    "kasuri methi",
    "kashmiri red chili powder",
    "kashmiri red chilli powder",
    "oil",
    "olive oil",
    "paprika",
    "pepper",
    "rapeseed oil",
    "red chilli",
    "red chilli powder",
    "salt",
    "sea salt",
    "sugar",
    "sunflower oil",
    "turmeric",
    "turmeric powder",
    "vegetable oil",
    "water",
}

ALIASES = {
    "carrots": "carrot",
    "aloo": "potato",
    "chana": "chickpea",
    "chickpeas": "chickpea",
    "chole": "chickpea",
    "curry leave": "curry leaf",
    "dal": "lentil",
    "gobi": "cauliflower",
    "curd": "yogurt",
    "egg yolk": "egg",
    "egg yolks": "egg",
    "eggs": "egg",
    "eggplant": "aubergine",
    "chicken breast": "chicken",
    "chicken thigh": "chicken",
    "chopped tomato": "tomato",
    "full fat yogurt": "yogurt",
    "green beans": "beans",
    "greek yogurt": "yogurt",
    "peas": "pea",
    "potatoes": "potato",
    "tomatoes": "tomato",
}

TITLE_CORE_ALIASES = {
    "aloo": "potato",
    "baingan": "aubergine",
    "chana": "chickpea",
    "chole": "chickpea",
    "gobi": "cauliflower",
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


def recipe_core_ingredients(recipe_name: str, ingredients: list[str]) -> list[str]:
    required = [
        normalize_ingredient(ingredient)
        for ingredient in ingredients
        if not is_pantry_staple(ingredient)
    ]
    normalized_title = normalize_ingredient(recipe_name)
    title_tokens = set(normalized_title.split())

    title_cores = [
        ingredient
        for ingredient in required
        if ingredient in normalized_title
    ]
    title_cores.extend(
        core
        for token, core in TITLE_CORE_ALIASES.items()
        if token in title_tokens and core in required
    )

    if title_cores:
        return sorted(set(title_cores))

    return required[:1]


def ingredient_matches(required: str, available: set[str]) -> bool:
    normalized_required = normalize_ingredient(required)

    if normalized_required in available:
        return True

    return any(
        normalized_required in ingredient or ingredient in normalized_required
        for ingredient in available
    )


def core_ingredients_available(
    recipe_name: str,
    ingredients: list[str],
    available: set[str],
    core_ingredients: list[str] | None = None,
) -> bool:
    required_core_ingredients = (
        [normalize_ingredient(ingredient) for ingredient in core_ingredients]
        if core_ingredients
        else recipe_core_ingredients(recipe_name, ingredients)
    )

    return all(
        ingredient_matches(core_ingredient, available)
        for core_ingredient in required_core_ingredients
    )
