// Browser-only pantry state for the MVP. The backend owns catalogs and recipes;
// this array just tracks the current in-progress form session.
const pantry = [];

const form = document.querySelector("#ingredient-form");
const ingredientInput = document.querySelector("#ingredient-input");
const quantityInput = document.querySelector("#quantity-input");
const cuisineSelect = document.querySelector("#cuisine-select");
const suggestions = document.querySelector("#suggestions");
const inventoryList = document.querySelector("#inventory-list");
const emptyInventory = document.querySelector("#empty-inventory");
const recipeList = document.querySelector("#recipe-list");
const emptyRecipes = document.querySelector("#empty-recipes");
const finishButton = document.querySelector("#finish-button");
const clearButton = document.querySelector("#clear-button");
const matchCount = document.querySelector("#match-count");
const formError = document.querySelector("#form-error");
const recommendationLoader = document.querySelector("#recommendation-loader");
const recommendationSummary = document.querySelector("#recommendation-summary");

const cuisineAccents = {
  Argentinian: "rust",
  British: "sage",
  Chinese: "chili",
  Filipino: "sun",
  Greek: "olive",
  Indian: "turmeric",
  Italian: "tomato",
  Mexican: "avocado",
  Spanish: "paprika"
};

function normalize(value) {
  return value.trim().toLowerCase();
}

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = !message;
}

function getRecipeAccent(recipe) {
  return cuisineAccents[recipe.cuisine] || "tomato";
}

async function fetchJson(path, options = {}) {
  // Small wrapper keeps API error handling consistent across suggestions,
  // ingredient creation, and recommendations.
  const response = await fetch(path, {
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

function closeSuggestions() {
  suggestions.innerHTML = "";
  suggestions.classList.remove("is-open");
}

function selectIngredient(name) {
  ingredientInput.value = name;
  closeSuggestions();
  quantityInput.focus();
}

function renderSuggestionButton(label, ingredient) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => selectIngredient(ingredient));
  item.append(button);
  suggestions.append(item);
}

async function loadIngredientOptions(query = "") {
  return fetchJson(`/api/ingredients?q=${encodeURIComponent(query)}`);
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
    closeSuggestions();
    return;
  }

  let matches = [];
  try {
    matches = await loadIngredientOptions(query);
  } catch (error) {
    showFormError("Could not load ingredients. Is the backend running?");
    closeSuggestions();
    return;
  }

  const visibleMatches = matches
    // Exact matches do not need a dropdown; the user can just add the item.
    .filter((ingredient) => ingredient !== query)
    .filter((ingredient) => !pantry.some((item) => item.name === ingredient))
    .slice(0, 6);

  visibleMatches.forEach((ingredient) => renderSuggestionButton(ingredient, ingredient));

  if (visibleMatches.length === 0 && !matches.includes(query)) {
    // Users can enter any ingredient. If the catalog does not know it yet, the
    // add flow will persist it through POST /api/ingredients.
    renderSuggestionButton(`Add "${query}" as new ingredient`, query);
  }

  suggestions.classList.toggle("is-open", suggestions.children.length > 0);
}

