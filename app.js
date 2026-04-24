const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

const pantry = [];
let ingredientOptions = [];

const form = document.querySelector("#ingredient-form");
const ingredientInput = document.querySelector("#ingredient-input");
const quantityInput = document.querySelector("#quantity-input");
const suggestions = document.querySelector("#suggestions");
const inventoryList = document.querySelector("#inventory-list");
const emptyInventory = document.querySelector("#empty-inventory");
const recipeList = document.querySelector("#recipe-list");
const emptyRecipes = document.querySelector("#empty-recipes");
const finishButton = document.querySelector("#finish-button");
const clearButton = document.querySelector("#clear-button");
const matchCount = document.querySelector("#match-count");

function normalize(value) {
  return value.trim().toLowerCase();
}

function selectIngredient(name) {
  ingredientInput.value = name;
  suggestions.classList.remove("is-open");
  quantityInput.focus();
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

async function loadIngredientOptions(query = "") {
  ingredientOptions = await fetchJson(`/api/ingredients?q=${encodeURIComponent(query)}`);
  return ingredientOptions;
}

async function saveIngredient(name) {
  const ingredient = await fetchJson("/api/ingredients", {
    method: "POST",
    body: JSON.stringify({ name })
  });

  return ingredient.name;
}

async function renderSuggestions() {
  const query = normalize(ingredientInput.value);
  suggestions.innerHTML = "";

  if (!query) {
    suggestions.classList.remove("is-open");
    return;
  }

  let matches = [];
  try {
    matches = await loadIngredientOptions(query);
  } catch (error) {
    showRecipeMessage("Could not load ingredients. Is the backend running?");
    return;
  }

  matches = matches
    .filter((ingredient) => !pantry.some((item) => item.name === ingredient))
    .slice(0, 6);

  if (matches.length === 0) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `Add "${query}" as new ingredient`;
    button.addEventListener("click", () => selectIngredient(query));
    item.append(button);
    suggestions.append(item);
    suggestions.classList.add("is-open");
    return;
  }

  matches.forEach((ingredient) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = ingredient;
    button.addEventListener("click", () => selectIngredient(ingredient));
    item.append(button);
    suggestions.append(item);
  });

  suggestions.classList.add("is-open");
}

function renderInventory() {
  inventoryList.innerHTML = "";
  emptyInventory.hidden = pantry.length > 0;

  pantry.forEach((item, index) => {
    const row = document.createElement("li");
    row.innerHTML = `<span><strong>${item.name}</strong> <span>${item.quantity}</span></span>`;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-button";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      pantry.splice(index, 1);
      renderInventory();
      clearRecommendations();
    });

    row.append(removeButton);
    inventoryList.append(row);
  });
}

function showRecipeMessage(message) {
  recipeList.innerHTML = "";
  emptyRecipes.textContent = message;
  emptyRecipes.hidden = false;
  matchCount.textContent = "0 ready";
}

function clearRecommendations() {
  recipeList.innerHTML = "";
  matchCount.textContent = "0 ready";
  emptyRecipes.textContent = "Add ingredients and press Finish to see recipe ideas.";
  emptyRecipes.hidden = false;
}

async function renderRecommendations() {
  if (pantry.length === 0) {
    showRecipeMessage("Add at least one ingredient before asking for recommendations.");
    return;
  }

  let rankedRecipes = [];
  try {
    rankedRecipes = await fetchJson("/api/recommendations", {
      method: "POST",
      body: JSON.stringify({ pantry })
    });
  } catch (error) {
    showRecipeMessage("Could not load recommendations. Is the backend running?");
    return;
  }

  recipeList.innerHTML = "";
  matchCount.textContent = `${rankedRecipes.length} ready`;
  emptyRecipes.hidden = rankedRecipes.length > 0;

  if (rankedRecipes.length === 0) {
    showRecipeMessage("No recipe matches yet. Try adding more ingredients.");
    return;
  }

  rankedRecipes.forEach((recipe) => {
    const card = document.createElement("li");
    card.className = "recipe-card";

    const missingText = recipe.missing_ingredients.length
      ? `<p class="missing-list">Missing: ${recipe.missing_ingredients.map((ingredient) => `<span>${ingredient}</span>`).join("")}</p>`
      : `<p class="missing-list"><span>All ingredients available</span></p>`;

    card.innerHTML = `
      <h3>${recipe.name}</h3>
      <p class="recipe-meta">
        <span>${recipe.time_minutes} min</span>
        <span>${Math.round(recipe.match_score * 100)}% pantry match</span>
        <span>${recipe.matched_ingredients.length}/${recipe.ingredients.length} ingredients</span>
      </p>
      ${missingText}
      <a class="recipe-link" href="${recipe.url}" target="_blank" rel="noreferrer">Open recipe</a>
    `;

    recipeList.append(card);
  });
}

async function addIngredient(event) {
  event.preventDefault();

  const name = normalize(ingredientInput.value);
  const quantity = quantityInput.value.trim();

  if (!name || !quantity) {
    return;
  }

  let ingredientName = name;

  if (!ingredientOptions.includes(ingredientName)) {
    await loadIngredientOptions(name);
  }

  if (!ingredientOptions.includes(ingredientName)) {
    try {
      const savedIngredient = await saveIngredient(name);
      ingredientName = savedIngredient;
      ingredientOptions.push(savedIngredient);
    } catch (error) {
      showRecipeMessage("Could not save that ingredient. Is the backend running?");
      return;
    }
  }

  const existing = pantry.find((item) => item.name === ingredientName);
  if (existing) {
    existing.quantity = quantity;
  } else {
    pantry.push({ name: ingredientName, quantity });
  }

  ingredientInput.value = "";
  quantityInput.value = "";
  suggestions.classList.remove("is-open");
  renderInventory();
  clearRecommendations();
  ingredientInput.focus();
}

form.addEventListener("submit", addIngredient);
ingredientInput.addEventListener("input", renderSuggestions);
finishButton.addEventListener("click", renderRecommendations);
clearButton.addEventListener("click", () => {
  pantry.splice(0, pantry.length);
  renderInventory();
  clearRecommendations();
  ingredientInput.focus();
});

document.addEventListener("click", (event) => {
  if (!suggestions.contains(event.target) && event.target !== ingredientInput) {
    suggestions.classList.remove("is-open");
  }
});

loadIngredientOptions().catch(() => {
  showRecipeMessage("Start the backend to load ingredients and recommendations.");
});
renderInventory();
clearRecommendations();
