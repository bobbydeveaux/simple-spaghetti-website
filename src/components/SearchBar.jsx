import React from 'react';
import { useRecipes } from '../context/RecipeContext';

const SearchBar = () => {
  const { filters, setFilters, filteredCount, totalRecipes } = useRecipes();

  const handleSearchChange = (event) => {
    const searchValue = event.target.value;
    setFilters({ search: searchValue });
  };

  const handleClearSearch = () => {
    setFilters({ search: '' });
  };

  return (
    <div className="w-full max-w-md mx-auto mb-6">
      <div className="relative">
        {/* Search Input */}
        <input
          type="text"
          value={filters.search}
          onChange={handleSearchChange}
          placeholder="Search recipes by name, ingredient, or description..."
          className="w-full px-4 py-3 pl-10 pr-10 text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />

        {/* Search Icon */}
        <div className="absolute inset-y-0 left-0 flex items-center pl-3">
          <svg
            className="w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Clear Button */}
        {filters.search && (
          <button
            onClick={handleClearSearch}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
            aria-label="Clear search"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Results Count */}
      <div className="mt-2 text-sm text-gray-600 text-center">
        {filters.search ? (
          <span>
            {filteredCount} of {totalRecipes} recipes match "{filters.search}"
          </span>
        ) : (
          <span>
            Showing all {totalRecipes} recipes
          </span>
        )}
      </div>
    </div>
  );
};

export default SearchBar;