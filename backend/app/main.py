from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import IngredientCreate, RecommendationRequest, RecipeRecommendation
from .recipe_store import add_ingredient, list_ingredients
from .recommender import recommend_recipes


PROJECT_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Recipe Recommender API")

# The frontend is intentionally simple static HTML/CSS/JS; FastAPI owns the
# recommendation and catalog APIs behind it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home() -> FileResponse:
    # Serve the single-page UI while keeping API routes under /api.
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ingredients")
def ingredients(q: str = Query(default="", description="Ingredient search text")) -> list[str]:
    query = q.strip().lower()
    available_ingredients = list_ingredients()

    if not query:
        return available_ingredients

    return [ingredient for ingredient in available_ingredients if query in ingredient]


@app.post("/api/ingredients", status_code=201)
def create_ingredient(ingredient: IngredientCreate) -> dict[str, str]:
    # Unknown user-entered ingredients are persisted so autocomplete improves
    # over time, even before we have recipes using that ingredient.
    return {"name": add_ingredient(ingredient.name)}


@app.post("/api/recommendations")
def recommendations(request: RecommendationRequest) -> list[RecipeRecommendation]:
    # Recommendation logic stays server-side so future DB and web discovery work
    # can evolve without changing the browser contract.
    return recommend_recipes(request.pantry, cuisine=request.cuisine)


app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
