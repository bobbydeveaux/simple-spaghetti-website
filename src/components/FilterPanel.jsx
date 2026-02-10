import React from 'react';
import { useRecipes } from '../context/RecipeContext';

const FilterPanel = () => {
  const { filters, setFilters, filterOptions, resetFilters } = useRecipes();

  const handleFilterChange = (filterType, value) => {
    setFilters({ [filterType]: value });
  };

  const hasActiveFilters = filters.pastaType || filters.region || filters.difficulty;

  return (
    <div className="w-full mb-6 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="flex flex-wrap items-center gap-4">
        {/* Filter Title */}
        <h3 className="text-lg font-semibold text-gray-800 flex-shrink-0">
          Filters:
        </h3>

        {/* Pasta Type Filter */}
        <div className="flex flex-col">
          <label htmlFor="pastaType" className="text-sm font-medium text-gray-700 mb-1">
            Pasta Type
          </label>
          <select
            id="pastaType"
            value={filters.pastaType}
            onChange={(e) => handleFilterChange('pastaType', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[120px]"
          >
            <option value="">All Types</option>
            {filterOptions.pastaTypes.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Region Filter */}
        <div className="flex flex-col">
          <label htmlFor="region" className="text-sm font-medium text-gray-700 mb-1">
            Region
          </label>
          <select
            id="region"
            value={filters.region}
            onChange={(e) => handleFilterChange('region', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[120px]"
          >
            <option value="">All Regions</option>
            {filterOptions.regions.map((region) => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
        </div>

        {/* Difficulty Filter */}
        <div className="flex flex-col">
          <label htmlFor="difficulty" className="text-sm font-medium text-gray-700 mb-1">
            Difficulty
          </label>
          <select
            id="difficulty"
            value={filters.difficulty}
            onChange={(e) => handleFilterChange('difficulty', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[120px]"
          >
            <option value="">All Levels</option>
            {filterOptions.difficulties.map((difficulty) => (
              <option key={difficulty} value={difficulty}>
                {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            onClick={resetFilters}
            className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-600">Active filters:</span>

            {filters.pastaType && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Type: {filters.pastaType}
                <button
                  onClick={() => handleFilterChange('pastaType', '')}
                  className="ml-1 text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            )}

            {filters.region && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Region: {filters.region}
                <button
                  onClick={() => handleFilterChange('region', '')}
                  className="ml-1 text-green-600 hover:text-green-800"
                >
                  ×
                </button>
              </span>
            )}

            {filters.difficulty && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                Difficulty: {filters.difficulty}
                <button
                  onClick={() => handleFilterChange('difficulty', '')}
                  className="ml-1 text-orange-600 hover:text-orange-800"
                >
                  ×
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterPanel;
