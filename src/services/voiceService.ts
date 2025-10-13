import { apiClient } from "../lib/api";

export interface VoiceConfig {
  voiceId: string;
  stability: number;
  similarityBoost: number;
  style: number;
}

export interface CharacterVoice {
  id: string;
  name: string;
  description: string;
  voiceId: string;
  personality: string;
}

export const voiceService = {
  getAvailableVoices: async (): Promise<any[]> => {
    const response = await apiClient.get<{ voices: any[] }>("/ai/voices");
    return response.voices;
  },

  generateSpeech: async (
    text: string,
    character: any,
    emotion: string
  ): Promise<string> => {
    const response = await apiClient.post<{ audio_url: string }>(
      "/ai/generate-voice",
      {
        text,
        character: character.name,
        emotion,
      }
    );
    return response.audio_url;
  },

  async getAvailableVoices(): Promise<CharacterVoice[]> {
    if (!this.apiKey) {
      return this.getFallbackVoices();
    }

    try {
      const response = await axios.get(`${this.baseUrl}/voices`, {
        headers: {
          "xi-api-key": this.apiKey,
        },
      });

      return response.data.voices.map((voice: any) => ({
        id: voice.voice_id,
        name: voice.name,
        description: voice.description || "AI-generated voice",
        voiceId: voice.voice_id,
        personality: voice.labels?.accent || "neutral",
      }));
    } catch (error) {
      return this.getFallbackVoices();
    }
  },

  getFallbackVoices(): CharacterVoice[] {
    return [
      {
        id: "narrator",
        name: "Narrator",
        description: "Professional storytelling voice",
        voiceId: "default",
        personality: "authoritative",
      },
      {
        id: "character1",
        name: "Hero",
        description: "Young, adventurous character",
        voiceId: "default",
        personality: "enthusiastic",
      },
      {
        id: "character2",
        name: "Wise Mentor",
        description: "Elderly, wise character",
        voiceId: "default",
        personality: "calm",
      },
    ];
  },

  async playCharacterDialogue(
    dialogue: string,
    character: CharacterVoice,
    emotion: string = "neutral"
  ): Promise<void> {
    const voiceConfig: VoiceConfig = {
      voiceId: character.voiceId,
      stability: 0.75,
      similarityBoost: 0.75,
      style: emotion === "excited" ? 0.8 : emotion === "sad" ? 0.2 : 0.5,
    };

    const audioBlob = await this.generateSpeech(dialogue, voiceConfig);

    if (audioBlob) {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      return new Promise((resolve, reject) => {
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.onerror = reject;
        audio.play().catch(reject);
      });
    }
  },
};
