import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from dataclasses import dataclass
from typing import Any

from .ingredient_matcher import (
    core_ingredients_available,
    ingredient_matches,
    is_pantry_staple,
    normalize_ingredient,
    recipe_core_ingredients,
)
from .models import PantryItem, Recipe


REQUEST_TIMEOUT_SECONDS = 4
MAX_SOURCE_LINKS = 60
MAX_RECIPE_PAGES = 16
MAX_DISCOVERY_FAILURES = 3


@dataclass(frozen=True)
class RecipeSource:
    key: str
    cuisine: str
    entry_urls: list[str]
    curated_urls: list[str]
    allowed_hosts: set[str]


WEB_SOURCES_BY_CUISINE = {
    "indian": [
        RecipeSource(
            key="indianhealthyrecipes",
            cuisine="Indian",
            entry_urls=["https://www.indianhealthyrecipes.com/"],
            curated_urls=[
                "https://www.indianhealthyrecipes.com/chana-masala/",
                "https://www.indianhealthyrecipes.com/chana-chaat-recipe/",
                "https://www.indianhealthyrecipes.com/potato-curry-aloo-sabzi/",
                "https://www.indianhealthyrecipes.com/dum-aloo-recipe/",
                "https://www.indianhealthyrecipes.com/onion-tomato-chutney-recipe/",
                "https://www.indianhealthyrecipes.com/aloo-paratha/",
            ],
            allowed_hosts={"www.indianhealthyrecipes.com"},
        ),
    ],
    "chinese": [
        RecipeSource(
            key="omnivorescookbook",
            cuisine="Chinese",
            entry_urls=["https://omnivorescookbook.com/"],
            curated_urls=[
                "https://omnivorescookbook.com/chinese-potato-stir-fry/",
                "https://omnivorescookbook.com/tomato-egg-noodles/",
                "https://omnivorescookbook.com/egg-fried-rice/",
                "https://omnivorescookbook.com/chicken-chop-suey/",
            ],
            allowed_hosts={"omnivorescookbook.com", "www.omnivorescookbook.com"},
        ),
    ],
    "italian": [
        RecipeSource(
            key="vincenzosplate",
            cuisine="Italian",
            entry_urls=["https://www.vincenzosplate.com/"],
            curated_urls=[
                "https://www.vincenzosplate.com/pasta-with-chickpeas/",
                "https://www.vincenzosplate.com/tomato-passata/",
                "https://www.vincenzosplate.com/10-minute-lazy-pasta-recipe/",
                "https://www.vincenzosplate.com/spaghetti-alla-carbonara-recipe/",
            ],
            allowed_hosts={"www.vincenzosplate.com", "vincenzosplate.com"},
        ),
    ],
    "mexican": [
        RecipeSource(
            key="mexicanplease",
            cuisine="Mexican",
            entry_urls=["https://www.mexicanplease.com/"],
            curated_urls=[
                "https://www.mexicanplease.com/easy-mexican-beans-and-rice-soup/",
                "https://www.mexicanplease.com/charro-beans/",
                "https://www.mexicanplease.com/chile-morita-salsa/",
                "https://www.mexicanplease.com/spicy-chicken-tinga/",
            ],
            allowed_hosts={"www.mexicanplease.com", "mexicanplease.com"},
        ),
        RecipeSource(
            key="simplyrecipes",
            cuisine="Mexican",
            entry_urls=["https://www.simplyrecipes.com/mexican-recipes-11734554"],
            curated_urls=[
                "https://www.simplyrecipes.com/recipes/simple_cooked_tomato_salsa/",
                "https://www.simplyrecipes.com/recipes/refried_black_beans/",
                "https://www.simplyrecipes.com/recipes/spanish_rice/",
                "https://www.simplyrecipes.com/recipes/huevos_rancheros/",
            ],
            allowed_hosts={"www.simplyrecipes.com", "simplyrecipes.com"},
        ),
    ],
}
EXCLUDED_SOURCE_SLUGS = {
    "about",
    "about-me",
    "about-us-5096129",
    "appetizers",
    "authentic-italian-cookbook",
    "breakfast",
    "cakes",
    "contact",
    "contact-2",
    "dessert",
    "dinner-recipes-5091433",
    "chicken",
    "filter",
    "home",
    "lunch-recipes-5091263",
    "main-dish",
    "mexican-recipes-11734554",
    "most-popular",
    "most-recent",
    "privacy-policy",
    "recipes",
    "recipes-5090746",
    "recipes-new",
    "rice",
    "snacks",
    "start-here-recipe-guide-for-mexican-please",
    "veg-curry",
}
EXCLUDED_PATH_PARTS = {
    "author",
    "category",
    "collection",
    "cooking-how-tos-5090751",
    "courses",
    "cuisine",
    "ingredient",
    "ingredient-guides-5090749",
    "page",
    "pantry",
    "recipe-collections-5119362",
    "recipe-type",
    "shop",
    "tag",
    "table-talk-5206565",
}
GENERIC_LINK_TEXT = {
    "academy",
    "all recipes",
    "appetizer",
    "appetiser recipes",
    "articles",
    "breakfast",
    "contact",
    "course",
    "dessert",
    "dessert recipes",
    "dinner",
    "get recipe",
    "home",
    "in the kitchen",
    "join now & save",
    "main course recipes",
    "mains",
    "more recipes",
    "my cookbook",
    "my saves",
    "order cookbook",
    "order my new cookbook!",
    "pasta",
    "pasta recipes",
    "pizza",
    "pizza recipes",
    "read more",
    "recipe of the day",
    "recipes",
    "sauces",
    "see more",
    "shop",
    "skip to content",
    "snacks",
    "surprise me!",
    "today's pick",
    "today’s pick",
    "tours",
    "view all",
}

