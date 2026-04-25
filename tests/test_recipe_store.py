import json
import shutil
from pathlib import Path
from uuid import uuid4

from backend.app.models import Recipe
from backend.app import recipe_store


def make_test_dir() -> Path:
    test_dir = Path("tests") / "runtime-data" / str(uuid4())
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def remove_test_dir(test_dir: Path) -> None:
    shutil.rmtree(test_dir, ignore_errors=True)


def test_list_ingredients_merges_user_and_recipe_ingredients(monkeypatch):
    test_dir = make_test_dir()
    recipes_path = test_dir / "recipes.json"
    ingredients_path = test_dir / "ingredients.json"

    try:
        recipes_path.write_text(
            json.dumps(
                [
                    {
                        "id": "test-recipe",
                        "name": "Test Recipe",
                        "ingredients": ["tomato", "cheese"],
                        "time_minutes": 10,
                        "url": "https://example.com/test",
                    }
                ]
            ),
            encoding="utf-8",
        )
        ingredients_path.write_text(json.dumps(["avocado"]), encoding="utf-8")

        monkeypatch.setattr(recipe_store, "DATA_PATH", recipes_path)
        monkeypatch.setattr(recipe_store, "INGREDIENTS_PATH", ingredients_path)
        recipe_store.load_recipes.cache_clear()

        assert recipe_store.list_ingredients() == ["avocado", "cheese", "tomato"]
    finally:
        recipe_store.load_recipes.cache_clear()
        remove_test_dir(test_dir)


def test_add_ingredient_persists_normalized_unique_names(monkeypatch):
    test_dir = make_test_dir()
    ingredients_path = test_dir / "ingredients.json"

    try:
        ingredients_path.write_text(json.dumps(["avocado"]), encoding="utf-8")

        monkeypatch.setattr(recipe_store, "INGREDIENTS_PATH", ingredients_path)

        assert recipe_store.add_ingredient(" Avocado ") == "avocado"
        assert recipe_store.add_ingredient("Beef") == "beef"
        assert json.loads(ingredients_path.read_text(encoding="utf-8")) == ["avocado", "beef"]
    finally:
        remove_test_dir(test_dir)


def test_save_new_recipes_appends_only_new_recipe_ids(monkeypatch):
    test_dir = make_test_dir()
    recipes_path = test_dir / "recipes.json"

    try:
        recipes_path.write_text(
            json.dumps(
                [
                    {
                        "id": "existing",
                        "name": "Existing",
                        "ingredients": ["tomato"],
                        "time_minutes": 10,
                        "url": "https://example.com/existing",
                    }
                ]
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(recipe_store, "DATA_PATH", recipes_path)
        recipe_store.load_recipes.cache_clear()

        new_recipe = Recipe(
            id="new",
            name="New",
            ingredients=["beef"],
            time_minutes=20,
            url="https://example.com/new",
        )
        duplicate_recipe = Recipe(
            id="existing",
            name="Existing",
            ingredients=["tomato"],
            time_minutes=10,
            url="https://example.com/existing",
        )

        saved = recipe_store.save_new_recipes([duplicate_recipe, new_recipe])
        stored_ids = [
            item["id"]
            for item in json.loads(recipes_path.read_text(encoding="utf-8"))
        ]

        assert saved == [new_recipe]
        assert stored_ids == ["existing", "new"]
    finally:
        recipe_store.load_recipes.cache_clear()
        remove_test_dir(test_dir)
