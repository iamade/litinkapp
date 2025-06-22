import axios from 'axios';

export interface VideoScene {
  id: string;
  title: string;
  description: string;
  videoUrl?: string;
  thumbnailUrl?: string;
  duration?: number;
  status: 'generating' | 'ready' | 'error';
}

export interface AvatarConfig {
  avatarId: string;
  voice: string;
  background: string;
  style: 'realistic' | 'animated' | 'cartoon';
}

class VideoService {
  private apiKey: string;
  private baseUrl = 'https://api.tavus.io/v2';

  constructor() {
    this.apiKey = import.meta.env.VITE_TAVUS_API_KEY || '';
  }

  async generateStoryScene(
    sceneDescription: string, 
    dialogue: string, 
    avatarConfig: AvatarConfig
  ): Promise<VideoScene | null> {
    if (!this.apiKey) {
      console.warn('Tavus API key not configured, using mock video generation');
      return this.generateMockScene(sceneDescription, dialogue);
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}/videos`,
        {
          script: dialogue,
          avatar_id: avatarConfig.avatarId,
          background: avatarConfig.background,
          voice_settings: {
            voice_id: avatarConfig.voice,
            stability: 0.75,
            similarity_boost: 0.75
          },
          video_settings: {
            quality: 'high',
            format: 'mp4'
          }
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      const videoId = response.data.video_id;
      
      // Poll for completion
      return await this.pollVideoStatus(videoId, sceneDescription);
    } catch (error) {
      console.error('Error generating video scene:', error);
      return this.generateMockScene(sceneDescription, dialogue);
    }
  }

  private async pollVideoStatus(videoId: string, sceneDescription: string): Promise<VideoScene> {
    const maxAttempts = 30; // 5 minutes max
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const response = await axios.get(`${this.baseUrl}/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        });

        const video = response.data;
        
        if (video.status === 'completed') {
          return {
            id: videoId,
            title: sceneDescription,
            description: 'AI-generated story scene',
            videoUrl: video.download_url,
            thumbnailUrl: video.thumbnail_url,
            duration: video.duration,
            status: 'ready'
          };
        } else if (video.status === 'failed') {
          return {
            id: videoId,
            title: sceneDescription,
            description: 'Failed to generate scene',
            status: 'error'
          };
        }

        // Wait 10 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 10000));
        attempts++;
      } catch (error) {
        console.error('Error polling video status:', error);
        break;
      }
    }

    // Timeout or error
    return {
      id: videoId,
      title: sceneDescription,
      description: 'Video generation timed out',
      status: 'error'
    };
  }

  private async generateMockScene(sceneDescription: string, dialogue: string): Promise<VideoScene> {
    // Simulate video generation delay
    await new Promise(resolve => setTimeout(resolve, 3000));

    return {
      id: `scene-${Date.now()}`,
      title: sceneDescription,
      description: 'AI-generated story scene (Demo)',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
      thumbnailUrl: 'https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=400',
      duration: 30,
      status: 'ready'
    };
  }

  async getAvailableAvatars(): Promise<AvatarConfig[]> {
    if (!this.apiKey) {
      return this.getMockAvatars();
    }

    try {
      const response = await axios.get(`${this.baseUrl}/avatars`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`
        }
      });

      return response.data.avatars.map((avatar: any) => ({
        avatarId: avatar.avatar_id,
        voice: avatar.voice_id,
        background: 'default',
        style: avatar.style || 'realistic'
      }));
    } catch (error) {
      console.error('Error fetching avatars:', error);
      return this.getMockAvatars();
    }
  }

  private getMockAvatars(): AvatarConfig[] {
    return [
      {
        avatarId: 'narrator-avatar',
        voice: 'professional',
        background: 'library',
        style: 'realistic'
      },
      {
        avatarId: 'character-avatar',
        voice: 'young',
        background: 'fantasy',
        style: 'animated'
      },
      {
        avatarId: 'mentor-avatar',
        voice: 'wise',
        background: 'study',
        style: 'realistic'
      }
    ];
  }
}

export const videoService = new VideoService();