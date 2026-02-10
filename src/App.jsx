import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { RecipeProvider } from './context/RecipeContext'
import Navigation from './components/Navigation'
import RecipeList from './components/RecipeList'
import RecipeDetail from './components/RecipeDetail'

function App() {
  return (
    <RecipeProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<RecipeList />} />
              <Route path="/recipe/:id" element={<RecipeDetail />} />
            </Routes>
          </main>
        </div>
      </Router>
    </RecipeProvider>
  )
}

export default App