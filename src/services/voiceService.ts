import axios from 'axios';

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

class VoiceService {
  private apiKey: string;
  private baseUrl = 'https://api.elevenlabs.io/v1';

  constructor() {
    this.apiKey = import.meta.env.VITE_ELEVENLABS_API_KEY || '';
  }

  async generateSpeech(text: string, voiceConfig: VoiceConfig): Promise<Blob | null> {
    if (!this.apiKey) {
      console.warn('ElevenLabs API key not configured');
      return null;
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}/text-to-speech/${voiceConfig.voiceId}`,
        {
          text,
          model_id: 'eleven_multilingual_v2',
          voice_settings: {
            stability: voiceConfig.stability,
            similarity_boost: voiceConfig.similarityBoost,
            style: voiceConfig.style,
            use_speaker_boost: true
          }
        },
        {
          headers: {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': this.apiKey
          },
          responseType: 'blob'
        }
      );

      return response.data;
    } catch (error) {
      console.error('Error generating speech:', error);
      return null;
    }
  }

  async getAvailableVoices(): Promise<CharacterVoice[]> {
    if (!this.apiKey) {
      return this.getFallbackVoices();
    }

    try {
      const response = await axios.get(`${this.baseUrl}/voices`, {
        headers: {
          'xi-api-key': this.apiKey
        }
      });

      return response.data.voices.map((voice: any) => ({
        id: voice.voice_id,
        name: voice.name,
        description: voice.description || 'AI-generated voice',
        voiceId: voice.voice_id,
        personality: voice.labels?.accent || 'neutral'
      }));
    } catch (error) {
      console.error('Error fetching voices:', error);
      return this.getFallbackVoices();
    }
  }

  private getFallbackVoices(): CharacterVoice[] {
    return [
      {
        id: 'narrator',
        name: 'Narrator',
        description: 'Professional storytelling voice',
        voiceId: 'default',
        personality: 'authoritative'
      },
      {
        id: 'character1',
        name: 'Hero',
        description: 'Young, adventurous character',
        voiceId: 'default',
        personality: 'enthusiastic'
      },
      {
        id: 'character2',
        name: 'Wise Mentor',
        description: 'Elderly, wise character',
        voiceId: 'default',
        personality: 'calm'
      }
    ];
  }

  async playCharacterDialogue(dialogue: string, character: CharacterVoice, emotion: string = 'neutral'): Promise<void> {
    const voiceConfig: VoiceConfig = {
      voiceId: character.voiceId,
      stability: 0.75,
      similarityBoost: 0.75,
      style: emotion === 'excited' ? 0.8 : emotion === 'sad' ? 0.2 : 0.5
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
  }
}

export const voiceService = new VoiceService();