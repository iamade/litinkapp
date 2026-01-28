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
  content_terminology?: string;  // Film, Episode, Part, Chapter, or custom
  pipeline_steps?: string[];
  current_step?: string;
}

export interface IntentAnalysisResult {
  primary_intent: string;
  confidence: number;
  reasoning: string;
  suggested_mode: string;
  detected_pipeline: string[];
}

export interface StoryboardConfig {
  key_scene_images: Record<string, string>;  // scene_number (str) -> image_id
  deselected_images: string[];               // image IDs that are excluded (opt-OUT)
  image_order: Record<string, string[]>;     // scene_number (str) -> ordered list of image_ids
}

export const projectService = {
  createProject: async (data: any) => {
    return await apiClient.post<Project>("/projects/", data);
  },

  createProjectFromUpload: async (
    files: File[], 
    projectType: string, 
    inputPrompt?: string,
    consultationConfig?: {
      content_terminology?: string;
      universe_name?: string;
      content_type?: string;
      consultation_data?: {
        conversation: Array<{ role: string; content: string }>;
        agreements: {
          universe_name?: string;
          phases?: any[];
          terminology?: string;
          content_type?: string;
        };
      };
    }
  ) => {
    const formData = new FormData();
    // Append each file with the same key 'files' - backend will receive as List[UploadFile]
    files.forEach(file => {
      formData.append("files", file);
    });
    formData.append("project_type", projectType);
    if (inputPrompt) {
        formData.append("input_prompt", inputPrompt);
    }
    // Add consultation config fields if provided
    if (consultationConfig?.content_terminology) {
      formData.append("content_terminology", consultationConfig.content_terminology);
    }
    if (consultationConfig?.universe_name) {
      formData.append("universe_name", consultationConfig.universe_name);
    }
    if (consultationConfig?.content_type) {
      formData.append("content_type", consultationConfig.content_type);
    }
    // Pass consultation data as JSON string for backend to parse
    if (consultationConfig?.consultation_data) {
      formData.append("consultation_data", JSON.stringify(consultationConfig.consultation_data));
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

  getStoryboardConfig: async (
    chapterId: string,
    scriptId: string
  ): Promise<StoryboardConfig> => {
    return await apiClient.get<StoryboardConfig>(
      `/chapters/${chapterId}/scripts/${scriptId}/storyboard-config`
    );
  },

  saveStoryboardConfig: async (
    chapterId: string,
    scriptId: string,
    config: StoryboardConfig
  ): Promise<StoryboardConfig> => {
    return await apiClient.patch<StoryboardConfig>(
      `/chapters/${chapterId}/scripts/${scriptId}/storyboard-config`,
      config
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
