import React, { useState, useEffect } from 'react';
import {
  Music,
  Volume2,
  Headphones,
  Wind,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Download,
  Trash2,
  Settings,
  Layers,
  Wand2,
  Loader2,
  VolumeX,
  Volume1
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAudioGeneration } from '../../hooks/useAudioGeneration';

// Import types from hook
interface AudioAssets {
  narration: any[];
  music: any[];
  effects: any[];
  ambiance: any[];
}
import AudioTimeline from './AudioTimeline';
import AudioMixer from './AudioMixer';
import { AudioGenerationModal } from './AudioGenerationModal';

interface AudioPanelProps {
  chapterId: string;
  chapterTitle: string;
  selectedScript: any;
  plotOverview: any;
}

const AudioPanel: React.FC<AudioPanelProps> = ({
  chapterId,
  chapterTitle,
  selectedScript,
  plotOverview
}) => {
  const [activeTab, setActiveTab] = useState<'narration' | 'music' | 'effects' | 'ambiance' | 'timeline'>('narration');
  const [showSettings, setShowSettings] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  const [generationOptions, setGenerationOptions] = useState({
    voiceModel: selectedScript?.script_style === 'cinematic' ? 'elevenlabs_conversational' : 'elevenlabs_narrator',
    musicStyle: 'cinematic',
    effectsIntensity: 'moderate' as 'subtle' | 'moderate' | 'dramatic',
    ambianceType: 'natural',
    audioQuality: 'high' as 'standard' | 'high' | 'premium',
    generateNarration: selectedScript?.script_style !== 'cinematic',
    generateMusic: true,
    generateEffects: true,
    generateAmbiance: true
  });

  const [showGenerationModal, setShowGenerationModal] = useState(false);

  const {
    audioAssets,
    isLoading,
    generatingAudio,
    selectedAudioFiles,
    audioRefs,
    loadAudioAssets,
    generateAudioForScene,
    generateAllAudio,
    playAudio,
    pauseAudio,
    stopAllAudio,
    setAudioVolume,
    deleteAudio,
    exportAudioMix,
    setSelectedAudioFiles
  } = useAudioGeneration(chapterId);

  useEffect(() => {
    loadAudioAssets();
  }, [loadAudioAssets]);

  useEffect(() => {
    if (selectedScript) {
      console.log("selectedScript: ", selectedScript);

      setGenerationOptions(prev => ({
        ...prev,
        voiceModel: selectedScript.script_style === 'cinematic' ? 'elevenlabs_conversational' : 'elevenlabs_narrator',
        generateNarration: selectedScript.script_style !== 'cinematic'
      }));
    }
  }, [selectedScript]);

  const scenes = selectedScript?.scene_descriptions || [];
  const characters = selectedScript?.characters || [];

  const getTabInfo = (type: keyof AudioAssets) => {
    const files = audioAssets[type];
    const completedCount = files.filter(f => f.status === 'completed').length;
    const generatingCount = files.filter(f => f.status === 'generating').length;
    return { completedCount, generatingCount, totalCount: files.length };
  };

  const audioTabs = [
    { id: 'narration', label: 'Narration', icon: Volume2, ...getTabInfo('narration') },
    { id: 'music', label: 'Music', icon: Music, ...getTabInfo('music') },
    { id: 'effects', label: 'Effects', icon: Headphones, ...getTabInfo('effects') },
    { id: 'ambiance', label: 'Ambiance', icon: Wind, ...getTabInfo('ambiance') },
    { id: 'timeline', label: 'Timeline', icon: Layers, completedCount: null, generatingCount: 0, totalCount: null }
  ];

  const handleGenerateAll = () => {
    if (!scenes.length) {
      toast.error('No scenes available to generate audio for');
      return;
    }

    setShowGenerationModal(true);
  };

  const handleConfirmGeneration = async () => {
    console.log('[DEBUG] handleConfirmGeneration called');
    console.log('[DEBUG] scenes:', scenes);
    console.log('[DEBUG] generationOptions:', generationOptions);
    await generateAllAudio(scenes, generationOptions);
  };

  const handlePlayPause = () => {
    if (isPlaying) {
      stopAllAudio();
      setIsPlaying(false);
    } else {
      // Play all selected audio files
      selectedAudioFiles.forEach(audioId => playAudio(audioId));
      setIsPlaying(true);
    }
  };

  const renderHeader = () => (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h3 className="text-xl font-semibold text-gray-900">Audio Production</h3>
        <p className="text-gray-600">Generate and manage audio for {chapterTitle}</p>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
        <button
          onClick={handleGenerateAll}
          disabled={!scenes.length || generatingAudio.size > 0}
          className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400"
        >
          <Wand2 className="w-4 h-4" />
          <span>Generate All Audio</span>
        </button>
        <button
          onClick={exportAudioMix}
          disabled={Object.values(audioAssets).every(arr => arr.length === 0)}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
        >
          <Download className="w-4 h-4" />
          <span>Export Mix</span>
        </button>
      </div>
    </div>
  );

  const renderSettings = () => (
    showSettings && (
      <div className="bg-white border rounded-lg p-6 mb-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Audio Generation Settings</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
           {generationOptions.generateNarration && (
             <div>
               <label className="block text-sm font-medium text-gray-700 mb-2">
                 Voice Model
                 {selectedScript?.script_style === 'cinematic' && (
                   <span className="text-xs text-blue-600 ml-2">(Character Dialogue)</span>
                 )}
               </label>
               <select
                 value={generationOptions.voiceModel}
                 onChange={(e) => setGenerationOptions(prev => ({ ...prev, voiceModel: e.target.value }))}
                 className="w-full border rounded-md px-3 py-2"
               >
                 <option value="elevenlabs_narrator">Professional Narrator (Storytelling)</option>
                 <option value="elevenlabs_conversational">Conversational (Character Dialogue)</option>
                 <option value="elevenlabs_expressive">Expressive (Dramatic Reading)</option>
                 <option value="openai_tts">OpenAI TTS (Natural)</option>
                 <option value="google_wavenet">Google WaveNet (Clear)</option>
               </select>
               <p className="text-xs text-gray-500 mt-1">
                 {selectedScript?.script_style === 'cinematic'
                   ? 'For character dialogue scripts, conversational voices work best'
                   : 'For narration scripts, professional narrator voices provide the best experience'
                 }
               </p>
             </div>
           )}

           <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Music Style</label>
            <select
              value={generationOptions.musicStyle}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, musicStyle: e.target.value }))}
              className="w-full border rounded-md px-3 py-2"
            >
              <option value="cinematic">Cinematic</option>
              <option value="orchestral">Orchestral</option>
              <option value="electronic">Electronic</option>
              <option value="ambient">Ambient</option>
              <option value="dramatic">Dramatic</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Audio Quality</label>
            <select
              value={generationOptions.audioQuality}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, audioQuality: e.target.value as any }))}
              className="w-full border rounded-md px-3 py-2"
            >
              <option value="standard">Standard</option>
              <option value="high">High Quality</option>
              <option value="premium">Premium</option>
            </select>
          </div>
        </div>

        <div className="mt-4 space-y-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={generationOptions.generateNarration}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, generateNarration: e.target.checked }))}
              className="rounded border-gray-300 text-purple-600"
            />
            <span className="ml-2 text-sm text-gray-700">Generate narration</span>
          </label>
          
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={generationOptions.generateMusic}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, generateMusic: e.target.checked }))}
              className="rounded border-gray-300 text-purple-600"
            />
            <span className="ml-2 text-sm text-gray-700">Generate background music</span>
          </label>
        </div>
      </div>
    )
  );

  const renderTabNavigation = () => (
    <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6">
      {audioTabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id as any)}
          className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
            activeTab === tab.id
              ? 'bg-white text-purple-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <tab.icon className="w-4 h-4" />
          <span>{tab.label}</span>
          {tab.totalCount !== null && (
            <div className="flex items-center space-x-1">
              <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded-full text-xs">
                {tab.completedCount}
              </span>
              {tab.generatingCount > 0 && (
                <div className="flex items-center space-x-1 px-2 py-1 bg-blue-100 text-blue-600 rounded-full text-xs">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>{tab.generatingCount}</span>
                </div>
              )}
            </div>
          )}
        </button>
      ))}
    </div>
  );

  const renderAudioPlayer = () => (
    <div className="bg-gray-900 text-white rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => {}}
            className="p-2 hover:bg-gray-800 rounded"
          >
            <SkipBack className="w-5 h-5" />
          </button>
          
          <button
            onClick={handlePlayPause}
            className="p-3 bg-purple-600 hover:bg-purple-700 rounded-full"
          >
            {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
          </button>
          
          <button
            onClick={() => {}}
            className="p-2 hover:bg-gray-800 rounded"
          >
            <SkipForward className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm">{formatTime(currentTime)}</span>
          <div className="w-64 h-1 bg-gray-700 rounded-full">
            <div 
              className="h-full bg-purple-600 rounded-full"
              style={{ width: `${(currentTime / duration) * 100}%` }}
            />
          </div>
          <span className="text-sm">{formatTime(duration)}</span>
        </div>

        <div className="flex items-center space-x-2">
          <VolumeX className="w-4 h-4" />
          <input
            type="range"
            min="0"
            max="100"
            defaultValue="75"
            className="w-24"
          />
          <Volume2 className="w-4 h-4" />
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (activeTab === 'timeline') {
      return (
        <AudioTimeline
          audioAssets={audioAssets}
          duration={duration}
          currentTime={currentTime}
          onTimeUpdate={setCurrentTime}
          onAudioSelect={(audioId) => {
            setSelectedAudioFiles(prev => {
              const newSet = new Set(prev);
              if (newSet.has(audioId)) {
                newSet.delete(audioId);
              } else {
                newSet.add(audioId);
              }
              return newSet;
            });
          }}
        />
      );
    }

    const audioType = activeTab as keyof AudioAssets;
    const files = audioAssets[audioType];

    return (
      <div className="space-y-4">
        {files.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Music className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No {activeTab} files yet</p>
            <p className="text-sm">Generate audio to see files here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {files
              .sort((a, b) => {
                // Sort by status: generating first, then completed, then failed
                const statusOrder = { generating: 0, completed: 1, failed: 2, pending: 3 };
                return statusOrder[a.status] - statusOrder[b.status];
              })
              .map(file => (
                <AudioFileCard
                  key={file.id}
                  file={file}
                  isSelected={selectedAudioFiles.has(file.id)}
                  onSelect={() => {
                    setSelectedAudioFiles(prev => {
                      const newSet = new Set(prev);
                      if (newSet.has(file.id)) {
                        newSet.delete(file.id);
                      } else {
                        newSet.add(file.id);
                      }
                      return newSet;
                    });
                  }}
                  onPlay={() => playAudio(file.id)}
                  onPause={() => pauseAudio(file.id)}
                  onVolumeChange={(volume) => setAudioVolume(file.id, volume)}
                  onDelete={() => deleteAudio(file.id, audioType)}
                  audioRef={(el) => {
                    if (el) audioRefs.current[file.id] = el;
                  }}
                />
              ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {renderHeader()}
      {renderSettings()}
      {renderAudioPlayer()}
      {renderTabNavigation()}
      {renderContent()}
      <AudioGenerationModal
        isOpen={showGenerationModal}
        onClose={() => setShowGenerationModal(false)}
        onConfirm={handleConfirmGeneration}
        sceneCount={scenes.length}
      />
    </div>
  );
};

// Helper component for audio file cards
const AudioFileCard: React.FC<{
  file: any;
  isSelected: boolean;
  onSelect: () => void;
  onPlay: () => void;
  onPause: () => void;
  onVolumeChange: (volume: number) => void;
  onDelete: () => void;
  audioRef: (el: HTMLAudioElement | null) => void;
}> = ({ file, isSelected, onSelect, onPlay, onPause, onVolumeChange, onDelete, audioRef }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const isGenerating = file.status === 'generating';
  const isFailed = file.status === 'failed';

  return (
    <div className={`bg-white border rounded-lg p-4 ${isSelected ? 'border-purple-500' : ''} ${isGenerating ? 'border-blue-300 bg-blue-50' : ''} ${isFailed ? 'border-red-300 bg-red-50' : ''}`}>
      {file.url && <audio ref={audioRef} src={file.url} />}

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="rounded border-gray-300 text-purple-600"
            disabled={isGenerating}
          />
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h5 className="font-medium text-gray-900">{file.name}</h5>
              {isGenerating && (
                <div className="flex items-center space-x-1 text-blue-600">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Generating...</span>
                </div>
              )}
              {isFailed && (
                <span className="text-sm text-red-600">Failed</span>
              )}
            </div>
            <p className="text-sm text-gray-500">
              Scene {file.sceneNumber}
              {file.duration > 0 && ` • ${formatTime(file.duration)}`}
              {file.character && ` • ${file.character}`}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!isGenerating && !isFailed && (
            <button
              onClick={() => {
                if (isPlaying) {
                  onPause();
                  setIsPlaying(false);
                } else {
                  onPlay();
                  setIsPlaying(true);
                }
              }}
              className="p-2 text-purple-600 hover:bg-purple-50 rounded"
              disabled={!file.url}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
          )}

          <button
            onClick={onDelete}
            className="p-2 text-red-600 hover:bg-red-50 rounded"
            disabled={isGenerating}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Waveform visualization or generating placeholder */}
      <div className="h-12 bg-gray-100 rounded mb-3">
        <div className="h-full flex items-center justify-center">
          {isGenerating ? (
            <div className="flex items-center space-x-2 text-blue-600">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Processing audio...</span>
            </div>
          ) : file.url ? (
            <div className="flex space-x-1">
              {[...Array(30)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-purple-400 rounded"
                  style={{ height: `${Math.random() * 100}%` }}
                />
              ))}
            </div>
          ) : (
            <span className="text-sm text-gray-500">Audio not ready</span>
          )}
        </div>
      </div>

      {/* Volume control - only show for completed files */}
      {file.status === 'completed' && (
        <div className="flex items-center space-x-2">
          <Volume1 className="w-4 h-4 text-gray-500" />
          <input
            type="range"
            min="0"
            max="100"
            defaultValue={file.volume * 100}
            onChange={(e) => onVolumeChange(parseInt(e.target.value) / 100)}
            className="flex-1"
          />
          <Volume2 className="w-4 h-4 text-gray-500" />
        </div>
      )}
    </div>
  );
};

// Helper function to format time
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default AudioPanel;
