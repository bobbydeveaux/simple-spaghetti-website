import React, { createContext, useContext, useState } from 'react'

const RecipeContext = createContext()

export function useRecipes() {
  const context = useContext(RecipeContext)
  if (!context) {
    throw new Error('useRecipes must be used within a RecipeProvider')
  }
  return context
}

export function RecipeProvider({ children }) {
  const [recipes] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  })

  const filteredRecipes = recipes

  const value = {
    recipes,
    filters,
    setFilters,
    filteredRecipes
  }

  return <RecipeContext.Provider value={value}>{children}</RecipeContext.Provider>
}