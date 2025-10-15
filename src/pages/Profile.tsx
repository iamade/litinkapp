import React from "react";
import { useAuth, hasRole } from "../contexts/AuthContext";
import RoleManagement from "../components/Profile/RoleManagement";
import {
  User,
  Award,
  BookOpen,
  Clock,
  Star,
  Trophy,
  Target,
  Calendar,
  Badge,
  Zap,
  Upload,
} from "lucide-react";

export default function Profile() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">
            Please sign in to view your profile
          </p>
        </div>
      </div>
    );
  }

  const stats = {
    booksRead: 12,
    booksUploaded: 3,
    hoursSpent: 45,
    badgesEarned: 8,
    streakDays: 15,
  };

  const badges = [
    {
      id: 1,
      name: "First Steps",
      description: "Completed your first lesson",
      earned: true,
      rarity: "common",
      earnedDate: "2024-01-15",
    },
    {
      id: 2,
      name: "Bookworm",
      description: "Read 10 books",
      earned: true,
      rarity: "uncommon",
      earnedDate: "2024-01-18",
    },
    {
      id: 3,
      name: "AI Explorer",
      description: "Used all AI features",
      earned: true,
      rarity: "rare",
      earnedDate: "2024-01-20",
    },
    {
      id: 4,
      name: "Speed Reader",
      description: "Complete 5 books in one week",
      earned: false,
      rarity: "epic",
      earnedDate: null,
    },
    {
      id: 5,
      name: "Story Master",
      description: "Complete 10 interactive stories",
      earned: true,
      rarity: "rare",
      earnedDate: "2024-01-22",
    },
    {
      id: 6,
      name: "Knowledge Seeker",
      description: "Earn perfect scores on 20 quizzes",
      earned: false,
      rarity: "legendary",
      earnedDate: null,
    },
  ];

  const recentActivity = [
    {
      id: 1,
      type: "completed",
      title: "Introduction to Machine Learning",
      description: "Completed lesson: Neural Networks Basics",
      timestamp: "2 hours ago",
      icon: BookOpen,
    },
    {
      id: 2,
      type: "badge",
      title: "Story Master",
      description: "Earned badge for completing interactive stories",
      timestamp: "1 day ago",
      icon: Award,
    },
    {
      id: 3,
      type: "streak",
      title: "15-Day Streak!",
      description: "Maintained daily learning streak",
      timestamp: "2 days ago",
      icon: Zap,
    },
    {
      id: 4,
      type: "completed",
      title: "The Crystal Chronicles",
      description: "Finished interactive story with ending #3",
      timestamp: "3 days ago",
      icon: Star,
    },
  ];

  const getRarityColor = (rarity: string) => {
    switch (rarity) {
      case "common":
        return "bg-gray-100 text-gray-800 border-gray-300";
      case "uncommon":
        return "bg-green-100 text-green-800 border-green-300";
      case "rare":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "epic":
        return "bg-purple-100 text-purple-800 border-purple-300";
      case "legendary":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Profile Header */}
        <div className="bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 rounded-2xl p-8 text-white mb-8">
          <div className="flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-6">
            <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center">
              <User className="h-12 w-12 text-white" />
            </div>
            <div className="text-center md:text-left flex-1">
              <h1 className="text-3xl font-bold mb-2">{user.display_name}</h1>
              <p className="text-white/90 mb-4">{user.email}</p>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                {hasRole(user, "explorer") && (
                  <span className="bg-green-500/30 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium border border-green-300/50">
                    Explorer
                  </span>
                )}
                {hasRole(user, "author") && (
                  <span className="bg-blue-500/30 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium border border-blue-300/50">
                    Content Creator
                  </span>
                )}
                <span className="bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium flex items-center">
                  <Zap className="h-4 w-4 mr-1" />
                  {stats.streakDays} day streak
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Stats and Activity */}
          <div className="lg:col-span-2 space-y-8">
            {/* Role Management Section */}
            <RoleManagement />
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 text-center">
                <BookOpen className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{stats.booksRead}</p>
                <p className="text-sm text-gray-600">Books Read</p>
              </div>
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 text-center">
                <Upload className="h-8 w-8 text-orange-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{stats.booksUploaded}</p>
                <p className="text-sm text-gray-600">Books Uploaded</p>
              </div>
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 text-center">
                <Clock className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{stats.hoursSpent}</p>
                <p className="text-sm text-gray-600">Hours Spent</p>
              </div>
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 text-center">
                <Award className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{stats.badgesEarned}</p>
                <p className="text-sm text-gray-600">Badges</p>
              </div>
            </div>
            
            {/* Additional Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 text-center">
                <Zap className="h-8 w-8 text-orange-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{stats.streakDays}</p>
                <p className="text-sm text-gray-600">Day Streak</p>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
                <Calendar className="h-6 w-6 text-purple-600 mr-2" />
                Recent Activity
              </h2>
              <div className="space-y-4">
                {recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start space-x-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex-shrink-0">
                      <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                        <activity.icon className="h-5 w-5 text-purple-600" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900">
                        {activity.title}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {activity.description}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {activity.timestamp}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Badges */}
          <div className="space-y-8">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
                <Trophy className="h-6 w-6 text-purple-600 mr-2" />
                Achievement Badges
              </h2>
              <div className="space-y-4">
                {badges.map((badge) => (
                  <div
                    key={badge.id}
                    className={`relative p-4 rounded-xl border-2 transition-all ${
                      badge.earned
                        ? getRarityColor(badge.rarity)
                        : "bg-gray-50 text-gray-500 border-gray-200 opacity-60"
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div
                        className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          badge.earned ? "bg-white/50" : "bg-gray-300"
                        }`}
                      >
                        <Badge
                          className={`h-6 w-6 ${
                            badge.earned ? "text-current" : "text-gray-500"
                          }`}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3
                          className={`font-semibold ${
                            badge.earned ? "text-current" : "text-gray-500"
                          }`}
                        >
                          {badge.name}
                        </h3>
                        <p
                          className={`text-sm ${
                            badge.earned
                              ? "text-current opacity-80"
                              : "text-gray-500"
                          }`}
                        >
                          {badge.description}
                        </p>
                        {badge.earned && badge.earnedDate && (
                          <p className="text-xs mt-1 opacity-70">
                            Earned on {badge.earnedDate}
                          </p>
                        )}
                      </div>
                    </div>
                    {badge.earned && (
                      <div className="absolute top-2 right-2">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Progress Goals */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
                <Target className="h-6 w-6 text-purple-600 mr-2" />
                Progress Goals
              </h2>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-gray-900">
                      Weekly Reading Goal
                    </span>
                    <span className="text-gray-600">3/5 books</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-green-500 to-blue-600 h-2 rounded-full"
                      style={{ width: "60%" }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-gray-900">
                      Badge Collection
                    </span>
                    <span className="text-gray-600">8/12 earned</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-pink-600 h-2 rounded-full"
                      style={{ width: "67%" }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-gray-900">
                      Learning Streak
                    </span>
                    <span className="text-gray-600">15/30 days</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-orange-500 to-yellow-600 h-2 rounded-full"
                      style={{ width: "50%" }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
