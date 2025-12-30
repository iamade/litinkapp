import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Brain,
  Search,
  Filter,
  Clock,
  Award,
  Play,
} from "lucide-react";
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";

interface Book {
  id: string;
  title: string;
  author_name?: string;
  cover_image_url?: string;
  description?: string;
  book_type?: string;
  status?: string;
  progress?: number;
  image?: string;
}

export default function LearningMode() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [continueBooks, setContinueBooks] = useState<Book[]>([]);
  const [continueLoading, setContinueLoading] = useState(true);
  const [exploreBooks, setExploreBooks] = useState<Book[]>([]);
  const [exploreLoading, setExploreLoading] = useState(true);

  const categories = [
    { id: "all", label: "All Categories" },
    { id: "programming", label: "Programming" },
    { id: "science", label: "Science" },
    { id: "business", label: "Business" },
    { id: "design", label: "Design" },
    { id: "language", label: "Languages" },
  ];

  const filteredBooks = exploreBooks.filter((book) => {
    const matchesSearch =
      book.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (book.author_name || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  useEffect(() => {
    const fetchBooksWithProgress = async () => {
      setContinueLoading(true);
      try {
        const books = await userService.getLearningBooksWithProgress();
        setContinueBooks(
          Array.isArray(books) ? books.filter((b) => b.progress > 0) : []
        );
      } catch {
        toast.error("Failed to load your learning books");
      } finally {
        setContinueLoading(false);
      }
    };
    fetchBooksWithProgress();
  }, []);

  useEffect(() => {
    const fetchExploreBooks = async () => {
      setExploreLoading(true);
      try {
        // Changed to use user's own learning books instead of superadmin books
        const books = await userService.getMyLearningBooks();
        setExploreBooks(Array.isArray(books) ? books : []);
      } catch {
        toast.error("Failed to load your learning books");
      } finally {
        setExploreLoading(false);
      }
    };
    fetchExploreBooks();
  }, []);

  return (
    <div className="min-h-screen py-8 bg-gray-50 dark:bg-[#0F0F23] transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Learning Mode
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Transform any book into interactive tutorials, personalized lessons,
            and smart quizzes powered by AI. Learn at your own pace and earn
            verified credentials.
          </p>
        </div>

        {/* Continue Learning Section */}
        {continueLoading ? (
          <div className="text-center py-12 text-gray-600 dark:text-gray-400">
            Loading your learning books...
          </div>
        ) : (
          continueBooks.length > 0 && (
            <div className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
                <Clock className="h-7 w-7 text-purple-600 dark:text-purple-400 mr-2" />
                Continue Learning
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {continueBooks.map((book) => (
                  <div
                    key={book.id}
                    className="group bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
                  >
                    <div className="relative">
                      <img
                        src={book.cover_image_url || book.image}
                        alt={book.title}
                        className="w-full h-48 object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                      <div className="absolute bottom-4 left-4 right-4">
                        <div className="bg-white/20 backdrop-blur-sm rounded-full p-1 mb-2">
                          <div
                            className="bg-gradient-to-r from-green-500 to-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${book.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-white text-sm font-medium">
                          {book.progress}% Complete
                        </p>
                      </div>
                    </div>
                    <div className="p-6">
                      <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                        {book.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                        by {book.author_name}
                      </p>
                      <Link
                        to={`/book/${book.id}`}
                        className="inline-flex items-center space-x-2 bg-gradient-to-r from-green-500 to-blue-600 text-white px-4 py-2 rounded-full font-medium hover:from-green-600 hover:to-blue-700 transition-all"
                      >
                        <Play className="h-4 w-4" />
                        <span>Continue</span>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        )}

        {/* Search and Filter */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search books, authors, topics..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Featured Books Grid */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <BookOpen className="h-7 w-7 text-purple-600 dark:text-purple-400 mr-2" />
            My Learning Books
          </h2>
          {exploreLoading ? (
            <div className="text-center py-8 text-gray-600 dark:text-gray-400">
              Loading your learning books...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {filteredBooks.map((book) => (
                <div
                  key={book.id}
                  className="group bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <div className="relative">
                    <img
                      src={book.cover_image_url || book.image}
                      alt={book.title}
                      className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                    />
                  </div>
                  <div className="p-6">
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                      {book.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                      by {book.author_name}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                      {book.description}
                    </p>
                    <div className="flex space-x-2">
                      <Link
                        to={`/book/${book.id}`}
                        className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-full font-medium text-center hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
                      >
                        Start Learning
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Features Callout */}
        <div className="bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 rounded-2xl p-8 text-white text-center">
          <Brain className="h-16 w-16 mx-auto mb-4 text-white" />
          <h2 className="text-2xl font-bold mb-4">
            AI-Powered Learning Features
          </h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            Experience personalized tutorials, adaptive quizzes, voice
            interactions, and earn blockchain-verified badges as you progress.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Brain className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Smart Tutorials</h3>
              <p className="text-sm opacity-90">
                AI adapts content to your learning style
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Award className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Verified Badges</h3>
              <p className="text-sm opacity-90">
                Blockchain-certified achievements
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Play className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Voice Learning</h3>
              <p className="text-sm opacity-90">
                Interactive voice-powered lessons
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
