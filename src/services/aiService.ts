import { apiClient } from "../lib/api";
import { PipelineStatus, RetryResponse } from "../types/pipelinestatus";

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

  getPipelineStatus: async (videoGenId: string): Promise<PipelineStatus> => {
    try {
      const response = await apiClient.get<PipelineStatus>(`/ai/pipeline-status/${videoGenId}`);
      return response;
    } catch (error) {
      console.error("Error getting pipeline status:", error);
      throw error;
    }
  },
  

  retryVideoGeneration: async (
    videoGenId: string, 
    retryFromStep?: string
  ): Promise<RetryResponse> => {
    try {
      const body = retryFromStep ? { retry_from_step: retryFromStep } : {};
      const response = await apiClient.post<RetryResponse>(
        `/ai/retry-generation/${videoGenId}`, 
        body
      );
      return response;
    } catch (error) {
      console.error("Error retrying video generation:", error);
      throw error;
    }
  },


  initializePipeline: async (videoGenId: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>(
        `/ai/initialize-pipeline/${videoGenId}`, 
        {}
      );
      return response;
    } catch (error) {
      console.error("Error initializing pipeline:", error);
      throw error;
    }
  },

  

  

};