INGREDIENT_TERMS = [
    "tomato puree",
    "ginger garlic paste",
    "kashmiri red chili powder",
    "kashmiri red chilli powder",
    "coriander powder",
    "cumin powder",
    "chaat masala",
    "ginger",
    "chicken",
    "chickpea",
    "aloo",
    "chana",
    "chole",
    "aubergine",
    "eggplant",
    "potato",
    "tomato",
    "onion",
    "garlic",
    "carrot",
    "cauliflower",
    "gobi",
    "yogurt",
    "curd",
    "kidney bean",
    "beans",
    "lentil",
    "dal",
    "rice",
    "paneer",
    "cheese",
    "egg",
    "pea",
    "spinach",
    "mushroom",
    "bell pepper",
    "cauliflower",
    "pasta",
    "oil",
    "ghee",
    "garam masala",
    "turmeric",
    "coriander",
    "cumin",
    "green chili",
    "green chilli",
    "curry leaf",
    "chili powder",
    "chilli powder",
    "chili",
    "chilli",
    "bay leaf",
    "cardamom",
    "cinnamon",
    "mustard seed",
    "black mustard",
    "fennel seed",
    "ajwain",
    "asafoetida",
    "kasuri methi",
    "amchur",
    "tamarind",
    "beef",
    "lamb",
    "mutton",
    "fish",
]

NOISE_WORDS = {
    "a",
    "about",
    "and",
    "as",
    "chopped",
    "clove",
    "cloves",
    "cup",
    "cups",
    "fine",
    "finely",
    "fresh",
    "gram",
    "grams",
    "large",
    "medium",
    "optional",
    "or",
    "small",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "tablespoon",
    "tablespoons",
    "to",
    "tsp",
}


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.current_href: str | None = None
        self.current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        attrs_by_name = dict(attrs)
        href = attrs_by_name.get("href")
        if href:
            self.current_href = href
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current_href:
            text = " ".join(" ".join(self.current_text).split())
            if text:
                self.links.append((self.current_href, text))
            self.current_href = None
            self.current_text = []


class JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self.in_json_ld = False
        self.current_script: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return

        attrs_by_name = {name.lower(): value for name, value in attrs}
        script_type = (attrs_by_name.get("type") or "").lower()
        if script_type == "application/ld+json":
            self.in_json_ld = True
            self.current_script = []

    def handle_data(self, data: str) -> None:
        if self.in_json_ld:
            self.current_script.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_json_ld:
            self.scripts.append("".join(self.current_script))
            self.in_json_ld = False
            self.current_script = []


def normalize(value: str) -> str:
    return normalize_ingredient(value)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Recipe-Recommender/0.1"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="ignore")


def is_supported_cuisine(cuisine: str | None) -> bool:
    normalized_cuisine = normalize(cuisine or "")
    return normalized_cuisine in WEB_SOURCES_BY_CUISINE


def source_base_url(source: RecipeSource) -> str:
    return source.entry_urls[0]


