import React from 'react';

function FilterPanel({ filters = {}, onFiltersChange }) {
  // Prevent unused variable warnings during development
  if (filters || onFiltersChange) { /* placeholder */ }
  return (
    <div className="mb-6 p-4 bg-gray-50 rounded-lg">
      <h3 className="text-lg font-semibold mb-4">Filter Recipes</h3>
      {/* Checkbox/dropdown filters will be implemented later */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Pasta Type
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            disabled
          >
            <option>All Types</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Region
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            disabled
          >
            <option>All Regions</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Difficulty
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            disabled
          >
            <option>All Difficulties</option>
          </select>
        </div>
      </div>
      <p className="text-sm text-gray-500 mt-2">Filtering functionality coming soon...</p>
    </div>
  );
}

export default FilterPanel;