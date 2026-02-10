/**
 * Filter recipes based on provided filters
 * @param {Array} recipes - Array of recipe objects
 * @param {Object} filters - Filter object with search, pastaType, region, difficulty
 * @returns {Array} Filtered array of recipes
 */
export function filterRecipes(recipes, filters) {
  if (!recipes || !Array.isArray(recipes)) {
    return [];
  }

  let filtered = recipes;

  // Search filter - will implement later
  if (filters.search) {
    // TODO: implement search by title and ingredients
  }

  // Pasta type filter - will implement later
  if (filters.pastaType) {
    // TODO: implement pasta type filtering
  }

  // Region filter - will implement later
  if (filters.region) {
    // TODO: implement region filtering
  }

  // Difficulty filter - will implement later
  if (filters.difficulty) {
    // TODO: implement difficulty filtering
  }

  return filtered;
}

/**
 * Search recipes by query string
 * @param {Array} recipes - Array of recipe objects
 * @param {string} query - Search query
 * @returns {Array} Array of recipes matching the query
 */
export function searchRecipes(recipes, query) {
  if (!recipes || !Array.isArray(recipes) || !query) {
    return recipes || [];
  }

  const searchTerm = query.toLowerCase().trim();

  return recipes.filter(recipe => {
    // TODO: implement search by title and ingredients
    const title = (recipe.title || '').toLowerCase();
    const ingredients = Array.isArray(recipe.ingredients)
      ? recipe.ingredients.join(' ').toLowerCase()
      : '';

    return title.includes(searchTerm) || ingredients.includes(searchTerm);
  });
}