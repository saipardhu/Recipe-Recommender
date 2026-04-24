# Recipe-Recommender
A sample recommender for food recipe based on ingredients you have

## Current MVP

This first local version uses a small JavaScript frontend backed by a Python FastAPI API. It lets a user:

- Search and select ingredients from an autocomplete list.
- Add any ingredient they have, even if it is not already in the catalog.
- Save new ingredients into the ingredient catalog for future autocomplete suggestions.
- Add a quantity for each ingredient.
- Finish their pantry entry and see up to 5 ranked recipe recommendations.
- Open matching recipe links online.

Recipe matching currently uses a small JSON recipe dataset in `backend/data/recipes.json`.
The browser UI is intentionally lightweight JavaScript, while recipe and ingredient logic stays in the Python backend.
Frontend assets are served from `index.html` and the `static/` folder.

## Product Direction

The recommendation flow should work like this:

1. Users can add any pantry ingredient, whether we already know it or not.
2. New ingredients are added to our ingredient catalog.
3. Once the user finalizes their pantry, the backend checks our recipe book first.
4. A recipe is useful only when at least 60% of its required ingredients are in the user's pantry.
5. The backend should always try to return 5 recipes.
6. The 5 recipes can be a mix of our recipe book and web-discovered recipes, but every recipe must satisfy the 60% match rule.
7. If our recipe book does not have enough useful matches to fill 5 recommendations, the backend should discover close recipe matches from the web.
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

## API endpoints

- `GET /api/health`
- `GET /api/ingredients?q=tom`
- `POST /api/ingredients`
- `POST /api/recommendations`

## Web routes

- `GET /`
- `GET /static/styles.css`
- `GET /static/app.js`

Example recommendation request:

```json
{
  "pantry": [
    { "name": "tomato", "quantity": "3" },
    { "name": "cheese", "quantity": "1 block" }
  ]
}
```
