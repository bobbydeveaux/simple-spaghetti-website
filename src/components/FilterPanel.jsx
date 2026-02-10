import { useRecipes } from '../context/RecipeContext'

export default function FilterPanel() {
  const { filters, setFilters } = useRecipes()

  const handleFilterChange = (filterType, value) => {
    setFilters({ ...filters, [filterType]: value })
  }

  const pastaTypes = ['Spaghetti', 'Penne', 'Lasagna', 'Fettuccine', 'Rigatoni', 'Tagliatelle']
  const regions = ['Northern Italy', 'Central Italy', 'Southern Italy']
  const difficulties = ['Easy', 'Medium', 'Hard']

  return (
    <div className="mb-8 bg-white p-4 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Filter Recipes</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Pasta Type Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Pasta Type
          </label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500"
            value={filters.pastaType}
            onChange={(e) => handleFilterChange('pastaType', e.target.value)}
          >
            <option value="">All Types</option>
            {pastaTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>

        {/* Region Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Region
          </label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500"
            value={filters.region}
            onChange={(e) => handleFilterChange('region', e.target.value)}
          >
            <option value="">All Regions</option>
            {regions.map(region => (
              <option key={region} value={region}>{region}</option>
            ))}
          </select>
        </div>

        {/* Difficulty Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Difficulty
          </label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500"
            value={filters.difficulty}
            onChange={(e) => handleFilterChange('difficulty', e.target.value)}
          >
            <option value="">All Levels</option>
            {difficulties.map(difficulty => (
              <option key={difficulty} value={difficulty}>{difficulty}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}