import React from 'react';
import { useParams } from 'react-router-dom';

function RecipeDetail() {
  const { id } = useParams();

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Recipe Detail</h1>
      {/* Full recipe page will be implemented later */}
      <div className="text-center text-gray-500">
        Recipe detail for ID: {id} coming soon...
      </div>
    </div>
  );
}

export default RecipeDetail;