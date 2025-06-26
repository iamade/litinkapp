import { apiClient } from "../lib/api";

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

export const userService = {
  getProfile: async (): Promise<UserProfile> => {
    return apiClient.get<UserProfile>("/users/me");
  },
  updateProfile: async (data: Partial<UserProfile>) => {
    return apiClient.put<UserProfile>("/users/me", data);
  },
  getStats: async (): Promise<UserStats> => {
    return apiClient.get<UserStats>("/users/me/stats");
  },
  getMyBooks: async () => {
    return apiClient.get("/books");
  },
  retryBookProcessing: async (bookId: string) => {
    return apiClient.post(`/books/${bookId}/retry`, {});
  },
  deleteBook: async (bookId: string) => {
    return apiClient.delete(`/books/${bookId}`);
  },
  getBook: async (bookId: string) => {
    return apiClient.get(`/books/${bookId}`);
  },
  getChapters: async (bookId: string) => {
    return apiClient.get(`/books/${bookId}/chapters`);
  },
};

export async function deleteBook(bookId: string) {
  const response = await fetch(`/api/v1/books/${bookId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to delete book");
  }
  return await response.json();
}
