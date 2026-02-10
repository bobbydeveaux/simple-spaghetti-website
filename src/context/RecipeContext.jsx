import React, { createContext, useContext, useState, useEffect, useMemo } from 'react'
import recipesData from '../data/recipes.json'
import { filterRecipes } from '../utils/filterHelpers'

const RecipeContext = createContext()

export function RecipeProvider({ children }) {
  const [recipes, setRecipes] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  })

  useEffect(() => {
    // Load recipes on component mount
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

export function useRecipes() {
  const context = useContext(RecipeContext)
  if (context === undefined) {
    throw new Error('useRecipes must be used within a RecipeProvider')
  }
  return context
}