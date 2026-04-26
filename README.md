# Recipe-Recommender
A local-first recipe recommender that suggests dishes based on the ingredients in your pantry.

## Current MVP

This first local version uses a small JavaScript frontend backed by a Python FastAPI API. It lets a user:

- Search and select ingredients from an autocomplete list.
- Add any ingredient they have, even if it is not already in the catalog.
- Save new ingredients into the ingredient catalog for future autocomplete suggestions.
- Add a quantity for each ingredient.
- Pick a cuisine as a hard filter, or leave it as `Any cuisine`.
- Finish their pantry entry and see up to 5 ranked recipe recommendations.
- Open matching recipe links online.

Recipe matching currently uses a small JSON recipe dataset in `backend/data/recipes.json`.
The browser UI is intentionally lightweight JavaScript, while recipe and ingredient logic stays in the Python backend.
Frontend assets are served from `index.html` and the `static/` folder.
When local recipes cannot fill the recommendation list, the backend can backfill from [TheMealDB](https://www.themealdb.com/), then from curated recipe website sources for selected cuisines, and save useful matches into the local recipe dataset.

## How It Works

The recommendation flow is local-first:

1. The user builds a pantry list with ingredients and quantities.
2. The backend searches the local recipe book first.
3. Recipes must satisfy the 60% pantry match rule.
4. Recipes must include their core ingredient, such as pasta for a pasta dish or aubergine for Baingan Bharta.
5. If a cuisine is selected, it is treated as a hard filter.
6. If fewer than 5 useful local recipes are available, the backend tries trusted discovery sources.
7. Useful discovered recipes are saved back into `backend/data/recipes.json` for future requests.

## Product Direction

The recommendation flow should work like this:

1. Users can add any pantry ingredient, whether we already know it or not.
2. New ingredients are added to our ingredient catalog.
3. Once the user finalizes their pantry, the backend checks our recipe book first.
4. A recipe is useful only when at least 60% of its required ingredients are in the user's pantry.
5. The backend should always try to return 5 recipes.
6. The 5 recipes can be a mix of our recipe book and web-discovered recipes, but every recipe must satisfy the 60% match rule.
7. If our recipe book does not have enough useful matches to fill 5 recommendations, the backend should discover close recipe matches from trusted recipe sources.
8. Any useful discovered recipe should be stored in our recipe book so future requests use our own data first.
9. In the future, the recommendation count should be configurable from the user prompt or user preferences.

## Run locally

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\dependencies.txt
python -m uvicorn backend.app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

If dependencies were installed into the local `.python-packages` folder, use:

```powershell
python backend\dev_server.py
```

## Run tests

```powershell
python -m pytest
```

## API endpoints

- `GET /api/health` - returns a simple health check response so callers can confirm the backend is running.
- `GET /api/ingredients?q=tom` - returns ingredient autocomplete suggestions, optionally filtered by the `q` query parameter.
- `POST /api/ingredients` - adds a new ingredient to the ingredient catalog so it can appear in future autocomplete suggestions.
- `POST /api/recommendations` - accepts the user's pantry and optional cuisine filter, then returns ranked recipe recommendations.

### `GET /api/health`

Request:

```bash
curl http://127.0.0.1:8000/api/health
```

Response:

```json
{
  "status": "ok"
}
```

### `GET /api/ingredients`

Request:

```bash
curl "http://127.0.0.1:8000/api/ingredients?q=tom"
```

Response:

```json
[
  "tomato",
  "tomato puree"
]
```

### `POST /api/ingredients`

Request:

```bash
curl -X POST http://127.0.0.1:8000/api/ingredients \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"avocado\"}"
```

Response:

```json
{
  "name": "avocado"
}
```

### `POST /api/recommendations`

Request:

```bash
curl -X POST http://127.0.0.1:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d "{\"cuisine\":\"Indian\",\"pantry\":[{\"name\":\"chickpeas\",\"quantity\":\"100g\"},{\"name\":\"tomato\",\"quantity\":\"3\"},{\"name\":\"onion\",\"quantity\":\"2\"},{\"name\":\"garlic\",\"quantity\":\"2\"}]}"
```

Response:

```json
[
  {
    "id": "chana-masala",
    "name": "Chana Masala",
    "cuisine": "Indian",
    "ingredients": ["chickpea", "tomato", "onion", "garlic", "garam masala"],
    "time_minutes": 30,
    "url": "https://www.indianhealthyrecipes.com/chana-masala/",
    "matched_ingredients": ["chickpea", "tomato", "onion", "garlic"],
    "missing_ingredients": [],
    "match_score": 1.0
  }
]
```

## Recipe Discovery

Recommendations are local-first:

1. Search `backend/data/recipes.json`.
2. Keep only recipes with at least a 60% pantry match.
3. If a cuisine is selected, keep only recipes from that cuisine.
4. If fewer than 5 recipes qualify, query [TheMealDB](https://www.themealdb.com/) by cuisine first when a cuisine is selected, then by pantry ingredients.
5. If [TheMealDB](https://www.themealdb.com/) still cannot fill the list, scan curated cuisine-specific recipe sources and parse structured recipe metadata from matching pages.
6. Lookup full recipe details for discovered meals.
7. Store qualifying discovered recipes back into `backend/data/recipes.json`.

[TheMealDB](https://www.themealdb.com/) does not provide cooking time in its free response, so discovered recipes currently use a default `45` minute estimate.
Matching also normalizes common ingredient variants, such as singular/plural forms, and ignores pantry staples like salt, pepper, oil, and water when calculating the 60% match threshold.
Cuisine selection is a hard filter: if the user picks `Indian`, the backend should not return non-Indian recipes just to fill the list.
The recommender also requires a recipe's `core_ingredients` to be present, so dishes like Baingan Bharta are not recommended when aubergine is missing even if the supporting ingredients match. Discovered recipes infer this field when they are saved.
Website discovery is intentionally narrow right now: it does not crawl the wider internet, and it only reads recipe schema data from trusted source adapters.

Current curated website sources:

- Indian: [Indian Healthy Recipes](https://www.indianhealthyrecipes.com/)
- Chinese: [Omnivore's Cookbook](https://omnivorescookbook.com/)
- Italian: [Vincenzo's Plate](https://www.vincenzosplate.com/)
- Mexican: [Mexican Please](https://www.mexicanplease.com/) and [Simply Recipes Mexican Recipes](https://www.simplyrecipes.com/mexican-recipes-11734554)

## Roadmap

Near-term ideas tracked in `Requirements.txt`:

- Polish the frontend styling and interaction design.
- Let users upload recipe cards, screenshots, or PDFs.
- Use OCR/computer vision to extract recipe details from uploaded files.
- Add a user review step before imported recipes are saved.
- Make the recommendation limit configurable.

## Web routes

- `GET /`
- `GET /static/styles.css`
- `GET /static/app.js`
