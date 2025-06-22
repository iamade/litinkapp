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
};
