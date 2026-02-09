// src/components/Video/SceneTimeline.tsx
import React, { useState, useEffect } from 'react';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import {
  SortableContext,
  horizontalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Clock,
  Image,
  Music,
  Shuffle,
  Plus,
  Edit2,
  Trash2,
  GripVertical,
  Users
} from 'lucide-react';
import type { VideoScene, Transition } from '../../types/videoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';
import { SceneAudioManager } from './SceneAudioManager';
// Define ChapterScript interface locally to avoid import issues
interface ChapterScript {
  id: string;
  chapter_id: string;
  script_style: string;
  script_name: string;
  script: string;
  scene_descriptions: SceneDescription[];
  characters: string[];
  character_details: string;
  acts: unknown[];
  beats: unknown[];
  scenes: unknown[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
}

interface SceneDescription {
  scene_number: number;
  location: string;
  time_of_day: string;
  characters: string[];
  key_actions: string;
  estimated_duration: number;
  visual_description: string;
  audio_requirements: string;
}

interface SceneTimelineProps {
  scenes: VideoScene[];
  onSceneSelect: (scene: VideoScene) => void;
  onSceneUpdate: (sceneId: string, updates: Partial<VideoScene>) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
  onAddTransition: (sceneId: string, transition: Transition) => void;
  selectedScript?: ChapterScript | null;
  selectedShotIds?: string[];  // Shot IDs selected for video generation
  onToggleShotSelection?: (shotId: string) => void;  // Toggle shot selection
  generatingShotIds?: Set<string>;  // Shot IDs currently being generated
}

const SceneCard: React.FC<{
  scene: VideoScene;
  onSelect: () => void;
  onUpdate: (updates: Partial<VideoScene>) => void;
  onDelete?: () => void;
  isSelected: boolean;
  disabled?: boolean;
  scriptScene?: SceneDescription;
  sceneCharacters?: string[];
  storyboardAudioCount?: number;
  onManageAudio: () => void;
  isSelectedForGeneration?: boolean;  // Whether this scene is selected for video generation
  onToggleSelection?: () => void;     // Toggle selection for video generation
  isGenerating?: boolean;             // Whether this scene is currently being generated
}> = ({ scene, onSelect, onUpdate, onDelete, isSelected, disabled, scriptScene, sceneCharacters, storyboardAudioCount, onManageAudio, isSelectedForGeneration, onToggleSelection, isGenerating }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: scene.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1
  };

  const [isEditing, setIsEditing] = useState(false);
  const [duration, setDuration] = useState(scene.duration.toString());

