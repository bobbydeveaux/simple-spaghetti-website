/**
 * Search recipes by title and ingredients (case-insensitive)
 * @param {Array} recipes - Array of recipe objects
 * @param {string} query - Search term
 * @returns {Array} Filtered recipes matching the search query
 */
export function searchRecipes(recipes, query) {
  if (!query || query.trim() === '') {
    return recipes;
  }

  const searchTerm = query.toLowerCase().trim();

  return recipes.filter(recipe => {
    // Search in title
    if (recipe.title.toLowerCase().includes(searchTerm)) {
      return true;
    }

    // Search in ingredients
    if (recipe.ingredients.some(ingredient =>
      ingredient.toLowerCase().includes(searchTerm)
    )) {
      return true;
    }

    // Search in description
    if (recipe.description.toLowerCase().includes(searchTerm)) {
      return true;
    }

    return false;
  });
}

/**
 * Filter recipes by various criteria
 * @param {Array} recipes - Array of recipe objects
 * @param {Object} filters - Filter object containing search, pastaType, region, difficulty
 * @returns {Array} Filtered recipes
 */
export function filterRecipes(recipes, filters) {
  if (!recipes || !Array.isArray(recipes)) {
    return [];
  }

  let filteredRecipes = recipes;

  // Apply search filter
  if (filters.search) {
    filteredRecipes = searchRecipes(filteredRecipes, filters.search);
  }

  // Apply pasta type filter
  if (filters.pastaType && filters.pastaType !== '') {
    filteredRecipes = filteredRecipes.filter(recipe =>
      recipe.pastaType === filters.pastaType
    );
  }

  // Apply region filter
  if (filters.region && filters.region !== '') {
    filteredRecipes = filteredRecipes.filter(recipe =>
      recipe.region === filters.region
    );
  }

  // Apply difficulty filter
  if (filters.difficulty && filters.difficulty !== '') {
    filteredRecipes = filteredRecipes.filter(recipe =>
      recipe.difficulty === filters.difficulty
    );
  }

  return filteredRecipes;
}

/**
 * Get unique values for filter options from recipes array
 * @param {Array} recipes - Array of recipe objects
 * @param {string} field - Field name to extract unique values from
 * @returns {Array} Sorted array of unique values
 */
export function getUniqueValues(recipes, field) {
  if (!recipes || !Array.isArray(recipes)) {
    return [];
  }

  const uniqueValues = [...new Set(recipes.map(recipe => recipe[field]))];
  return uniqueValues.filter(value => value !== null && value !== undefined).sort();
}

/**
 * Get filter options for all filter types
 * @param {Array} recipes - Array of recipe objects
 * @returns {Object} Object containing arrays of unique values for each filter type
 */
export function getFilterOptions(recipes) {
  return {
    pastaTypes: getUniqueValues(recipes, 'pastaType'),
    regions: getUniqueValues(recipes, 'region'),
    difficulties: getUniqueValues(recipes, 'difficulty')
  };
}