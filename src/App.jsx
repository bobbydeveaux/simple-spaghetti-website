import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { RecipeProvider } from './context/RecipeContext';
import Navigation from './components/Navigation';
import RecipeList from './components/RecipeList';
import RecipeDetail from './components/RecipeDetail';
import './index.css';

function App() {
  return (
    <RecipeProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <main>
            <Routes>
              <Route path="/" element={<RecipeList />} />
              <Route path="/recipe/:id" element={<RecipeDetail />} />
              <Route path="/about" element={
                <div className="container mx-auto px-4 py-8 text-center">
                  <h1 className="text-3xl font-bold mb-4">About</h1>
                  <p className="text-gray-600">
                    Welcome to our pasta recipe collection!
                    Discover delicious pasta dishes from around Italy.
                  </p>
                </div>
              } />
              <Route path="*" element={
                <div className="container mx-auto px-4 py-8 text-center">
                  <h1 className="text-3xl font-bold mb-4">404 - Page Not Found</h1>
                  <p className="text-gray-600">
                    The page you&apos;re looking for doesn&apos;t exist.
                  </p>
                </div>
              } />
            </Routes>
          </main>
        </div>
      </Router>
    </RecipeProvider>
  );
}

export default App;