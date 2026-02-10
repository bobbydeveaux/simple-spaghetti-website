import { Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'
import RecipeList from './components/RecipeList'
import RecipeDetail from './components/RecipeDetail'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="py-8">
        <Routes>
          <Route path="/" element={<RecipeList />} />
          <Route path="/recipe/:id" element={<RecipeDetail />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  )
}

// Simple About page component
function AboutPage() {
  return (
    <div className="container mx-auto px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-6">About Pasta Recipes</h1>
        <div className="bg-white rounded-lg shadow-md p-8">
          <p className="text-lg text-gray-600 mb-4">
            Welcome to our collection of authentic Italian pasta recipes! We're passionate about
            bringing you the finest traditional and modern pasta dishes from across Italy.
          </p>
          <p className="text-lg text-gray-600 mb-4">
            Our recipes are carefully curated to help home cooks of all skill levels create
            delicious pasta dishes. From simple weeknight meals to impressive dinner party
            centerpieces, you'll find something to love in our collection.
          </p>
          <p className="text-lg text-gray-600">
            Browse by region to explore the diverse culinary traditions of Northern, Central,
            and Southern Italy, or filter by difficulty level to find recipes that match your
            cooking experience.
          </p>
        </div>
      </div>
    </div>
  )
}

export default App