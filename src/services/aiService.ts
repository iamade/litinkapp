import { apiClient } from "../lib/api";

interface AIResponse {
  text: string;
}

export const aiService = {
  generateText: async (prompt: string, context?: string): Promise<string> => {
    const response = await apiClient.post<AIResponse>("/ai/generate-text", {
      prompt,
      context,
    });
    return response.text;
  },

  generateQuiz: async (
    bookId: number,
    numQuestions: number,
    difficulty: string
  ): Promise<string> => {
    const response = await apiClient.post<AIResponse>("/ai/generate-quiz", {
      book_id: bookId,
      num_questions: numQuestions,
      difficulty,
    });
    return response.text;
  },

  analyzeChapterSafety: async (chapterId: string): Promise<any> => {
    try {
      const response = await apiClient.post("/ai/analyze-chapter-safety", {
        chapter_id: chapterId,
      });
      return response.data;
    } catch (error) {
      console.error("Error analyzing chapter safety:", error);
      throw error;
    }
  },
};
