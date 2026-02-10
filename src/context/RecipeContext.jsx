import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { filterRecipes, getFilterOptions } from '../utils/filterHelpers';
import recipesData from '../data/recipes.json';

// Create the context
const RecipeContext = createContext();

// Custom hook to use the Recipe context
export const useRecipes = () => {
  const context = useContext(RecipeContext);
  if (!context) {
    throw new Error('useRecipes must be used within a RecipeProvider');
  }
  return context;
};

// Recipe Provider component
export const RecipeProvider = ({ children }) => {
  // State for recipes and filters
  const [recipes, setRecipes] = useState([]);
  const [filters, setFilters] = useState({
    search: '',
    pastaType: '',
    region: '',
    difficulty: ''
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load recipes on component mount
  useEffect(() => {
    const loadRecipes = async () => {
      try {
        setLoading(true);
        // In a real app, this might be an API call
        // For now, we're using imported JSON data
        setRecipes(recipesData);
        setError(null);
      } catch (err) {
        setError('Failed to load recipes');
        console.error('Error loading recipes:', err);
      } finally {
        setLoading(false);
      }
    };

    loadRecipes();
  }, []);

  // Compute filtered recipes using useMemo for performance
  const filteredRecipes = useMemo(() => {
    return filterRecipes(recipes, filters);
  }, [recipes, filters]);

  // Get filter options for dropdowns
  const filterOptions = useMemo(() => {
    return getFilterOptions(recipes);
  }, [recipes]);

  // Function to update filters
  const updateFilters = (newFilters) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      ...newFilters
    }));
  };

  // Function to reset all filters
  const resetFilters = () => {
    setFilters({
      search: '',
      pastaType: '',
      region: '',
      difficulty: ''
    });
  };

  // Context value
  const value = {
    // Data
    recipes,
    filteredRecipes,

    // Filter state
    filters,
    setFilters: updateFilters,
    resetFilters,

    // Filter options
    filterOptions,

    // Loading states
    loading,
    error,

    // Computed values
    totalRecipes: recipes.length,
    filteredCount: filteredRecipes.length
  };

  return (
    <RecipeContext.Provider value={value}>
      {children}
    </RecipeContext.Provider>
  );
};