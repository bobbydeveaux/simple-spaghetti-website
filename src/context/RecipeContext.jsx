import { createContext, useContext, useState, useEffect, useMemo } from 'react'

const RecipeContext = createContext()

export function useRecipes() {
  const context = useContext(RecipeContext)
  if (context === undefined) {
    throw new Error('useRecipes must be used within a RecipeProvider')
  }
  return context
}

export function RecipeProvider({ children }) {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  })

  // Load recipes data on mount
  useEffect(() => {
    const loadRecipes = async () => {
      try {
        setLoading(true)
        // For now, we'll use empty array until recipes.json is created in next task
        // In the future: const response = await fetch('/src/data/recipes.json')
        // const data = await response.json()
        const data = []
        setRecipes(data)
      } catch (err) {
        setError('Failed to load recipes')
        console.error('Error loading recipes:', err)
      } finally {
        setLoading(false)
      }
    }

    loadRecipes()
  }, [])

  // Compute filtered recipes based on current filters
  const filteredRecipes = useMemo(() => {
    if (!recipes.length) return []

    return recipes.filter(recipe => {
      // Search filter - check title and ingredients
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase()
        const titleMatch = recipe.title?.toLowerCase().includes(searchTerm)
        const ingredientMatch = recipe.ingredients?.some(ing =>
          ing.toLowerCase().includes(searchTerm)
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
  }, [recipes, filters])

  const value = {
    recipes,
    filteredRecipes,
    filters,
    setFilters,
    loading,
    error
  }

  return (
    <RecipeContext.Provider value={value}>
      {children}
    </RecipeContext.Provider>
  )
}