def absolute_source_url(href: str, source: RecipeSource) -> str | None:
    url = urllib.parse.urljoin(source_base_url(source), href)
    parsed = urllib.parse.urlparse(url)

    if parsed.netloc not in source.allowed_hosts:
        return None

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None
    if len(path_parts) > 2:
        return None
    slug = path_parts[-1]
    if slug in EXCLUDED_SOURCE_SLUGS:
        return None
    if source.key == "indianhealthyrecipes" and slug.endswith("-recipes"):
        return None
    if "-recipes" in slug or slug.endswith("recipes"):
        return None
    if source.key == "simplyrecipes" and not (
        path_parts[0] == "recipes" or "recipe" in slug
    ):
        return None
    if any(part in EXCLUDED_PATH_PARTS for part in path_parts):
        return None

    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def is_likely_recipe_link_text(text: str) -> bool:
    normalized_text = " ".join(text.lower().split())
    return bool(normalized_text) and normalized_text not in GENERIC_LINK_TEXT


def parse_recipe_links(html: str, source: RecipeSource | None = None) -> list[tuple[str, str]]:
    source = source or WEB_SOURCES_BY_CUISINE["indian"][0]
    parser = LinkCollector()
    parser.feed(html)

    links: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for href, text in parser.links:
        if not is_likely_recipe_link_text(text):
            continue

        url = absolute_source_url(href, source)
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        links.append((url, text))

    return links[:MAX_SOURCE_LINKS]


def curated_recipe_links(source: RecipeSource) -> list[tuple[str, str]]:
    links = []
    for url in source.curated_urls:
        slug = urllib.parse.urlparse(url).path.strip("/").replace("-", " ")
        links.append((url, slug.title()))
    return links


def dedupe_links_by_url(links: list[tuple[str, str]]) -> list[tuple[str, str]]:
    deduped: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for url, title in links:
        if url in seen_urls:
            continue

        seen_urls.add(url)
        deduped.append((url, title))

    return deduped


def parse_json_ld_scripts(html: str) -> list[Any]:
    parser = JsonLdCollector()
    parser.feed(html)

    parsed_scripts = []
    for script in parser.scripts:
        try:
            parsed_scripts.append(json.loads(script))
        except json.JSONDecodeError:
            continue

    return parsed_scripts


def iter_recipe_objects(value: Any) -> list[dict]:
    recipes: list[dict] = []

    if isinstance(value, list):
        for item in value:
            recipes.extend(iter_recipe_objects(item))
        return recipes

    if not isinstance(value, dict):
        return recipes

    recipe_type = value.get("@type")
    recipe_types = recipe_type if isinstance(recipe_type, list) else [recipe_type]
    if any(str(item).lower() == "recipe" for item in recipe_types):
        recipes.append(value)

    for key in ("@graph", "itemListElement"):
        recipes.extend(iter_recipe_objects(value.get(key)))

    return recipes


def parse_duration_minutes(value: str | None) -> int | None:
    if not value:
        return None

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?)?",
        value,
    )
    if not match:
        return None

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    return days * 24 * 60 + hours * 60 + minutes


def recipe_time_minutes(recipe_data: dict) -> int:
    for field in ("totalTime", "cookTime", "prepTime"):
        minutes = parse_duration_minutes(recipe_data.get(field))
        if minutes:
            return minutes

    return 45


def normalize_recipe_cuisine(value: Any, fallback_cuisine: str) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""

    cuisine = str(value or "").strip()
    if not cuisine:
        return fallback_cuisine

    if "indian" in cuisine.lower():
        return "Indian"
    if "chinese" in cuisine.lower():
        return "Chinese"
    if "italian" in cuisine.lower():
        return "Italian"
    if "mexican" in cuisine.lower():
        return "Mexican"

    return cuisine


def clean_ingredient_line(line: str) -> str | None:
    lowered = normalize(line)
    lowered = re.sub(r"\([^)]*\)", " ", lowered)
    lowered = re.sub(r"[\d./]+", " ", lowered)
    lowered = re.sub(r"[^a-z ]+", " ", lowered)
    lowered = " ".join(lowered.split())

    for term in INGREDIENT_TERMS:
        if term in lowered:
            return normalize(term)

    words = [word for word in lowered.split() if word not in NOISE_WORDS]
    if not words:
        return None

    return normalize(" ".join(words[:2]))


