from pydantic import BaseModel, Field


class PantryItem(BaseModel):
    name: str = Field(min_length=1)
    quantity: str = Field(min_length=1)


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1)


class RecommendationRequest(BaseModel):
    pantry: list[PantryItem]
    cuisine: str | None = None


class Recipe(BaseModel):
    id: str
    name: str
    cuisine: str | None = None
    core_ingredients: list[str] = Field(default_factory=list)
    ingredients: list[str]
    time_minutes: int
    url: str


class RecipeRecommendation(BaseModel):
    id: str
    name: str
    cuisine: str | None = None
    ingredients: list[str]
    time_minutes: int
    url: str
    matched_ingredients: list[str]
    missing_ingredients: list[str]
    match_score: float
