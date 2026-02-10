export function filterRecipes(recipes, filters) {
  if (!recipes || recipes.length === 0) return []

  return recipes.filter(recipe => {
    // Search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase()
      const titleMatch = recipe.title.toLowerCase().includes(searchTerm)
      const ingredientsMatch = recipe.ingredients.some(ingredient =>
        ingredient.toLowerCase().includes(searchTerm)
      )
      if (!titleMatch && !ingredientsMatch) return false
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
  if (!query) return recipes

  const searchTerm = query.toLowerCase()
  return recipes.filter(recipe => {
    const titleMatch = recipe.title.toLowerCase().includes(searchTerm)
    const ingredientsMatch = recipe.ingredients.some(ingredient =>
      ingredient.toLowerCase().includes(searchTerm)
    )
    return titleMatch || ingredientsMatch
  })
}