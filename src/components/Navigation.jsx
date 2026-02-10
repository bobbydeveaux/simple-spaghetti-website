import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const location = useLocation()

  const isActive = (path) => location.pathname === path

  return (
    <nav className="bg-primary-600 shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center py-4">
          {/* Logo/Brand */}
          <Link to="/" className="text-white text-2xl font-bold hover:text-primary-100">
            Pasta Recipes
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex space-x-8">
            <Link
              to="/"
              className={`text-white hover:text-primary-100 transition-colors ${
                isActive('/') ? 'text-primary-100 font-semibold' : ''
              }`}
            >
              Home
            </Link>
            <Link
              to="/about"
              className={`text-white hover:text-primary-100 transition-colors ${
                isActive('/about') ? 'text-primary-100 font-semibold' : ''
              }`}
            >
              About
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden text-white focus:outline-none focus:text-primary-100"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Navigation Menu */}
        {isMenuOpen && (
          <div className="md:hidden pb-4">
            <div className="flex flex-col space-y-4">
              <Link
                to="/"
                className={`text-white hover:text-primary-100 transition-colors ${
                  isActive('/') ? 'text-primary-100 font-semibold' : ''
                }`}
                onClick={() => setIsMenuOpen(false)}
              >
                Home
              </Link>
              <Link
                to="/about"
                className={`text-white hover:text-primary-100 transition-colors ${
                  isActive('/about') ? 'text-primary-100 font-semibold' : ''
                }`}
                onClick={() => setIsMenuOpen(false)}
              >
                About
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}