def recipe_from_json_ld(
    recipe_data: dict,
    fallback_url: str,
    source: RecipeSource | None = None,
) -> Recipe | None:
    source = source or WEB_SOURCES_BY_CUISINE["indian"][0]
    name = recipe_data.get("name")
    raw_ingredients = recipe_data.get("recipeIngredient") or []
    if isinstance(raw_ingredients, str):
        raw_ingredients = [raw_ingredients]

    ingredients = [
        ingredient
        for ingredient in (clean_ingredient_line(line) for line in raw_ingredients)
        if ingredient
    ]
    ingredients = sorted(set(ingredients), key=ingredients.index)

    if not name or not ingredients:
        return None

    url = recipe_data.get("url") or fallback_url
    parsed_url = urllib.parse.urlparse(fallback_url)
    slug = parsed_url.path.strip("/").replace("/", "-")

    return Recipe(
        id=f"{source.key}-{slug}",
        name=name,
        cuisine=normalize_recipe_cuisine(recipe_data.get("recipeCuisine"), source.cuisine),
        core_ingredients=recipe_core_ingredients(str(name), ingredients),
        ingredients=ingredients,
        time_minutes=recipe_time_minutes(recipe_data),
        url=url,
    )


def recipe_from_html(
    html: str,
    fallback_url: str,
    source: RecipeSource | None = None,
) -> Recipe | None:
    source = source or WEB_SOURCES_BY_CUISINE["indian"][0]
    for script in parse_json_ld_scripts(html):
        for recipe_data in iter_recipe_objects(script):
            recipe = recipe_from_json_ld(recipe_data, fallback_url, source)
            if recipe:
                return recipe

    return None


def link_relevance_score(title: str, pantry: list[PantryItem]) -> int:
    normalized_title = normalize(title)
    title_terms = set(normalized_title.split())
    available = {normalize(item.name) for item in pantry}
    matched_title_terms = {
        term
        for term in INGREDIENT_TERMS
        if term in normalized_title and ingredient_matches(term, available)
    }
    direct_matches = {
        ingredient
        for ingredient in available
        if ingredient in normalized_title or any(token in title_terms for token in ingredient.split())
    }
    return len(matched_title_terms) * 3 + len(direct_matches)


def pantry_match_score(recipe: Recipe, pantry: list[PantryItem]) -> float:
    available = {normalize(item.name) for item in pantry}
    if not core_ingredients_available(
        recipe.name,
        recipe.ingredients,
        available,
        recipe.core_ingredients,
    ):
        return 0

    required = [ingredient for ingredient in recipe.ingredients if not is_pantry_staple(ingredient)]
    matched = [ingredient for ingredient in required if ingredient_matches(ingredient, available)]

    return len(matched) / len(required) if required else 0


def discover_web_recipes(
    pantry: list[PantryItem],
    min_match_score: float,
    existing_recipe_ids: set[str],
    limit: int,
    cuisine: str | None = None,
) -> list[Recipe]:
    if limit <= 0 or not is_supported_cuisine(cuisine):
        return []

    discovered: list[Recipe] = []
    seen_ids = set(existing_recipe_ids)
    sources = WEB_SOURCES_BY_CUISINE[normalize(cuisine or "")]

    for source in sources:
        failures = 0
        source_links = curated_recipe_links(source)

        for entry_url in source.entry_urls:
            try:
                source_links.extend(parse_recipe_links(fetch_text(entry_url), source))
            except Exception:
                failures += 1

        candidate_links = dedupe_links_by_url(source_links)
        ranked_links = sorted(
            candidate_links,
            key=lambda item: (-link_relevance_score(item[1], pantry), item[1]),
        )

        for url, _title in ranked_links[:MAX_RECIPE_PAGES]:
            if len(discovered) >= limit or failures >= MAX_DISCOVERY_FAILURES:
                break

            try:
                recipe = recipe_from_html(fetch_text(url), url, source)
            except Exception:
                failures += 1
                continue

            if not recipe or recipe.id in seen_ids:
                continue

            if normalize_recipe_cuisine(recipe.cuisine, source.cuisine).lower() != source.cuisine.lower():
                recipe.cuisine = source.cuisine

            if pantry_match_score(recipe, pantry) < min_match_score:
                continue

            seen_ids.add(recipe.id)
            discovered.append(recipe)

        if len(discovered) >= limit:
            break

    return discovered
