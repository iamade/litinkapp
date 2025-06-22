import React, { useState } from 'react';
import { Link } from 'react-router-dom';
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
  Film
} from 'lucide-react';

export default function EntertainmentMode() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('all');

  const genres = [
    { id: 'all', label: 'All Genres' },
    { id: 'fantasy', label: 'Fantasy' },
    { id: 'mystery', label: 'Mystery' },
    { id: 'romance', label: 'Romance' },
    { id: 'scifi', label: 'Sci-Fi' },
    { id: 'adventure', label: 'Adventure' },
    { id: 'thriller', label: 'Thriller' }
  ];

  const featuredStories = [
    {
      id: 1,
      title: 'The Crystal Chronicles',
      author: 'Elena Mystral',
      genre: 'fantasy',
      duration: '4 hours',
      readers: 12500,
      rating: 4.9,
      progress: 0,
      choices: 47,
      image: 'https://images.pexels.com/photos/1029141/pexels-photo-1029141.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Embark on a magical journey where your choices shape the destiny of an enchanted realm.',
      tags: ['Magic', 'Dragons', 'Multiple Endings']
    },
    {
      id: 2,
      title: 'Digital Shadows',
      author: 'Marcus Cyber',
      genre: 'scifi',
      duration: '5 hours',
      readers: 8900,
      rating: 4.7,
      progress: 65,
      choices: 38,
      image: 'https://images.pexels.com/photos/2047905/pexels-photo-2047905.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Navigate a cyberpunk world where AI and humanity collide in unexpected ways.',
      tags: ['Cyberpunk', 'AI', 'Choice-Driven']
    },
    {
      id: 3,
      title: 'Moonlight Manor Mystery',
      author: 'Victoria Sterling',
      genre: 'mystery',
      duration: '3 hours',
      readers: 15600,
      rating: 4.8,
      progress: 0,
      choices: 32,
      image: 'https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Solve an intricate murder mystery in a Victorian mansion full of secrets.',
      tags: ['Victorian', 'Detective', 'Puzzle']
    },
    {
      id: 4,
      title: 'Hearts & Kingdoms',
      author: 'Isabella Rose',
      genre: 'romance',
      duration: '6 hours',
      readers: 21300,
      rating: 4.6,
      progress: 25,
      choices: 56,
      image: 'https://images.pexels.com/photos/1563356/pexels-photo-1563356.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'A royal romance where political intrigue meets matters of the heart.',
      tags: ['Royal', 'Politics', 'Romance']
    },
    {
      id: 5,
      title: 'Starbound Adventures',
      author: 'Captain Nova',
      genre: 'adventure',
      duration: '7 hours',
      readers: 9800,
      rating: 4.9,
      progress: 0,
      choices: 61,
      image: 'https://images.pexels.com/photos/1116302/pexels-photo-1116302.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Explore distant galaxies and make choices that determine the fate of civilizations.',
      tags: ['Space', 'Exploration', 'Epic']
    },
    {
      id: 6,
      title: 'The Last Heist',
      author: 'Jake Storm',
      genre: 'thriller',
      duration: '4 hours',
      readers: 11200,
      rating: 4.5,
      progress: 80,
      choices: 29,
      image: 'https://images.pexels.com/photos/1040424/pexels-photo-1040424.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Plan and execute the perfect heist in this high-stakes interactive thriller.',
      tags: ['Crime', 'Suspense', 'Strategy']
    }
  ];

  const filteredStories = featuredStories.filter(story => {
    const matchesSearch = story.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         story.author.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGenre = selectedGenre === 'all' || story.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  const continueReading = featuredStories.filter(story => story.progress > 0);

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Entertainment Mode
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Immerse yourself in interactive stories where your choices matter. Experience branching narratives 
            with AI-driven characters, voice interactions, and collectible NFTs.
          </p>
        </div>

        {/* Continue Reading Section */}
        {continueReading.length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <Clock className="h-7 w-7 text-purple-600 mr-2" />
              Continue Your Adventures
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {continueReading.map((story) => (
                <div
                  key={story.id}
                  className="group bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
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
                      <p className="text-white text-sm font-medium">{story.progress}% Complete</p>
                    </div>
                  </div>
                  <div className="p-6">
                    <h3 className="font-bold text-lg text-gray-900 mb-2 group-hover:text-purple-600 transition-colors">
                      {story.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-4">by {story.author}</p>
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
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <select
                  value={selectedGenre}
                  onChange={(e) => setSelectedGenre(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Sparkles className="h-7 w-7 text-purple-600 mr-2" />
            Interactive Stories
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredStories.map((story) => (
              <div
                key={story.id}
                className="group bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
              >
                <div className="relative">
                  <img 
                    src={story.image} 
                    alt={story.title}
                    className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                  />
                  <div className="absolute top-4 left-4">
                    <span className="bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium text-gray-900 capitalize">
                      {story.genre}
                    </span>
                  </div>
                  <div className="absolute top-4 right-4 flex space-x-2">
                    <button className="bg-white/90 backdrop-blur-sm p-2 rounded-full hover:bg-white transition-colors">
                      <Heart className="h-4 w-4 text-gray-600" />
                    </button>
                  </div>
                </div>
                
                <div className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-400 fill-current" />
                      <span className="text-sm text-gray-600">{story.rating}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Zap className="h-4 w-4 text-purple-500" />
                      <span className="text-sm text-purple-600 font-medium">{story.choices} choices</span>
                    </div>
                  </div>
                  
                  <h3 className="font-bold text-lg text-gray-900 mb-2 group-hover:text-purple-600 transition-colors">
                    {story.title}
                  </h3>
                  
                  <p className="text-gray-600 text-sm mb-3">by {story.author}</p>
                  
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                    {story.description}
                  </p>
                  
                  <div className="flex flex-wrap gap-1 mb-4">
                    {story.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="bg-purple-100 text-purple-700 px-2 py-1 rounded-full text-xs font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {story.duration}
                      </span>
                      <span className="flex items-center">
                        <Users className="h-4 w-4 mr-1" />
                        {story.readers.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Link
                      to={`/book/${story.id}`}
                      className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 text-white py-2 px-4 rounded-full font-medium text-center hover:from-purple-600 hover:to-pink-700 transition-all transform hover:scale-105"
                    >
                      {story.progress > 0 ? 'Continue' : 'Start Story'}
                    </Link>
                    <button className="border border-purple-200 text-purple-600 py-2 px-4 rounded-full hover:bg-purple-50 transition-colors">
                      Preview
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Features Callout */}
        <div className="bg-gradient-to-br from-purple-600 via-pink-600 to-indigo-700 rounded-2xl p-8 text-white text-center">
          <Sparkles className="h-16 w-16 mx-auto mb-4 text-white" />
          <h2 className="text-2xl font-bold mb-4">AI-Enhanced Entertainment</h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            Experience stories like never before with voice-driven characters, AI-generated scenes, 
            and collectible animated NFTs that unlock as you progress.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Play className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Voice Characters</h3>
              <p className="text-sm opacity-90">AI-powered character voices bring stories to life</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Film className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Dynamic Scenes</h3>
              <p className="text-sm opacity-90">AI generates visual scenes based on your choices</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Star className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Collectible NFTs</h3>
              <p className="text-sm opacity-90">Earn unique animated collectibles</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}