function renderInventory() {
  inventoryList.innerHTML = "";
  emptyInventory.hidden = pantry.length > 0;

  pantry.forEach((item, index) => {
    const row = document.createElement("li");
    row.innerHTML = `
      <span class="ingredient-icon" aria-hidden="true"></span>
      <span class="ingredient-copy"><strong>${item.name}</strong> <span>${item.quantity}</span></span>
    `;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-button";
    removeButton.setAttribute("aria-label", `Remove ${item.name}`);
    removeButton.title = `Remove ${item.name}`;
    removeButton.textContent = "x";
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
  recommendationLoader.hidden = true;
  recommendationSummary.hidden = true;
  emptyRecipes.textContent = message;
  emptyRecipes.hidden = false;
  matchCount.textContent = "0 ready";
}

function clearRecommendations() {
  recipeList.innerHTML = "";
  recommendationLoader.hidden = true;
  recommendationSummary.hidden = true;
  matchCount.textContent = "0 ready";
  emptyRecipes.textContent = "Add ingredients and press Finish to see recipe ideas.";
  emptyRecipes.hidden = false;
}

function setRecommendationLoading(isLoading) {
  recommendationLoader.hidden = !isLoading;
  finishButton.disabled = isLoading;
  finishButton.textContent = isLoading ? "Searching..." : "Finish";
}

async function renderRecommendations() {
  if (pantry.length === 0) {
    showRecipeMessage("Add at least one ingredient before asking for recommendations.");
    return;
  }

  let rankedRecipes = [];
  const cuisine = cuisineSelect.value;
  try {
    setRecommendationLoading(true);
    recipeList.innerHTML = "";
    emptyRecipes.textContent = "This may take a few seconds when web discovery is needed.";
    emptyRecipes.hidden = false;
    // POST is used because the pantry is structured request data and will grow
    // with quantities, units, preferences, and future user context.
    rankedRecipes = await fetchJson("/api/recommendations", {
      method: "POST",
      body: JSON.stringify({ pantry, cuisine: cuisine || null })
    });
  } catch (error) {
    showRecipeMessage("Could not load recommendations. Is the backend running?");
    return;
  } finally {
    setRecommendationLoading(false);
  }

  recipeList.innerHTML = "";
  matchCount.textContent = `${rankedRecipes.length} ready`;
  emptyRecipes.hidden = rankedRecipes.length > 0;
  recommendationSummary.hidden = rankedRecipes.length === 0;

  if (rankedRecipes.length === 0) {
    showRecipeMessage("No recipe matches yet. Web discovery will backfill this list in the next iteration.");
    return;
  }

  recommendationSummary.innerHTML = `
    <span aria-hidden="true"></span>
    <p>Great job. You can make <strong>${rankedRecipes.length}</strong> delicious ${rankedRecipes.length === 1 ? "recipe" : "recipes"} with what you have.</p>
  `;

  rankedRecipes.forEach((recipe) => {
    const card = document.createElement("li");
    card.className = "recipe-card";
    card.dataset.accent = getRecipeAccent(recipe);

    const missingText = recipe.missing_ingredients.length
      ? `<p class="missing-list"><strong>Missing:</strong> ${recipe.missing_ingredients.map((ingredient) => `<span>${ingredient}</span>`).join("")}</p>`
      : `<p class="missing-list"><strong>Ready:</strong> <span>All ingredients available</span></p>`;

    card.innerHTML = `
      <div class="recipe-visual" aria-hidden="true"></div>
      <div class="recipe-content">
        <h3>${recipe.name}</h3>
        <p class="recipe-meta">
          ${recipe.cuisine ? `<span class="cuisine-pill">${recipe.cuisine}</span>` : ""}
          <span>${recipe.time_minutes} min</span>
          <span>${Math.round(recipe.match_score * 100)}% pantry match</span>
          <span>${recipe.matched_ingredients.length}/${recipe.ingredients.length} ingredients</span>
        </p>
        ${missingText}
        <a class="recipe-link" href="${recipe.url}" target="_blank" rel="noreferrer">Open recipe <span aria-hidden="true">-&gt;</span></a>
      </div>
    `;

    recipeList.append(card);
  });
}

async function addIngredient(event) {
  event.preventDefault();
  showFormError("");

  const name = normalize(ingredientInput.value);
  const quantity = quantityInput.value.trim();

  if (!name || !quantity) {
    showFormError("Ingredient and quantity are both required.");
    return;
  }

  let ingredientName = name;

  try {
    const matches = await loadIngredientOptions(name);
    if (!matches.includes(name)) {
      // Save new ingredients before adding them to pantry so future searches
      // can suggest them.
      ingredientName = await saveIngredient(name);
    }
  } catch (error) {
    showFormError("Could not save that ingredient. Is the backend running?");
    return;
  }

  const existing = pantry.find((item) => item.name === ingredientName);
  if (existing) {
    existing.quantity = quantity;
  } else {
    pantry.push({ name: ingredientName, quantity });
  }

  ingredientInput.value = "";
  quantityInput.value = "";
  closeSuggestions();
  renderInventory();
  clearRecommendations();
  ingredientInput.focus();
}

form.addEventListener("submit", addIngredient);
ingredientInput.addEventListener("input", renderSuggestions);
finishButton.addEventListener("click", renderRecommendations);
cuisineSelect.addEventListener("change", clearRecommendations);
clearButton.addEventListener("click", () => {
  pantry.splice(0, pantry.length);
  renderInventory();
  clearRecommendations();
  ingredientInput.focus();
});

document.addEventListener("click", (event) => {
  if (!suggestions.contains(event.target) && event.target !== ingredientInput) {
    closeSuggestions();
  }
});

renderInventory();
clearRecommendations();
