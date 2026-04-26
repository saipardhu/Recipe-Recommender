from backend.app.models import PantryItem
from backend.app.web_discovery import (
    WEB_SOURCES_BY_CUISINE,
    discover_web_recipes,
    parse_recipe_links,
    recipe_from_html,
)


def pantry(*names: str) -> list[PantryItem]:
    return [PantryItem(name=name, quantity="1") for name in names]


def recipe_html(
    name: str = "Chana Masala Recipe",
    ingredients: list[str] | None = None,
    total_time: str = "PT30M",
) -> str:
    recipe_ingredients = ingredients or [
        "1 cup chickpeas",
        "2 medium tomatoes",
        "1 onion",
        "2 cloves garlic",
        "1 teaspoon garam masala",
    ]
    ingredient_json = ", ".join(f'"{ingredient}"' for ingredient in recipe_ingredients)
    return f"""
    <html>
      <head>
        <script type="application/ld+json">
          {{
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "{name}",
            "recipeCuisine": "Indian",
            "recipeIngredient": [{ingredient_json}],
            "totalTime": "{total_time}",
            "url": "https://www.indianhealthyrecipes.com/chana-masala/"
          }}
        </script>
      </head>
    </html>
    """


def test_recipe_from_html_reads_json_ld_recipe():
    recipe = recipe_from_html(recipe_html(), "https://www.indianhealthyrecipes.com/chana-masala/")

    assert recipe is not None
    assert recipe.id == "indianhealthyrecipes-chana-masala"
    assert recipe.name == "Chana Masala Recipe"
    assert recipe.cuisine == "Indian"
    assert recipe.time_minutes == 30
    assert recipe.ingredients == ["chickpea", "tomato", "onion", "garlic", "garam masala"]
    assert recipe.core_ingredients == ["chickpea"]


def test_parse_recipe_links_keeps_recipe_page_urls_only():
    source = WEB_SOURCES_BY_CUISINE["indian"][0]
    links = parse_recipe_links(
        """
        <a href="/chana-masala/">Chana Masala Recipe</a>
        <a href="/recipes/">Recipes</a>
        <a href="https://example.com/offsite">Offsite</a>
        <a href="/chana-masala/">Duplicate</a>
        """,
        source,
    )

    assert links == [
        ("https://www.indianhealthyrecipes.com/chana-masala/", "Chana Masala Recipe"),
    ]


def test_discover_web_recipes_requires_supported_cuisine(monkeypatch):
    monkeypatch.setattr("backend.app.web_discovery.fetch_text", lambda url: "")

    recipes = discover_web_recipes(
        pantry("chickpeas", "tomato", "onion"),
        min_match_score=0.6,
        existing_recipe_ids=set(),
        limit=5,
        cuisine="British",
    )

    assert recipes == []


def test_discover_web_recipes_scores_and_returns_matching_indian_recipes(monkeypatch):
    home_html = """
    <a href="/chana-masala/">Chana Masala Recipe</a>
    <a href="/baingan-bharta/">Baingan Bharta Recipe</a>
    """

    def fake_fetch_text(url: str) -> str:
        if url == "https://www.indianhealthyrecipes.com/":
            return home_html
        if url.endswith("/chana-masala/"):
            return recipe_html()
        return recipe_html(
            name="Baingan Bharta Recipe",
            ingredients=["1 aubergine", "1 tomato", "1 onion", "1 clove garlic"],
        )

    monkeypatch.setattr("backend.app.web_discovery.fetch_text", fake_fetch_text)

    recipes = discover_web_recipes(
        pantry("chickpeas", "tomato", "onion", "garlic"),
        min_match_score=0.6,
        existing_recipe_ids=set(),
        limit=5,
        cuisine="Indian",
    )

    assert [recipe.name for recipe in recipes] == ["Chana Masala Recipe"]


def test_discover_web_recipes_uses_cuisine_specific_sources(monkeypatch):
    italian_source = WEB_SOURCES_BY_CUISINE["italian"][0]
    captured_urls = []

    def fake_fetch_text(url: str) -> str:
        captured_urls.append(url)
        if url == "https://www.vincenzosplate.com/":
            return '<a href="/tomato-pasta/">Tomato Pasta</a>'
        return recipe_html(
            name="Tomato Pasta",
            ingredients=["200g pasta", "3 tomatoes", "1 garlic clove"],
        ).replace('"recipeCuisine": "Indian"', '"recipeCuisine": "Italian"')

    monkeypatch.setattr("backend.app.web_discovery.fetch_text", fake_fetch_text)

    recipes = discover_web_recipes(
        pantry("pasta", "tomato", "garlic"),
        min_match_score=0.6,
        existing_recipe_ids=set(),
        limit=5,
        cuisine="Italian",
    )

    assert captured_urls[0] == italian_source.entry_urls[0]
    assert "vincenzosplate-tomato-pasta" in [recipe.id for recipe in recipes]
    assert {recipe.cuisine for recipe in recipes} == {"Italian"}


def test_configures_requested_cuisine_sources():
    assert WEB_SOURCES_BY_CUISINE["chinese"][0].entry_urls == ["https://omnivorescookbook.com/"]
    assert WEB_SOURCES_BY_CUISINE["italian"][0].entry_urls == ["https://www.vincenzosplate.com/"]
    assert [source.entry_urls[0] for source in WEB_SOURCES_BY_CUISINE["mexican"]] == [
        "https://www.mexicanplease.com/",
        "https://www.simplyrecipes.com/mexican-recipes-11734554",
    ]
