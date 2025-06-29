import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Menu, X, User, LogOut } from "lucide-react";
import { toast } from "react-hot-toast";

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleSignOut = () => {
    logout();
    navigate("/auth");
  };

  const handleExploreClick = (e: React.MouseEvent) => {
    e.preventDefault();
    toast("Explore feature coming soon! 🔍", {
      icon: "🌟",
      style: {
        borderRadius: "10px",
        background: "#333",
        color: "#fff",
      },
    });
  };

  const navItems = [
    { path: "/", label: "Home", showWhenLoggedIn: true },
    {
      path: "/learn",
      label: "Learn",
      showWhenLoggedIn: true,
    },
    {
      path: "/explore",
      label: "Explore",
      showWhenLoggedIn: true,
      onClick: handleExploreClick,
    },
    ...(user?.role === "author"
      ? [{ path: "/author", label: "Create", showWhenLoggedIn: true }]
      : []),
  ];

  // Filter nav items based on authentication status
  const visibleNavItems = navItems.filter(
    (item) => !item.showWhenLoggedIn || user
  );

  return (
    <nav className="bg-white/90 backdrop-blur-lg border-b border-purple-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-3">
            <img
              src="/litink.png"
              alt="Litink AI Logo"
              className="h-10 w-10 object-contain"
            />
            <span className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              Litink AI
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={item.onClick}
                className={`text-sm font-medium transition-colors hover:text-purple-600 ${
                  location.pathname === item.path
                    ? "text-purple-600"
                    : "text-gray-700"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* Desktop Auth */}
          <div className="hidden md:flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <Link
                  to="/dashboard"
                  className="text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors"
                >
                  Dashboard
                </Link>
                {user.role === "author" && (
                  <Link
                    to="/author"
                    className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-full font-medium hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
                  >
                    Author Panel
                  </Link>
                )}
                <Link
                  to="/profile"
                  className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors"
                >
                  <User className="h-4 w-4" />
                  <span>{user.display_name}</span>
                </Link>
                <button
                  onClick={handleSignOut}
                  className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-red-600 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/auth"
                className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-2 rounded-full font-medium hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
              >
                Sign In
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-700 hover:text-purple-600 transition-colors"
            >
              {isMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-purple-100">
            <div className="flex flex-col space-y-3">
              {visibleNavItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={(e) => {
                    if (item.onClick) {
                      item.onClick(e);
                    }
                    setIsMenuOpen(false);
                  }}
                  className={`text-base font-medium transition-colors hover:text-purple-600 px-2 py-1 ${
                    location.pathname === item.path
                      ? "text-purple-600"
                      : "text-gray-700"
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
                    className="text-base font-medium text-gray-700 hover:text-purple-600 transition-colors px-2 py-1"
                  >
                    Dashboard
                  </Link>
                  {user.role === "author" && (
                    <Link
                      to="/author"
                      onClick={() => setIsMenuOpen(false)}
                      className="text-base font-medium text-purple-600 hover:text-purple-700 transition-colors px-2 py-1"
                    >
                      Author Panel
                    </Link>
                  )}
                  <Link
                    to="/profile"
                    onClick={() => setIsMenuOpen(false)}
                    className="text-base font-medium text-gray-700 hover:text-purple-600 transition-colors px-2 py-1"
                  >
                    Profile
                  </Link>
                  <button
                    onClick={() => {
                      logout();
                      setIsMenuOpen(false);
                      navigate("/auth");
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
                  className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-full font-medium text-center mx-2"
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
