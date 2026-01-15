import { apiClient } from "../lib/api";

export type ProjectStatus = "draft" | "generating" | "review" | "completed" | "published";

export interface Project {
  id: string;
  title: string;
  project_type: "entertainment" | "training" | "advert" | "music_video";
  workflow_mode: "explorer_agentic" | "creator_interactive";
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  input_prompt?: string;
  source_material_url?: string;
  artifacts?: any[];
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

  createProjectFromUpload: async (file: File, projectType: string, inputPrompt?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_type", projectType);
    if (inputPrompt) {
        formData.append("input_prompt", inputPrompt);
    }
    
    // Use apiClient.upload which handles FormData and multipart
    return await apiClient.upload<Project>("/projects/upload", formData);
  },

  getProjects: async () => {
    return await apiClient.get<Project[]>("/projects/");
  },

  getProject: async (id: string) => {
    return await apiClient.get<Project>(`/projects/${id}`);
  },

  generateSceneImage: async (
    projectId: string, 
    sceneNumber: number, 
    data: { 
      scene_description: string; 
      style: string; 
      aspect_ratio: string; 
      custom_prompt?: string;
      script_id?: string;
      character_ids?: string[];
      character_image_urls?: string[];
    }
  ) => {
    return await apiClient.post<any>(
      `/chapters/${projectId}/images/scenes/${sceneNumber}`,
      data
    );
  },

  updateSceneDescription: async (
    chapterId: string,
    scriptId: string,
    sceneNumber: number,
    sceneDescription: string
  ) => {
    return await apiClient.put(
      `/chapters/${chapterId}/scripts/${scriptId}/scenes/${sceneNumber}`,
      { scene_description: sceneDescription }
    );
  },

  reorderScenes: async (
    chapterId: string,
    scriptId: string,
    sceneOrder: number[]
  ) => {
    return await apiClient.patch(
      `/chapters/${chapterId}/scripts/${scriptId}/reorder-scenes`,
      { scene_order: sceneOrder }
    );
  },

  analyzeIntent: async (prompt: string, fileName?: string) => {
    return await apiClient.post<IntentAnalysisResult>("/projects/analyze-intent", {
      prompt,
      file_name: fileName,
    });
  },

  deleteProject: async (id: string) => {
    return await apiClient.delete(`/projects/${id}`);
  },

  updateProject: async (id: string, data: Partial<Project>) => {
    return await apiClient.patch<Project>(`/projects/${id}`, data);
  },
};
