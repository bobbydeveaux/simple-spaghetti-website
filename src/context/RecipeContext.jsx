import React, { createContext, useContext, useState, useMemo } from 'react';

const RecipeContext = createContext();

export function useRecipes() {
  const context = useContext(RecipeContext);
  if (!context) {
    throw new Error('useRecipes must be used within a RecipeProvider');
  }
  return context;
}

export function RecipeProvider({ children }) {
  // Will be loaded from recipes.json later
  const [recipes] = useState([]);

  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  });

  // Computed filtered recipes using useMemo
  const filteredRecipes = useMemo(() => {
    // Will implement filtering logic later
    // For now, just return recipes (filters will be used in future task)
    console.log('Filters available:', filters); // Prevent unused warning
    return recipes;
  }, [recipes, filters]);

  const value = {
    recipes,
    filters,
    setFilters,
    filteredRecipes
  };

  return (
    <RecipeContext.Provider value={value}>
      {children}
    </RecipeContext.Provider>
  );
}

export default RecipeContext;