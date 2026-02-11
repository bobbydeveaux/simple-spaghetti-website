import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { RecipeProvider } from './context/RecipeContext';
import Navigation from './components/Navigation';
import RecipeList from './components/RecipeList';
import RecipeDetail from './components/RecipeDetail';
import VotingApp from './voting/App';

// Simple About component
const About = () => (
  <div className="min-h-screen bg-gray-50 py-8">
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">About Pasta Recipes</h1>
        <p className="text-gray-700 mb-4">
          Welcome to our collection of authentic Italian pasta recipes! This site features traditional
          recipes from all regions of Italy, from the creamy risottos of Northern Italy to the
          spicy pasta dishes of the South.
        </p>
        <p className="text-gray-700 mb-4">
          Each recipe includes detailed ingredients, step-by-step instructions, and helpful information
          about cooking times, difficulty levels, and serving sizes. Use our search and filter tools
          to find the perfect pasta dish for your skill level and taste preferences.
        </p>
        <p className="text-gray-700">
          Browse by region to explore the diverse culinary traditions of Northern, Central,
          and Southern Italy, or filter by difficulty level to find recipes that match your
          cooking experience. Buon appetito! 🍝
        </p>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <RecipeProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <main className="py-8">
            <Routes>
              <Route path="/" element={<RecipeList />} />
              <Route path="/recipe/:id" element={<RecipeDetail />} />
              <Route path="/about" element={<About />} />
              <Route path="/voting/*" element={<VotingApp />} />
            </Routes>
          </main>
        </div>
      </Router>
    </RecipeProvider>
  );
}

export default App;
