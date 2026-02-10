import React from 'react';
import { useRecipes } from '../context/RecipeContext';
import RecipeCard from './RecipeCard';
import SearchBar from './SearchBar';
import FilterPanel from './FilterPanel';

const RecipeList = () => {
  const { filteredRecipes, loading, error } = useRecipes();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center items-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading delicious recipes...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center items-center h-64">
            <div className="text-center">
              <div className="text-red-500 text-xl mb-2">⚠️</div>
              <p className="text-red-600">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Italian Pasta Recipes
          </h1>
          <p className="text-xl text-gray-600">
            Discover authentic Italian pasta dishes from all regions
          </p>
        </div>

        {/* Search and Filters */}
        <div className="mb-8">
          <SearchBar />
          <FilterPanel />
        </div>

        {/* Results */}
        {filteredRecipes.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🍝</div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-2">
              No recipes found
            </h3>
            <p className="text-gray-600 mb-6">
              Try adjusting your search terms or filters to find more recipes.
            </p>
            <div className="space-y-2 text-sm text-gray-500">
              <p>💡 Try searching for:</p>
              <div className="flex flex-wrap justify-center gap-2">
                <span className="px-2 py-1 bg-gray-100 rounded">carbonara</span>
                <span className="px-2 py-1 bg-gray-100 rounded">tomatoes</span>
                <span className="px-2 py-1 bg-gray-100 rounded">spaghetti</span>
                <span className="px-2 py-1 bg-gray-100 rounded">easy</span>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Recipe Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredRecipes.map((recipe) => (
                <RecipeCard key={recipe.id} recipe={recipe} />
              ))}
            </div>

            {/* Results Summary */}
            <div className="mt-8 text-center text-gray-600">
              Showing {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? 's' : ''}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default RecipeList;
