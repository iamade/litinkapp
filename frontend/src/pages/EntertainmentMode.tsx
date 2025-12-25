import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Search,
  Filter,
  Play,
  Star,
  Users,
  Clock,
  Heart,
  Zap,
  Film,
} from "lucide-react";
import { userService } from "../services/userService";

export default function EntertainmentMode() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("all");
  const [exploreStories, setExploreStories] = useState<any[]>([]);
  const [exploreLoading, setExploreLoading] = useState(true);

  const genres = [
    { id: "all", label: "All Genres" },
    { id: "fantasy", label: "Fantasy" },
    { id: "mystery", label: "Mystery" },
    { id: "romance", label: "Romance" },
    { id: "scifi", label: "Sci-Fi" },
    { id: "adventure", label: "Adventure" },
    { id: "thriller", label: "Thriller" },
  ];

  const filteredStories = exploreStories.filter((story) => {
    const matchesSearch =
      story.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (story.author_name || story.author || "")
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
    const matchesGenre =
      selectedGenre === "all" || story.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  const continueReading = exploreStories.filter((story) => story.progress > 0);

  useEffect(() => {
    const fetchExploreStories = async () => {
      setExploreLoading(true);
      try {
        // Changed to use user's own entertainment books instead of superadmin books
        const stories = await userService.getMyEntertainmentBooks();
        setExploreStories(Array.isArray(stories) ? stories : []);
      } catch {
        // Optionally show a toast
      } finally {
        setExploreLoading(false);
      }
    };
    fetchExploreStories();
  }, []);

  return (
    <div className="min-h-screen py-8 bg-gray-50 dark:bg-[#0F0F23] transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Entertainment Mode
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Immerse yourself in interactive stories where your choices matter.
            Experience branching narratives with AI-driven characters, voice
            interactions, and collectible NFTs.
          </p>
        </div>

        {/* Continue Reading Section */}
        {continueReading.length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
              <Clock className="h-7 w-7 text-purple-600 dark:text-purple-400 mr-2" />
              Continue Your Adventures
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {continueReading.map((story) => (
                <div
                  key={story.id}
                  className="group bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <div className="relative">
                    <img
                      src={story.image}
                      alt={story.title}
                      className="w-full h-48 object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-4 left-4 right-4">
                      <div className="bg-white/20 backdrop-blur-sm rounded-full p-1 mb-2">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-pink-600 h-2 rounded-full transition-all"
                          style={{ width: `${story.progress}%` }}
                        ></div>
                      </div>
                      <p className="text-white text-sm font-medium">
                        {story.progress}% Complete
                      </p>
                    </div>
                  </div>
                  <div className="p-6">
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                      {story.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                      by {story.author}
                    </p>
                    <Link
                      to={`/book/${story.id}`}
                      className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-4 py-2 rounded-full font-medium hover:from-purple-600 hover:to-pink-700 transition-all"
                    >
                      <Play className="h-4 w-4" />
                      <span>Continue Story</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Search and Filter */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search stories, authors, genres..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <select
                  value={selectedGenre}
                  onChange={(e) => setSelectedGenre(e.target.value)}
                  className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  {genres.map((genre) => (
                    <option key={genre.id} value={genre.id}>
                      {genre.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Featured Stories Grid */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Sparkles className="h-7 w-7 text-purple-600 dark:text-purple-400 mr-2" />
            My Entertainment Books
          </h2>
          {exploreLoading ? (
            <div className="text-center py-8 text-gray-600 dark:text-gray-400">
              Loading your entertainment books...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {filteredStories.map((story) => (
                <div
                  key={story.id}
                  className="group bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <div className="relative">
                    <img
                      src={story.cover_image_url || story.image}
                      alt={story.title}
                      className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                    />
                  </div>
                  <div className="p-6">
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                      {story.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                      by {story.author_name || story.author}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                      {story.description}
                    </p>
                    <div className="flex space-x-2">
                      <Link
                        to={`/book/${story.id}`}
                        className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 text-white py-2 px-4 rounded-full font-medium text-center hover:from-purple-600 hover:to-pink-700 transition-all transform hover:scale-105"
                      >
                        Start Story
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Features Callout */}
        <div className="bg-gradient-to-br from-purple-600 via-pink-600 to-indigo-700 rounded-2xl p-8 text-white text-center">
          <Sparkles className="h-16 w-16 mx-auto mb-4 text-white" />
          <h2 className="text-2xl font-bold mb-4">AI-Enhanced Entertainment</h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            Experience stories like never before with voice-driven characters,
            AI-generated scenes, and collectible animated NFTs that unlock as
            you progress.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Play className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Voice Characters</h3>
              <p className="text-sm opacity-90">
                AI-powered character voices bring stories to life
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Film className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Dynamic Scenes</h3>
              <p className="text-sm opacity-90">
                AI generates visual scenes based on your choices
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Star className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Collectible NFTs</h3>
              <p className="text-sm opacity-90">
                Earn unique animated collectibles
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
