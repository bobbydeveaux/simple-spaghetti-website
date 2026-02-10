import { Link } from 'react-router-dom'

export default function RecipeCard({ recipe }) {
  const difficultyColor = {
    Easy: 'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Hard: 'bg-red-100 text-red-800'
  }

  return (
    <Link to={`/recipe/${recipe.id}`} className="group">
      <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
        <div className="aspect-w-16 aspect-h-9">
          <img
            src={recipe.image || '/api/placeholder/400/250'}
            alt={recipe.title}
            className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
            onError={(e) => {
              e.target.src = '/api/placeholder/400/250'
            }}
          />
        </div>
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-orange-600 transition-colors">
            {recipe.title}
          </h3>
          <div className="flex justify-between items-center mb-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${difficultyColor[recipe.difficulty] || difficultyColor.Medium}`}>
              {recipe.difficulty}
            </span>
            <div className="flex items-center text-gray-600 text-sm">
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {recipe.cookTime}
            </div>
          </div>
          <p className="text-gray-600 text-sm line-clamp-2">
            {recipe.description}
          </p>
          <div className="mt-3 text-xs text-gray-500">
            {recipe.pastaType} • {recipe.region}
          </div>
        </div>
      </div>
    </Link>
  )
}