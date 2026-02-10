import { useRecipes } from '../context/RecipeContext'

export default function SearchBar() {
  const { filters, setFilters } = useRecipes()

  const handleSearchChange = (e) => {
    setFilters({ ...filters, search: e.target.value })
  }

  return (
    <div className="mb-6">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m21 21-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-orange-500 focus:border-orange-500"
          placeholder="Search recipes or ingredients..."
          value={filters.search}
          onChange={handleSearchChange}
        />
      </div>
    </div>
  )
}