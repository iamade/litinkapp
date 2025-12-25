import React, { useState, useEffect } from 'react';
import { voiceService, CharacterVoice } from '../services/voiceService';
import { videoService, VideoScene, AvatarConfig } from '../services/videoService';
import { blockchainService } from '../services/blockchainService';
import { Play, Pause, Volume2, VolumeX, Film, Award, Loader } from 'lucide-react';

interface StoryBranch {
  id: string;
  content: string;
  choices: {
    text: string;
    nextBranchId: string;
    consequence: string;
  }[];
  characterDialogue?: {
    character: string;
    text: string;
    emotion: string;
  }[];
  videoScene?: VideoScene;
}

interface VoiceStoryComponentProps {
  storyContent: string;
  onChoiceMade: (choice: string, consequence: string) => void;
}

export default function VoiceStoryComponent({ storyContent, onChoiceMade }: VoiceStoryComponentProps) {
  const [currentBranch, setCurrentBranch] = useState<StoryBranch | null>(null);
  const [voices, setVoices] = useState<CharacterVoice[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [earnedNFT, setEarnedNFT] = useState<any>(null);
  const [generatingNFT, setGeneratingNFT] = useState(false);

  useEffect(() => {
    initializeStory();
    loadVoices();
  }, [storyContent]);

  const initializeStory = () => {
    // Create initial story branch
    const initialBranch: StoryBranch = {
      id: 'start',
      content: `You find yourself standing at the edge of a mystical forest. The ancient trees whisper secrets in the wind, and two paths diverge before you. The left path glows with a soft blue light, while the right path is shrouded in mysterious shadows.`,
      choices: [
        {
          text: 'Take the glowing blue path',
          nextBranchId: 'blue-path',
          consequence: 'You discover a magical crystal that grants you wisdom'
        },
        {
          text: 'Venture into the shadowy path',
          nextBranchId: 'shadow-path',
          consequence: 'You encounter a mysterious guardian who tests your courage'
        },
        {
          text: 'Call out to see if anyone responds',
          nextBranchId: 'call-out',
          consequence: 'A wise owl appears and offers guidance'
        }
      ],
      characterDialogue: [
        {
          character: 'Narrator',
          text: 'Welcome to the Crystal Chronicles, where your choices shape destiny itself.',
          emotion: 'mysterious'
        }
      ]
    };

    setCurrentBranch(initialBranch);
  };

  const loadVoices = async () => {
    try {
      const availableVoices = await voiceService.getAvailableVoices();
      setVoices(availableVoices);
    } catch (error) {
    }
  };

  const playDialogue = async (dialogue: string, characterName: string, emotion: string) => {
    if (isMuted) return;

    setIsPlaying(true);
    try {
      const character = voices.find(v => v.name === characterName) || voices[0];
      if (character) {
        await voiceService.playCharacterDialogue(dialogue, character, emotion);
      }
    } catch (error) {
    } finally {
      setIsPlaying(false);
    }
  };

  const generateVideoScene = async (sceneDescription: string, dialogue: string) => {
    setGeneratingVideo(true);
    try {
      const avatarConfig: AvatarConfig = {
        avatarId: 'narrator-avatar',
        voice: 'professional',
        background: 'fantasy',
        style: 'animated'
      };

      const videoScene = await videoService.generateStoryScene(sceneDescription, dialogue, avatarConfig);
      
      if (videoScene && currentBranch) {
        setCurrentBranch({
          ...currentBranch,
          videoScene
        });
      }
    } catch (error) {
    } finally {
      setGeneratingVideo(false);
    }
  };

  const handleChoiceSelect = async (choice: any) => {
    // Award NFT for significant story moments
    if (choice.consequence.includes('crystal') || choice.consequence.includes('guardian')) {
      await awardStoryNFT(choice.consequence);
    }

    // Generate next branch based on choice
    const nextBranch = generateNextBranch(choice);
    setCurrentBranch(nextBranch);
    
    onChoiceMade(choice.text, choice.consequence);

    // Auto-play dialogue for new branch
    if (nextBranch.characterDialogue && nextBranch.characterDialogue.length > 0) {
      const dialogue = nextBranch.characterDialogue[0];
      setTimeout(() => {
        playDialogue(dialogue.text, dialogue.character, dialogue.emotion);
      }, 1000);
    }
  };

  const generateNextBranch = (choice: any): StoryBranch => {
    const branchId = choice.nextBranchId;
    
    // Generate different story branches based on choice
    switch (branchId) {
      case 'blue-path':
        return {
          id: branchId,
          content: `The blue light guides you to a clearing where a magnificent crystal hovers above an ancient pedestal. As you approach, the crystal pulses with energy and whispers of ancient knowledge fill your mind.`,
          choices: [
            {
              text: 'Touch the crystal',
              nextBranchId: 'crystal-touch',
              consequence: 'You gain the power to understand all languages'
            },
            {
              text: 'Study the pedestal inscriptions',
              nextBranchId: 'study-inscriptions',
              consequence: 'You learn the location of a hidden treasure'
            }
          ],
          characterDialogue: [
            {
              character: 'Crystal Spirit',
              text: 'Seeker of wisdom, you have chosen the path of enlightenment. What knowledge do you desire?',
              emotion: 'ethereal'
            }
          ]
        };
      
      case 'shadow-path':
        return {
          id: branchId,
          content: `The shadows part to reveal a towering guardian made of living stone. Its eyes glow with ancient fire as it blocks your path, testing your resolve with its imposing presence.`,
          choices: [
            {
              text: 'Challenge the guardian to combat',
              nextBranchId: 'combat-guardian',
              consequence: 'You prove your strength and earn the guardian\'s respect'
            },
            {
              text: 'Attempt to negotiate',
              nextBranchId: 'negotiate-guardian',
              consequence: 'You discover the guardian\'s tragic past and help heal its pain'
            }
          ],
          characterDialogue: [
            {
              character: 'Stone Guardian',
              text: 'Who dares disturb the ancient watch? Prove your worth, or turn back now!',
              emotion: 'threatening'
            }
          ]
        };
      
      default:
        return {
          id: 'call-out',
          content: `Your voice echoes through the forest, and a magnificent owl with silver feathers descends from the canopy. Its wise eyes seem to see into your very soul.`,
          choices: [
            {
              text: 'Ask for guidance about the paths',
              nextBranchId: 'owl-guidance',
              consequence: 'The owl reveals the true nature of your quest'
            },
            {
              text: 'Inquire about the forest\'s history',
              nextBranchId: 'forest-history',
              consequence: 'You learn about an ancient prophecy'
            }
          ],
          characterDialogue: [
            {
              character: 'Wise Owl',
              text: 'Greetings, traveler. I am the keeper of this forest\'s secrets. What wisdom do you seek?',
              emotion: 'wise'
            }
          ]
        };
    }
  };

  const awardStoryNFT = async (storyMoment: string) => {
    setGeneratingNFT(true);
    try {
      const nft = await blockchainService.simulateEarnNFT(storyMoment);
      setEarnedNFT(nft);
    } catch (error) {
    } finally {
      setGeneratingNFT(false);
    }
  };

  if (!currentBranch) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
        <div className="text-center">
          <Loader className="h-12 w-12 text-purple-600 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">Loading your interactive story...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      {/* Video Scene */}
      {currentBranch.videoScene && (
        <div className="relative">
          <video
            src={currentBranch.videoScene.videoUrl}
            poster={currentBranch.videoScene.thumbnailUrl}
            controls
            className="w-full h-64 object-cover"
          />
          <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
            AI-Generated Scene
          </div>
        </div>
      )}

      <div className="p-8">
        {/* Story Content */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900">Interactive Story</h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                {isMuted ? <VolumeX className="h-5 w-5 text-gray-600" /> : <Volume2 className="h-5 w-5 text-gray-600" />}
              </button>
              
              {!currentBranch.videoScene && (
                <button
                  onClick={() => generateVideoScene(currentBranch.content, currentBranch.characterDialogue?.[0]?.text || '')}
                  disabled={generatingVideo}
                  className="flex items-center space-x-2 bg-purple-100 text-purple-700 px-3 py-2 rounded-full text-sm hover:bg-purple-200 transition-colors disabled:opacity-50"
                >
                  {generatingVideo ? (
                    <Loader className="h-4 w-4 animate-spin" />
                  ) : (
                    <Film className="h-4 w-4" />
                  )}
                  <span>{generatingVideo ? 'Generating...' : 'Generate Scene'}</span>
                </button>
              )}
            </div>
          </div>
          
          <p className="text-gray-700 leading-relaxed text-lg mb-6">
            {currentBranch.content}
          </p>
        </div>

        {/* Character Dialogue */}
        {currentBranch.characterDialogue && currentBranch.characterDialogue.length > 0 && (
          <div className="mb-6">
            {currentBranch.characterDialogue.map((dialogue, index) => (
              <div key={index} className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-purple-900">{dialogue.character}</span>
                  <button
                    onClick={() => playDialogue(dialogue.text, dialogue.character, dialogue.emotion)}
                    disabled={isPlaying}
                    className="flex items-center space-x-1 bg-purple-600 text-white px-3 py-1 rounded-full text-sm hover:bg-purple-700 transition-colors disabled:opacity-50"
                  >
                    {isPlaying ? (
                      <Pause className="h-3 w-3" />
                    ) : (
                      <Play className="h-3 w-3" />
                    )}
                    <span>Voice</span>
                  </button>
                </div>
                <p className="text-purple-800 italic">"{dialogue.text}"</p>
              </div>
            ))}
          </div>
        )}

        {/* NFT Award Notification */}
        {(earnedNFT || generatingNFT) && (
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-6 mb-6">
            {generatingNFT ? (
              <div className="text-center">
                <Loader className="h-8 w-8 text-purple-600 mx-auto mb-2 animate-spin" />
                <p className="text-purple-800 font-medium">Minting your story collectible...</p>
              </div>
            ) : earnedNFT ? (
              <div className="text-center">
                <Award className="h-12 w-12 text-purple-600 mx-auto mb-3" />
                <h4 className="text-lg font-bold text-purple-900 mb-2">🎉 Story NFT Earned!</h4>
                <p className="text-purple-800 font-medium">{earnedNFT.name}</p>
                <p className="text-sm text-purple-600 mt-1">Collectible story moment</p>
                <div className="mt-3 text-xs text-purple-600">
                  Asset ID: {earnedNFT.assetId} | TX: {earnedNFT.transactionId?.substring(0, 8)}...
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Story Choices */}
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-900 mb-4">What do you choose?</h4>
          {currentBranch.choices.map((choice, index) => (
            <button
              key={index}
              onClick={() => handleChoiceSelect(choice)}
              className="w-full text-left p-4 rounded-xl border-2 border-gray-300 hover:border-purple-500 hover:bg-purple-50 transition-all group"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900 group-hover:text-purple-900">
                  {choice.text}
                </span>
                <span className="text-sm text-gray-500 group-hover:text-purple-600">
                  →
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1 group-hover:text-purple-700">
                {choice.consequence}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}