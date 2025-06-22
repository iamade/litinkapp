import { apiClient } from "../lib/api";

export const videoService = {
  // This is a placeholder as the backend doesn't have video endpoints yet.
  // When you add them, the implementation will look like this:

  // getAvailableAvatars: async (): Promise<any[]> => {
  //   return apiClient.get('/ai/avatars');
  // },

  // generateVideo: async (script: string, avatarId: string): Promise<string> => {
  //   const response = await apiClient.post<{ video_url: string }>('/ai/generate-video', { script, avatarId });
  //   return response.video_url;
  // },

  // Mock functionality to avoid breaking the UI
  getAvailableAvatars: async (): Promise<any[]> => {
    console.warn(
      "Video service: Using mock avatars. Implement backend endpoint."
    );
    return [
      { id: "1", name: "avatar-1", preview_url: "/path/to/avatar1.png" },
      { id: "2", name: "avatar-2", preview_url: "/path/to/avatar2.png" },
    ];
  },

  generateVideo: async (script: string, avatarId: string): Promise<string> => {
    console.warn(
      "Video service: Using mock video URL. Implement backend endpoint."
    );
    console.log(
      `Generating video for script: "${script}" with avatar: ${avatarId}`
    );
    // Simulate network delay
    await new Promise((res) => setTimeout(res, 1500));
    return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";
  },
};
