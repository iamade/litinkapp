import { apiClient } from "../lib/api";

export interface Project {
  id: string;
  title: string;
  project_type: "entertainment" | "training" | "advert" | "music_video";
  workflow_mode: "explorer_agentic" | "creator_interactive";
  status: "draft" | "generating" | "review" | "completed" | "published";
  created_at: string;
}

export interface IntentAnalysisResult {
  primary_intent: string;
  confidence: number;
  reasoning: string;
  suggested_mode: string;
  detected_pipeline: string[];
}

export const projectService = {
  createProject: async (data: any) => {
    return await apiClient.post<Project>("/projects/", data);
  },

  getProjects: async () => {
    return await apiClient.get<Project[]>("/projects/");
  },

  getProject: async (id: string) => {
    return await apiClient.get<Project>(`/projects/${id}`);
  },

  analyzeIntent: async (prompt: string, fileName?: string) => {
    return await apiClient.post<IntentAnalysisResult>("/projects/analyze-intent", {
      prompt,
      file_name: fileName,
    });
  },
};
