import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Menu, X, User, LogOut, BookOpen } from 'lucide-react';

export default function Navbar() {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Home' },
    { path: '/learn', label: 'Learn' },
    { path: '/explore', label: 'Explore' },
    ...(user?.role === 'author' ? [{ path: '/author', label: 'Create' }] : []),
  ];

  return (
    <nav className="bg-white/95 backdrop-blur-lg border-b border-indigo-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 via-purple-600 to-blue-700 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-300 group-hover:scale-105">
                <BookOpen className="h-6 w-6 text-white" />
              </div>
              <div className="absolute -inset-1 bg-gradient-to-br from-indigo-600 via-purple-600 to-blue-700 rounded-xl opacity-20 blur group-hover:opacity-30 transition-opacity"></div>
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-700 bg-clip-text text-transparent">
              Litink
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`text-sm font-medium transition-colors hover:text-indigo-600 relative ${
                  location.pathname === item.path
                    ? 'text-indigo-600'
                    : 'text-gray-700'
                }`}
              >
                {item.label}
                {location.pathname === item.path && (
                  <div className="absolute -bottom-1 left-0 right-0 h-0.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-700 rounded-full"></div>
                )}
              </Link>
            ))}
          </div>

          {/* Desktop Auth */}
          <div className="hidden md:flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <Link
                  to="/dashboard"
                  className="text-sm font-medium text-gray-700 hover:text-indigo-600 transition-colors"
                >
                  Dashboard
                </Link>
                {user.role === 'author' && (
                  <Link
                    to="/author"
                    className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-700 text-white px-4 py-2 rounded-full font-medium hover:shadow-lg transition-all transform hover:scale-105"
                  >
                    Author Panel
                  </Link>
                )}
                <Link
                  to="/profile"
                  className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-indigo-600 transition-colors"
                >
                  <User className="h-4 w-4" />
                  <span>{user.displayName}</span>
                </Link>
                <button
                  onClick={signOut}
                  className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-red-600 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/auth"
                className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-700 text-white px-6 py-2 rounded-full font-medium hover:shadow-lg transition-all transform hover:scale-105"
              >
                Sign In
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-700 hover:text-indigo-600 transition-colors"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-indigo-100">
            <div className="flex flex-col space-y-3">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMenuOpen(false)}
                  className={`text-base font-medium transition-colors hover:text-indigo-600 px-2 py-1 ${
                    location.pathname === item.path
                      ? 'text-indigo-600'
                      : 'text-gray-700'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
              
              {user ? (
                <>
                  <Link
                    to="/dashboard"
                    onClick={() => setIsMenuOpen(false)}
                    className="text-base font-medium text-gray-700 hover:text-indigo-600 transition-colors px-2 py-1"
                  >
                    Dashboard
                  </Link>
                  {user.role === 'author' && (
                    <Link
                      to="/author"
                      onClick={() => setIsMenuOpen(false)}
                      className="text-base font-medium text-indigo-600 hover:text-indigo-700 transition-colors px-2 py-1"
                    >
                      Author Panel
                    </Link>
                  )}
                  <Link
                    to="/profile"
                    onClick={() => setIsMenuOpen(false)}
                    className="text-base font-medium text-gray-700 hover:text-indigo-600 transition-colors px-2 py-1"
                  >
                    Profile
                  </Link>
                  <button
                    onClick={() => {
                      signOut();
                      setIsMenuOpen(false);
                    }}
                    className="text-base font-medium text-gray-700 hover:text-red-600 transition-colors text-left px-2 py-1"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <Link
                  to="/auth"
                  onClick={() => setIsMenuOpen(false)}
                  className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-700 text-white px-4 py-2 rounded-full font-medium text-center mx-2"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}