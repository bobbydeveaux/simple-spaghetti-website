import React, { createContext, useContext, useState, useEffect, useMemo } from 'react'
import recipesData from '../data/recipes.json'
import { filterRecipes } from '../utils/filterHelpers'

const RecipeContext = createContext()

export function useRecipes() {
  const context = useContext(RecipeContext)
  if (!context) {
    throw new Error('useRecipes must be used within a RecipeProvider')
  }
  return context
}

export function RecipeProvider({ children }) {
  const [recipes, setRecipes] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  })

  useEffect(() => {
    setRecipes(recipesData)
  }, [])

  const filteredRecipes = useMemo(() => {
    return filterRecipes(recipes, filters)
  }, [recipes, filters])

  const value = {
    recipes,
    filters,
    setFilters,
    filteredRecipes
  }

  return <RecipeContext.Provider value={value}>{children}</RecipeContext.Provider>
}