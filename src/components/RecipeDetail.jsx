import { useParams, Link } from 'react-router-dom'
import { useRecipes } from '../context/RecipeContext'

export default function RecipeDetail() {
  const { id } = useParams()
  const { recipes } = useRecipes()

  const recipe = recipes.find(r => r.id === parseInt(id))

  if (!recipe) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">😞</div>
        <h2 className="text-2xl font-bold text-gray-700 mb-4">Recipe not found</h2>
        <p className="text-gray-500 mb-6">The recipe you're looking for doesn't exist.</p>
        <Link
          to="/"
          className="inline-flex items-center px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition"
        >
          ← Back to Recipes
        </Link>
      </div>
    )
  }

  const difficultyColor = {
    Easy: 'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Hard: 'bg-red-100 text-red-800'
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back Button */}
      <Link
        to="/"
        className="inline-flex items-center text-orange-600 hover:text-orange-800 mb-6"
      >
        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Recipes
      </Link>

      {/* Recipe Header */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <img
          src={recipe.image || '/api/placeholder/800/400'}
          alt={recipe.title}
          className="w-full h-64 md:h-80 object-cover"
          onError={(e) => {
            e.target.src = '/api/placeholder/800/400'
          }}
        />

        <div className="p-6 md:p-8">
          <div className="flex flex-wrap gap-3 mb-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${difficultyColor[recipe.difficulty]}`}>
              {recipe.difficulty}
            </span>
            <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">
              {recipe.pastaType}
            </span>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
              {recipe.region}
            </span>
          </div>

          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            {recipe.title}
          </h1>

          <p className="text-lg text-gray-700 mb-6 leading-relaxed">
            {recipe.description}
          </p>

          {/* Recipe Metadata */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg mb-8">
            <div className="text-center">
              <div className="font-semibold text-gray-900">{recipe.prepTime}</div>
              <div className="text-sm text-gray-600">Prep Time</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">{recipe.cookTime}</div>
              <div className="text-sm text-gray-600">Cook Time</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">{recipe.servings}</div>
              <div className="text-sm text-gray-600">Servings</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">{recipe.difficulty}</div>
              <div className="text-sm text-gray-600">Difficulty</div>
            </div>
          </div>

          {/* Ingredients */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Ingredients</h2>
            <ul className="space-y-2">
              {recipe.ingredients.map((ingredient, index) => (
                <li key={index} className="flex items-start">
                  <span className="text-orange-600 mr-3 mt-1.5">•</span>
                  <span className="text-gray-700">{ingredient}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Instructions */}
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Instructions</h2>
            <ol className="space-y-4">
              {recipe.instructions.map((instruction, index) => (
                <li key={index} className="flex">
                  <span className="flex-shrink-0 w-8 h-8 bg-orange-600 text-white rounded-full flex items-center justify-center text-sm font-semibold mr-4 mt-1">
                    {index + 1}
                  </span>
                  <p className="text-gray-700 pt-1">{instruction}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}