import { useRecipes } from '../context/RecipeContext'
import SearchBar from './SearchBar'
import FilterPanel from './FilterPanel'
import RecipeCard from './RecipeCard'

export default function RecipeList() {
  const { filteredRecipes } = useRecipes()

  return (
    <div>
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Delicious Pasta Recipes
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Discover authentic Italian pasta recipes from all regions. From simple spaghetti to complex lasagnas, find your perfect dish.
        </p>
      </div>

      <SearchBar />
      <FilterPanel />

      {filteredRecipes.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">🍝</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No recipes found</h3>
          <p className="text-gray-500">Try adjusting your search or filters</p>
        </div>
      ) : (
        <>
          <div className="mb-4 text-gray-600">
            Found {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? 's' : ''}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredRecipes.map(recipe => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}