export function filterRecipes(recipes, filters) {
  return recipes.filter(recipe => {
    // Search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase()
      const titleMatch = recipe.title.toLowerCase().includes(searchTerm)
      const ingredientMatch = recipe.ingredients.some(ingredient =>
        ingredient.toLowerCase().includes(searchTerm)
      )
      if (!titleMatch && !ingredientMatch) {
        return false
      }
    }

    // Pasta type filter
    if (filters.pastaType && recipe.pastaType !== filters.pastaType) {
      return false
    }

    // Region filter
    if (filters.region && recipe.region !== filters.region) {
      return false
    }

    // Difficulty filter
    if (filters.difficulty && recipe.difficulty !== filters.difficulty) {
      return false
    }

    return true
  })
}

export function searchRecipes(recipes, query) {
  const searchTerm = query.toLowerCase()
  return recipes.filter(recipe => {
    const titleMatch = recipe.title.toLowerCase().includes(searchTerm)
    const ingredientMatch = recipe.ingredients.some(ingredient =>
      ingredient.toLowerCase().includes(searchTerm)
    )
    return titleMatch || ingredientMatch
  })
}