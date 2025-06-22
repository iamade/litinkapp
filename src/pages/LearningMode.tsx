import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  BookOpen, 
  Brain, 
  Search, 
  Filter, 
  Clock, 
  Award,
  Star,
  Users,
  Play,
  CheckCircle
} from 'lucide-react';

export default function LearningMode() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const categories = [
    { id: 'all', label: 'All Categories' },
    { id: 'programming', label: 'Programming' },
    { id: 'science', label: 'Science' },
    { id: 'business', label: 'Business' },
    { id: 'design', label: 'Design' },
    { id: 'language', label: 'Languages' }
  ];

  const featuredBooks = [
    {
      id: 1,
      title: 'Introduction to Machine Learning',
      author: 'Dr. Sarah Chen',
      category: 'programming',
      level: 'Beginner',
      duration: '6 hours',
      students: 1250,
      rating: 4.8,
      progress: 0,
      image: 'https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Learn the fundamentals of machine learning with interactive tutorials and real-world examples.'
    },
    {
      id: 2,
      title: 'Modern Web Development',
      author: 'Alex Rivera',
      category: 'programming',
      level: 'Intermediate',
      duration: '8 hours',
      students: 890,
      rating: 4.9,
      progress: 45,
      image: 'https://images.pexels.com/photos/11035380/pexels-photo-11035380.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Master modern web development with React, Node.js, and cutting-edge tools.'
    },
    {
      id: 3,
      title: 'Digital Marketing Mastery',
      author: 'Jessica Wong',
      category: 'business',
      level: 'Beginner',
      duration: '5 hours',
      students: 2100,
      rating: 4.7,
      progress: 0,
      image: 'https://images.pexels.com/photos/265087/pexels-photo-265087.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Comprehensive guide to digital marketing strategies and implementation.'
    },
    {
      id: 4,
      title: 'Data Science Fundamentals',
      author: 'Dr. Michael Torres',
      category: 'science',
      level: 'Intermediate',
      duration: '10 hours',
      students: 756,
      rating: 4.9,
      progress: 75,
      image: 'https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Explore data science concepts with hands-on projects and AI-powered insights.'
    },
    {
      id: 5,
      title: 'UX Design Principles',
      author: 'Emma Thompson',
      category: 'design',
      level: 'Beginner',
      duration: '4 hours',
      students: 1450,
      rating: 4.8,
      progress: 0,
      image: 'https://images.pexels.com/photos/196644/pexels-photo-196644.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Learn essential UX design principles with interactive case studies.'
    },
    {
      id: 6,
      title: 'Spanish for Beginners',
      author: 'Carlos Martinez',
      category: 'language',
      level: 'Beginner',
      duration: '12 hours',
      students: 3200,
      rating: 4.6,
      progress: 20,
      image: 'https://images.pexels.com/photos/256417/pexels-photo-256417.jpeg?auto=compress&cs=tinysrgb&w=400',
      description: 'Interactive Spanish learning with AI-powered pronunciation and conversation practice.'
    }
  ];

  const filteredBooks = featuredBooks.filter(book => {
    const matchesSearch = book.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         book.author.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || book.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const continueLearning = featuredBooks.filter(book => book.progress > 0);

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Learning Mode
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Transform any book into interactive tutorials, personalized lessons, and smart quizzes powered by AI. 
            Learn at your own pace and earn verified credentials.
          </p>
        </div>

        {/* Continue Learning Section */}
        {continueLearning.length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <Clock className="h-7 w-7 text-purple-600 mr-2" />
              Continue Learning
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {continueLearning.map((book) => (
                <div
                  key={book.id}
                  className="group bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <div className="relative">
                    <img 
                      src={book.image} 
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
                      <p className="text-white text-sm font-medium">{book.progress}% Complete</p>
                    </div>
                  </div>
                  <div className="p-6">
                    <h3 className="font-bold text-lg text-gray-900 mb-2 group-hover:text-purple-600 transition-colors">
                      {book.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-4">by {book.author}</p>
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
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <BookOpen className="h-7 w-7 text-purple-600 mr-2" />
            Explore Learning Materials
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredBooks.map((book) => (
              <div
                key={book.id}
                className="group bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-all transform hover:scale-105"
              >
                <div className="relative">
                  <img 
                    src={book.image} 
                    alt={book.title}
                    className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                  />
                  <div className="absolute top-4 left-4">
                    <span className="bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium text-gray-900">
                      {book.level}
                    </span>
                  </div>
                  {book.progress > 0 && (
                    <div className="absolute top-4 right-4">
                      <div className="bg-green-500 p-2 rounded-full">
                        <CheckCircle className="h-4 w-4 text-white" />
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-purple-600 font-medium capitalize">
                      {book.category}
                    </span>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-400 fill-current" />
                      <span className="text-sm text-gray-600">{book.rating}</span>
                    </div>
                  </div>
                  
                  <h3 className="font-bold text-lg text-gray-900 mb-2 group-hover:text-purple-600 transition-colors">
                    {book.title}
                  </h3>
                  
                  <p className="text-gray-600 text-sm mb-3">by {book.author}</p>
                  
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                    {book.description}
                  </p>
                  
                  <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {book.duration}
                      </span>
                      <span className="flex items-center">
                        <Users className="h-4 w-4 mr-1" />
                        {book.students.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Link
                      to={`/book/${book.id}`}
                      className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-full font-medium text-center hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
                    >
                      {book.progress > 0 ? 'Continue' : 'Start Learning'}
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
        <div className="bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 rounded-2xl p-8 text-white text-center">
          <Brain className="h-16 w-16 mx-auto mb-4 text-white" />
          <h2 className="text-2xl font-bold mb-4">AI-Powered Learning Features</h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            Experience personalized tutorials, adaptive quizzes, voice interactions, and earn blockchain-verified badges as you progress.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Brain className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Smart Tutorials</h3>
              <p className="text-sm opacity-90">AI adapts content to your learning style</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Award className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Verified Badges</h3>
              <p className="text-sm opacity-90">Blockchain-certified achievements</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <Play className="h-8 w-8 mx-auto mb-2" />
              <h3 className="font-semibold mb-2">Voice Learning</h3>
              <p className="text-sm opacity-90">Interactive voice-powered lessons</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}