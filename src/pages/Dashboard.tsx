import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  BookOpen, 
  Brain, 
  Sparkles, 
  Upload, 
  Award, 
  TrendingUp,
  Clock,
  Star
} from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">Please sign in to access your dashboard</p>
          <Link
            to="/auth"
            className="bg-purple-600 text-white px-6 py-3 rounded-full font-semibold hover:bg-purple-700 transition-colors"
          >
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  const recentBooks = [
    {
      id: 1,
      title: 'Introduction to AI',
      author: 'Dr. Sarah Chen',
      progress: 75,
      type: 'learning',
      lastRead: '2 hours ago'
    },
    {
      id: 2,
      title: 'The Mystery of Echo Valley',
      author: 'Marcus Johnson',
      progress: 45,
      type: 'entertainment',
      lastRead: '1 day ago'
    },
    {
      id: 3,
      title: 'Modern Web Development',
      author: 'Alex Rivera',
      progress: 90,
      type: 'learning',
      lastRead: '3 hours ago'
    }
  ];

  const achievements = [
    { title: 'First Steps', description: 'Complete your first lesson', icon: Star, earned: true },
    { title: 'Bookworm', description: 'Read 5 books this month', icon: BookOpen, earned: true },
    { title: 'AI Explorer', description: 'Try all AI features', icon: Brain, earned: false },
    { title: 'Story Master', description: 'Complete 3 interactive stories', icon: Sparkles, earned: false }
  ];

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome back, {user.displayName}!
          </h1>
          <p className="text-gray-600">
            {user.role === 'author' 
              ? 'Ready to create amazing interactive content?' 
              : 'Continue your learning and exploration journey.'
            }
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Link
            to="/learn"
            className="group bg-gradient-to-br from-green-50 to-blue-50 p-6 rounded-2xl border border-green-100 hover:border-green-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Brain className="h-12 w-12 text-green-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Learning Mode</h3>
            <p className="text-sm text-gray-600">Interactive tutorials & quizzes</p>
          </Link>

          <Link
            to="/explore"
            className="group bg-gradient-to-br from-purple-50 to-pink-50 p-6 rounded-2xl border border-purple-100 hover:border-purple-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Sparkles className="h-12 w-12 text-purple-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Entertainment</h3>
            <p className="text-sm text-gray-600">Interactive stories & adventures</p>
          </Link>

          {user.role === 'author' && (
            <Link
              to="/upload"
              className="group bg-gradient-to-br from-yellow-50 to-orange-50 p-6 rounded-2xl border border-yellow-100 hover:border-yellow-200 transition-all transform hover:scale-105 hover:shadow-lg"
            >
              <Upload className="h-12 w-12 text-orange-600 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-gray-900 mb-2">Upload Book</h3>
              <p className="text-sm text-gray-600">Create AI-powered content</p>
            </Link>
          )}

          <Link
            to="/profile"
            className="group bg-gradient-to-br from-gray-50 to-slate-50 p-6 rounded-2xl border border-gray-100 hover:border-gray-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Award className="h-12 w-12 text-gray-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">My Profile</h3>
            <p className="text-sm text-gray-600">Progress & achievements</p>
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Activity */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 flex items-center">
                  <Clock className="h-6 w-6 text-purple-600 mr-2" />
                  Continue Reading
                </h2>
                <Link 
                  to="/learn"
                  className="text-purple-600 hover:text-purple-700 text-sm font-medium"
                >
                  View All
                </Link>
              </div>

              <div className="space-y-4">
                {recentBooks.map((book) => (
                  <div
                    key={book.id}
                    className="flex items-center space-x-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors group cursor-pointer"
                  >
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      book.type === 'learning' 
                        ? 'bg-gradient-to-br from-green-500 to-blue-600' 
                        : 'bg-gradient-to-br from-purple-500 to-pink-600'
                    }`}>
                      {book.type === 'learning' ? (
                        <Brain className="h-6 w-6 text-white" />
                      ) : (
                        <Sparkles className="h-6 w-6 text-white" />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">
                        {book.title}
                      </h3>
                      <p className="text-sm text-gray-600">by {book.author}</p>
                      <p className="text-xs text-gray-500">{book.lastRead}</p>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900 mb-1">
                        {book.progress}%
                      </div>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            book.type === 'learning' 
                              ? 'bg-gradient-to-r from-green-500 to-blue-600' 
                              : 'bg-gradient-to-r from-purple-500 to-pink-600'
                          }`}
                          style={{ width: `${book.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Achievements */}
          <div className="space-y-6">
            {/* Stats */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <TrendingUp className="h-6 w-6 text-purple-600 mr-2" />
                Your Stats
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Books Read</span>
                  <span className="font-bold text-2xl text-purple-600">12</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Hours Spent</span>
                  <span className="font-bold text-2xl text-blue-600">45</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Badges Earned</span>
                  <span className="font-bold text-2xl text-green-600">8</span>
                </div>
              </div>
            </div>

            {/* Achievements */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <Award className="h-6 w-6 text-purple-600 mr-2" />
                Achievements
              </h2>
              <div className="space-y-3">
                {achievements.map((achievement, index) => (
                  <div 
                    key={index}
                    className={`flex items-center space-x-3 p-3 rounded-lg ${
                      achievement.earned 
                        ? 'bg-green-50 border border-green-200' 
                        : 'bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      achievement.earned 
                        ? 'bg-green-500' 
                        : 'bg-gray-400'
                    }`}>
                      <achievement.icon className="h-4 w-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className={`font-medium ${
                        achievement.earned ? 'text-green-900' : 'text-gray-900'
                      }`}>
                        {achievement.title}
                      </h4>
                      <p className={`text-xs ${
                        achievement.earned ? 'text-green-600' : 'text-gray-500'
                      }`}>
                        {achievement.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}