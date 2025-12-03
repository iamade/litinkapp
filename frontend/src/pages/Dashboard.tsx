import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, hasRole } from "../contexts/AuthContext";
import { userService } from "../services/userService";
import { subscriptionService, SubscriptionUsageStats } from "../services/subscriptionService";
import UsageIndicator from "../components/Subscription/UsageIndicator";
import UpgradeBanner from "../components/Dashboard/UpgradeBanner";
import {
  Brain,
  Sparkles,
  Upload,
  Award,
  TrendingUp,
  Clock,
  Wand2,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiClient } from "../lib/api";

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  roles: ("author" | "explorer")[];
  avatar_url?: string;
  bio?: string;
}

interface UserStats {
  books_read: number;
  total_time_hours: number;
  badges_earned: number;
  quizzes_taken: number;
  average_quiz_score: number;
  books_uploaded: number;
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

function DeleteModal({
  open,
  onClose,
  onConfirm,
  bookTitle,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  bookTitle: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-sm w-full">
        <h2 className="text-lg font-bold mb-4 text-gray-900">Delete Book</h2>
        <p className="mb-6 text-gray-700">
          Are you sure you want to delete{" "}
          <span className="font-semibold">{bookTitle}</span>? This action cannot
          be undone.
        </p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [allBooks, setAllBooks] = useState<Book[]>([]);
  const navigate = useNavigate();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [bookToDelete, setBookToDelete] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [retryingBookId, setRetryingBookId] = useState<string | null>(null);
  const [usage, setUsage] = useState<SubscriptionUsageStats | null>(null);

  // Function to fetch all books
  const fetchBooks = async () => {
    const books = await userService.getMyBooks(); // This actually calls /books (all books)
    setAllBooks(books as Book[]);
    return books;
  };

  useEffect(() => {
    if (!user) return;
    userService.getProfile().then((data: UserProfile) => setProfile(data));
    userService.getStats().then((data: UserStats) => setStats(data));
    fetchBooks();
    subscriptionService.getUsageStats().then(setUsage).catch(() => setUsage(null));
  }, [user]);

  // Auto-refresh books every 7 seconds if there are processing or generating books
  useEffect(() => {
    if (!allBooks.length) return;
    const hasProcessingBooks = allBooks.some(
      (book) => book.status === "PROCESSING" || book.status === "GENERATING"
    );
    if (!hasProcessingBooks) return;
    const interval = setInterval(fetchBooks, 7000);
    return () => clearInterval(interval);
  }, [allBooks]);

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

  const handleChapterRetry = async (bookId: string) => {
    setRetryingBookId(bookId);
    try {
      const bookWithChapters = await apiClient.post(
        `/books/${bookId}/regenerate-chapters`,
        {}
      );
      // Navigate to the upload page, passing the book data to resume at step 4
      navigate("/upload", { state: { resumeBook: bookWithChapters } });
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "Failed to retry chapter generation.");
    } finally {
      setRetryingBookId(null);
    }
  };

  const handleDelete = async () => {
    if (!bookToDelete) return;
    try {
      await userService.deleteBook(bookToDelete.id);
      await fetchBooks();
      toast.success("Book deleted successfully!");
    } catch {
      toast.error("Failed to delete book.");
    } finally {
      setDeleteModalOpen(false);
      setBookToDelete(null);
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome back, {profile?.display_name || user.display_name}!
          </h1>
          <p className="text-gray-600">
            {hasRole(user, "author") && hasRole(user, "explorer")
              ? "Create, explore, and learn amazing content!"
              : hasRole(user, "author")
              ? "Ready to create amazing interactive content?"
              : "Continue your learning and exploration journey."}
          </p>
        </div>

        {/* Upgrade Banner - Show only for users without creator role */}
        {!hasRole(user, "author") && (
          <div className="mb-8">
            <UpgradeBanner />
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {/* Show Learning Mode only for explorer users */}
          {hasRole(user, "explorer") && (
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
          )}

          {/* Show Entertainment only for explorer users */}
          {hasRole(user, "explorer") && (
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
          )}

          {/* Show Creator Mode only for author users */}
          {hasRole(user, "author") && (
            <Link
              to="/creator"
              className="group bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-2xl border border-blue-100 hover:border-blue-200 transition-all transform hover:scale-105 hover:shadow-lg"
            >
              <Wand2 className="h-12 w-12 text-blue-600 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-gray-900 mb-2">Creator Mode</h3>
              <p className="text-sm text-gray-600">
                Generate books, scripts & videos
              </p>
            </Link>
          )}

          <Link
            to="/upload"
            className="group bg-gradient-to-br from-yellow-50 to-orange-50 p-6 rounded-2xl border border-yellow-100 hover:border-yellow-200 transition-all transform hover:scale-105 hover:shadow-lg"
          >
            <Upload className="h-12 w-12 text-orange-600 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-gray-900 mb-2">Upload Book</h3>
            <p className="text-sm text-gray-600">
              {hasRole(user, "author")
                ? "Upload and claim authorship"
                : "Upload a book to the platform"}
            </p>
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
                {allBooks.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">
                    You have no books uploaded.
                  </div>
                ) : (
                  allBooks.map((book) => (
                    <div
                      key={book.id}
                      className="flex items-center space-x-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors group"
                    >
                      <div
                        className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                          book.book_type === "entertainment"
                            ? "bg-gradient-to-br from-purple-500 to-pink-600"
                            : book.book_type === "learning"
                            ? "bg-gradient-to-br from-green-500 to-blue-600"
                            : "bg-gradient-to-br from-gray-400 to-gray-600"
                        }`}
                      >
                        {book.book_type === "entertainment" ? (
                          <Sparkles className="h-6 w-6 text-white" />
                        ) : book.book_type === "learning" ? (
                          <Brain className="h-6 w-6 text-white" />
                        ) : (
                          <span className="text-xs text-white">?</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">
                          {book.title}
                        </h3>
                        <p className="text-sm text-gray-600">
                          by {book.author_name}
                        </p>
                        <div className="text-sm text-gray-500 mt-1">
                          Status:{" "}
                          <span
                            className={`font-semibold ${
                              book.status === "READY"
                                ? "text-green-600"
                                : book.status === "FAILED"
                                ? "text-red-600"
                                : "text-yellow-600"
                            }`}
                          >
                            {book.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-col space-y-2 items-end">
                        <button
                          className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-medium hover:bg-blue-200 transition-colors disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                          onClick={() =>
                            book.status === "READY" &&
                            navigate(`/book/${book.id}`)
                          }
                          disabled={book.status !== "READY"}
                        >
                          View
                        </button>
                        {book.status === "GENERATING" && (
                          <button
                            className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-lg text-xs font-medium hover:bg-yellow-200 transition-colors"
                            onClick={() => handleChapterRetry(book.id)}
                            disabled={retryingBookId === book.id}
                          >
                            {retryingBookId === book.id
                              ? "Retrying..."
                              : "Retry"}
                          </button>
                        )}
                        <button
                          className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-medium hover:bg-red-200 transition-colors"
                          onClick={() => {
                            setBookToDelete({ id: book.id, title: book.title });
                            setDeleteModalOpen(true);
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Achievements */}
          <div className="space-y-6">
            {/* Usage Indicator */}
            {usage && (
              <UsageIndicator usage={usage} />
            )}

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
                  <span className="text-gray-600">Books Uploaded</span>
                  <span className="font-bold text-2xl text-orange-600">
                    {stats?.books_uploaded ?? "--"}
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
      </div>
      <DeleteModal
        open={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setBookToDelete(null);
        }}
        onConfirm={handleDelete}
        bookTitle={bookToDelete?.title || ""}
      />
    </div>
  );
}