  const handleDurationSave = () => {
    const newDuration = parseFloat(duration);
    if (!isNaN(newDuration) && newDuration > 0) {
      onUpdate({ duration: newDuration });
      setIsEditing(false);
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`bg-white dark:bg-gray-800 rounded-lg border p-4 cursor-pointer hover:shadow-md transition-shadow ${
        isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : isGenerating
            ? 'border-yellow-400 ring-2 ring-yellow-300/50'
            : scene.status === 'completed'
              ? 'border-green-500'
              : 'border-gray-200 dark:border-gray-700'
      } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div {...attributes} {...listeners} className="cursor-grab">
            <GripVertical className="w-4 h-4 text-gray-400" />
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            Scene {scene.sceneNumber}
          </span>
          {scene.shotType && (
            <span className={`px-1.5 py-0.5 text-xs rounded ${scene.shotType === 'key_scene' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}`}>
              {scene.shotType === 'key_scene' ? 'Key Scene' : 'Suggested Shot'}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={(e) => {
               e.stopPropagation();
               onManageAudio();
            }}
            className="p-1.5 hover:bg-blue-100 bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50 rounded-md border border-blue-200 dark:border-blue-800"
            title="Manage Scene Audio"
          >
            <Music className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <Edit2 className="w-3 h-3 text-gray-500 dark:text-gray-400" />
          </button>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <Trash2 className="w-3 h-3 text-red-500" />
            </button>
          )}
        </div>
      </div>

      <div onClick={disabled ? undefined : onSelect} className="space-y-3">
        {/* Scene Thumbnail */}
        <div className="relative aspect-video bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
          {/* Selection Checkbox */}
          <div 
            className="absolute top-2 left-2 z-10"
            onClick={(e) => {
              e.stopPropagation();
              onToggleSelection?.();
            }}
          >
            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center cursor-pointer transition-colors ${
              isSelectedForGeneration 
                ? 'bg-blue-500 border-blue-500' 
                : 'bg-white/80 border-gray-400 hover:border-blue-400 dark:bg-gray-800/80 dark:border-gray-500'
            }`}>
              {isSelectedForGeneration && (
                <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>
          
          {scene.thumbnailUrl || scene.imageUrl ? (
            <img
              src={scene.thumbnailUrl || scene.imageUrl}
              alt={`Scene ${scene.sceneNumber}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <Image className="w-8 h-8 text-gray-400" />
            </div>
          )}
          {scene.transitions.length > 0 && (
            <div className="absolute top-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
              {scene.transitions[0].type}
            </div>
          )}
          {/* Generating Overlay */}
          {isGenerating && (
            <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center z-20 rounded">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-white border-t-transparent mb-2" />
              <span className="text-white text-xs font-medium">Generating...</span>
            </div>
          )}
        </div>

        {/* Scene Info */}
        <div className="space-y-2">
          {isEditing ? (
            <div className="flex items-center space-x-2">
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-20 px-2 py-1 border rounded text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                step="0.1"
                min="0.1"
                onClick={(e) => e.stopPropagation()}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDurationSave();
                }}
                className="text-xs bg-blue-600 text-white px-2 py-1 rounded"
              >
                Save
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Duration and Audio Info */}
              <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                <div className="flex items-center space-x-1">
                  <Clock className="w-3 h-3" />
                  <span>{scene.duration}s</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Music className="w-3 h-3" />
                  <span>{storyboardAudioCount !== undefined ? storyboardAudioCount : scene.audioFiles.length} audio</span>
                </div>
              </div>
              
              {/* Script-specific character info */}
              {sceneCharacters && sceneCharacters.length > 0 && (
                <div className="flex items-center space-x-1 text-xs text-blue-600">
                  <Users className="w-3 h-3" />
                  <span className="truncate">{sceneCharacters.join(', ')}</span>
                </div>
              )}
              
              {/* Script scene description preview */}
              {scriptScene?.location && (
                <div className="text-xs text-gray-500 truncate">
                  {scriptScene.location} • {scriptScene.time_of_day}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const SceneTimeline: React.FC<SceneTimelineProps> = ({
  scenes,
  onSceneSelect,
  onSceneUpdate,
  onReorder,
  onAddTransition,
  selectedScript,
  selectedShotIds = [],
  onToggleShotSelection,
  generatingShotIds = new Set()
}) => {
  // Script selection context integration
  const {
    selectedScriptId,
    selectedChapterId,
    selectedSegmentId,
    versionToken,
    isSwitching,
    selectSegment,
    subscribe,
  } = useScriptSelection();
  
  const [managingAudioSceneNum, setManagingAudioSceneNum] = useState<number | null>(null);

  // Recompute markers on selection changes
  useEffect(() => {
    // Validate scene-scene_description mapping
    if (selectedScript?.scene_descriptions && scenes.length > 0) {
      // Scene validation logic
    }
  }, [selectedScriptId, selectedChapterId, versionToken, selectedScript, scenes]);

  // Center active segment on change (optional)
  useEffect(() => {
    if (selectedSegmentId) {
      // Scroll active marker into view if needed
      // This could be implemented with refs to scroll to the selected scene card
    }
  }, [selectedSegmentId]);

  // Listen for timeline events
  useEffect(() => {
    const unsub = subscribe((evt) => {
      if (evt === 'TIMELINE_RECALC_REQUESTED' || evt === 'SEGMENT_CHANGED') {
        // Recompute sizes/positions if needed
        // Force re-render or recalculate layout
      }
    });
    return unsub;
  }, [subscribe]);

  // Click handler for segment selection
  const handleMarkerClick = (sceneId: string) => {
    if (isSwitching) return;
    selectSegment(sceneId, { reason: 'user' });
  };

  // Storyboard context for audio counts
  const storyboardContext = useStoryboardOptional();

  // Disabled during switching
  const disabled = isSwitching;
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      const oldIndex = scenes.findIndex(s => s.id === active.id);
      const newIndex = scenes.findIndex(s => s.id === over.id);
      onReorder(oldIndex, newIndex);
    }
  };

  const totalDuration = scenes.reduce((sum, scene) => sum + scene.duration, 0);

  // If no script is selected, render inert timeline
  if (!selectedScriptId) {
    return (
      <div className="space-y-4 opacity-50">
        {/* Timeline Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h4 className="text-lg font-semibold text-gray-900">Timeline</h4>
            <div className="text-sm text-gray-600">
              Select a script to view timeline
            </div>
          </div>
        </div>

        {/* Inert Timeline Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-100 rounded-lg border border-gray-200 p-4 opacity-50">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500">Scene {i}</span>
              </div>
              <div className="aspect-video bg-gray-200 rounded flex items-center justify-center">
                <Image className="w-8 h-8 text-gray-400" />
              </div>
              <div className="mt-2 text-xs text-gray-500 text-center">
                No data available
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${disabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {/* Timeline Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h4 className="text-lg font-semibold text-gray-900">Timeline</h4>
          <div className="text-sm text-gray-600">
            {scenes.length} scenes • {totalDuration.toFixed(1)}s total
          </div>
        </div>
        <button className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          <Plus className="w-3 h-3" />
          <span>Add Scene</span>
        </button>
      </div>

      {/* Timeline Grid */}
      <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={scenes.map(s => s.id)}
          strategy={horizontalListSortingStrategy}
        >
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {scenes.map((scene, index) => {
              // Get script-specific scene description if available
              const scriptScene = selectedScript?.scene_descriptions?.[index];
              const sceneCharacters = scriptScene?.characters || [];
              
              return (
                <SceneCard
                  key={scene.id}
                  scene={scene}
                  onSelect={() => {
                    onSceneSelect(scene);
                    handleMarkerClick(scene.id);
                  }}
                  onUpdate={(updates) => onSceneUpdate(scene.id, updates)}
                  isSelected={scene.id === selectedSegmentId}
                  disabled={disabled}
                  scriptScene={scriptScene}
                  sceneCharacters={sceneCharacters}
                  storyboardAudioCount={storyboardContext?.getAudioForShot(scene.sceneNumber, scene.shotIndex)?.length ?? 0}
                  onManageAudio={() => setManagingAudioSceneNum(scene.sceneNumber)}
                  isSelectedForGeneration={selectedShotIds.includes(scene.id)}
                  onToggleSelection={() => onToggleShotSelection?.(scene.id)}
                  isGenerating={generatingShotIds.has(scene.id) || generatingShotIds.has('__all__')}
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>
      
      {managingAudioSceneNum !== null && (
        <SceneAudioManager
          sceneNumber={managingAudioSceneNum}
          availableShots={scenes.filter(s => s.sceneNumber === managingAudioSceneNum)}
          onClose={() => setManagingAudioSceneNum(null)}
        />
      )}

      {/* Timeline Controls */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="flex items-center space-x-2">
          <button
            className={`flex items-center space-x-2 px-3 py-1 rounded text-sm ${
              disabled
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
            disabled={disabled}
          >
            <Shuffle className="w-3 h-3" />
            <span>Auto-arrange</span>
          </button>
        </div>
        <div className={`text-sm ${
          disabled ? 'text-gray-400' : 'text-gray-600'
        }`}>
          {disabled ? 'Switching scripts...' : 'Drag scenes to reorder • Click to edit'}
        </div>
      </div>
    </div>
  );
};

export default SceneTimeline;
