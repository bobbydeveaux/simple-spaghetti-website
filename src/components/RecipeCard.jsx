import React from 'react';
import { Link } from 'react-router-dom';

function RecipeCard({ recipe }) {
  if (!recipe) {
    return null;
  }

  return (
    <Link to={`/recipe/${recipe.id}`} className="block">
      <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200">
        {/* Recipe preview card will be implemented later */}
        <div className="p-4">
          <h3 className="text-lg font-semibold mb-2">{recipe.title || 'Recipe Title'}</h3>
          <p className="text-gray-600 text-sm">Coming soon...</p>
        </div>
      </div>
    </Link>
  );
}

export default RecipeCard;