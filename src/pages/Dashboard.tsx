import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { userService } from "../services/userService";
import {
  Brain,
  Sparkles,
  Upload,
  Award,
  TrendingUp,
  Clock,
} from "lucide-react";

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: "author" | "explorer";
  avatar_url?: string;
  bio?: string;
}

interface UserStats {
  books_read: number;
  total_time_hours: number;
  badges_earned: number;
  quizzes_taken: number;
  average_quiz_score: number;
}

interface Book {
  id: string;
  title: string;
  author_name: string;
  book_type: string;
  difficulty: string;
  cover_image_path?: string;
  status: "PROCESSING" | "GENERATING" | "READY" | "FAILED";
  progress: number;
  total_steps: number;
  progress_message?: string;
  error_message?: string;
}

const BookCard = ({
  book,
  onRetry,
}: {
  book: Book;
  onRetry: (bookId: string) => Promise<void>;
}) => {
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await onRetry(book.id);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className="border rounded-xl p-4 flex flex-col hover:shadow-lg transition-all transform hover:scale-105">
      {book.cover_image_path && (
        <img
          src={
            book.cover_image_path.startsWith("/")
              ? book.cover_image_path
              : `/uploads/${book.cover_image_path}`
          }
          alt={book.title}
          className="h-40 w-full object-cover rounded mb-2"
        />
      )}
      <div className="font-bold text-lg mb-1">{book.title}</div>
      <div className="text-gray-600 text-sm mb-1">By {book.author_name}</div>
      <div className="text-xs text-purple-600 mb-2">{book.book_type}</div>

      {/* Progress and Status Section */}
      <div className="mt-auto">
        <div className="flex justify-between items-center mb-2">
          <div className="text-gray-500 text-xs">{book.difficulty}</div>
          {book.status === "PROCESSING" && (
            <div className="flex items-center text-yellow-600">
              <div className="animate-spin mr-2 h-4 w-4 border-2 border-yellow-600 rounded-full border-t-transparent"></div>
              <span className="text-xs">Processing...</span>
            </div>
          )}
          {book.status === "GENERATING" && (
            <div className="flex items-center text-blue-600">
              <div className="animate-spin mr-2 h-4 w-4 border-2 border-blue-600 rounded-full border-t-transparent"></div>
              <span className="text-xs">Generating...</span>
            </div>
          )}
          {book.status === "READY" && (
            <div className="flex items-center text-green-600">
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-xs">Ready</span>
            </div>
          )}
          {book.status === "FAILED" && (
            <div className="flex items-center text-red-600">
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span className="text-xs">Failed</span>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        {(book.status === "PROCESSING" || book.status === "GENERATING") && (
          <div className="w-full bg-gray-200 rounded-full h-1.5 mb-2">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${(book.progress / book.total_steps) * 100}%` }}
            ></div>
          </div>
        )}

        {/* Progress Message */}
        {book.progress_message && (
          <div className="text-xs text-gray-600 mb-2">
            {book.progress_message}
          </div>
        )}

        {/* Error Message and Retry Button */}
        {book.status === "FAILED" && (
          <div className="mt-2">
            {book.error_message && (
              <div className="text-xs text-red-600 mb-2">
                {book.error_message}
              </div>
            )}
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="w-full px-3 py-1 bg-red-100 text-red-600 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors disabled:opacity-50"
            >
              {isRetrying ? "Retrying..." : "Retry Processing"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default function Dashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({
    display_name: "",
    avatar_url: "",
    bio: "",
  });
  const [saving, setSaving] = useState(false);
  const [myBooks, setMyBooks] = useState<Book[]>([]);

  // Function to fetch books
  const fetchBooks = async () => {
    const books = await userService.getMyBooks();
    setMyBooks(books as Book[]);
    return books;
  };

  useEffect(() => {
    if (!user) return;
    userService.getProfile().then((data: UserProfile) => setProfile(data));
    userService.getStats().then((data: UserStats) => setStats(data));
    fetchBooks();
  }, [user]);

  // Auto-refresh books every 5 seconds if there are processing or generating books
  useEffect(() => {
    if (!myBooks.length) return;

    const hasProcessingBooks = myBooks.some(
      (book) => book.status === "PROCESSING" || book.status === "GENERATING"
    );

    if (!hasProcessingBooks) return;

    const interval = setInterval(fetchBooks, 5000);
    return () => clearInterval(interval);
  }, [myBooks]);

  useEffect(() => {
    if (profile) {
      setForm({
        display_name: profile.display_name || "",
        avatar_url: profile.avatar_url || "",
        bio: profile.bio || "",
      });
    }
  }, [profile]);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">
            Please sign in to access your dashboard
          </p>
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

  const handleEdit = () => setEditMode(true);
  const handleCancel = () => setEditMode(false);
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };
  const handleSave = async () => {
    setSaving(true);
    await userService.updateProfile(form);
    setEditMode(false);
    setSaving(false);
    const updated = (await userService.getProfile()) as UserProfile;
    setProfile(updated);
  };

  const handleRetry = async (bookId: string) => {
    try {
      await userService.retryBookProcessing(bookId);
      await fetchBooks();
    } catch (error) {
      console.error("Failed to retry book processing:", error);
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome back, {profile?.display_name || user.display_name}!
            </h1>
            <p className="text-gray-600">
              {user.role === "author"
                ? "Ready to create amazing interactive content?"
                : "Continue your learning and exploration journey."}
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex space-x-2">
            <button
              onClick={handleEdit}
              className="px-4 py-2 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 transition-all"
            >
              Edit Profile
            </button>
          </div>
        </div>
        {editMode && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-8 max-w-xl mx-auto">
            <h2 className="text-xl font-bold mb-4">Edit Profile</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  name="display_name"
                  value={form.display_name}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-xl px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Avatar URL
                </label>
                <input
                  type="text"
                  name="avatar_url"
                  value={form.avatar_url}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-xl px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Bio
                </label>
                <textarea
                  name="bio"
                  value={form.bio}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  rows={3}
                />
              </div>
              <div className="flex space-x-3 mt-4">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition-all disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Link
            to="/learn"
            className="group bg-gradient-to-br from-green-50 to-blue-50 p-6 rounded-2xl border border-green-100 hover:border-green-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Brain className="h-12 w-12 text-green-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Learning Mode</h3>
            <p className="text-sm text-gray-600">
              Interactive tutorials & quizzes
            </p>
          </Link>

          <Link
            to="/explore"
            className="group bg-gradient-to-br from-purple-50 to-pink-50 p-6 rounded-2xl border border-purple-100 hover:border-purple-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Sparkles className="h-12 w-12 text-purple-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Entertainment</h3>
            <p className="text-sm text-gray-600">
              Interactive stories & adventures
            </p>
          </Link>

          <Link
            to="/upload"
            className="group bg-gradient-to-br from-yellow-50 to-orange-50 p-6 rounded-2xl border border-yellow-100 hover:border-yellow-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Upload className="h-12 w-12 text-orange-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Upload Book</h3>
            <p className="text-sm text-gray-600">
              {user.role === "author"
                ? "Create AI-powered content as the book owner"
                : "Upload a book (ownership will not be assigned to you)"}
            </p>
          </Link>

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
                  Start Learning
                </h2>
                <Link
                  to="/learn"
                  className="text-purple-600 hover:text-purple-700 text-sm font-medium"
                >
                  View All
                </Link>
              </div>

              <div className="space-y-4">
                {myBooks.map((book) => (
                  <div
                    key={book.id}
                    className="flex items-center space-x-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors group cursor-pointer"
                  >
                    <div
                      className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        book.cover_image_path?.startsWith("/")
                          ? "bg-gradient-to-br from-green-500 to-blue-600"
                          : "bg-gradient-to-br from-purple-500 to-pink-600"
                      }`}
                    >
                      {book.cover_image_path?.startsWith("/") ? (
                        <Brain className="h-6 w-6 text-white" />
                      ) : (
                        <Sparkles className="h-6 w-6 text-white" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">
                        {book.title}
                      </h3>
                      <p className="text-sm text-gray-600">
                        by {book.author_name}
                      </p>
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
                  <span className="font-bold text-2xl text-purple-600">
                    {stats?.books_read ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Hours Spent</span>
                  <span className="font-bold text-2xl text-blue-600">
                    {stats?.total_time_hours ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Badges Earned</span>
                  <span className="font-bold text-2xl text-green-600">
                    {stats?.badges_earned ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Quizzes Taken</span>
                  <span className="font-bold text-2xl text-yellow-600">
                    {stats?.quizzes_taken ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Avg. Quiz Score</span>
                  <span className="font-bold text-2xl text-pink-600">
                    {stats?.average_quiz_score
                      ? stats.average_quiz_score.toFixed(1)
                      : "--"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Uploaded Books List */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Your Uploaded Books</h2>
          {myBooks.length === 0 ? (
            <div className="text-gray-500">No books uploaded yet.</div>
          ) : (
            <div className="space-y-8">
              {Object.entries(
                myBooks.reduce((acc, book) => {
                  const type = book.book_type || "Other";
                  return {
                    ...acc,
                    [type]: [...(acc[type] || []), book],
                  };
                }, {} as Record<string, Book[]>)
              ).map(([bookType, books]) => (
                <div key={bookType}>
                  <h3 className="text-lg font-semibold mb-4 text-purple-600">
                    {bookType}
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {books.map((book) => (
                      <BookCard
                        key={book.id}
                        book={book}
                        onRetry={handleRetry}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
