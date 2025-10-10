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
}> = ({ scene, onSelect, onUpdate, onDelete, isSelected, disabled, scriptScene, sceneCharacters }) => {
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
      className={`bg-white rounded-lg border p-4 cursor-pointer hover:shadow-md transition-shadow ${
        isSelected
          ? 'border-blue-500 bg-blue-50'
          : scene.status === 'completed'
            ? 'border-green-500'
            : 'border-gray-200'
      } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div {...attributes} {...listeners} className="cursor-grab">
            <GripVertical className="w-4 h-4 text-gray-400" />
          </div>
          <span className="text-sm font-medium text-gray-900">
            Scene {scene.sceneNumber}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <Edit2 className="w-3 h-3 text-gray-500" />
          </button>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1 hover:bg-red-50 rounded"
            >
              <Trash2 className="w-3 h-3 text-red-500" />
            </button>
          )}
        </div>
      </div>

      <div onClick={disabled ? undefined : onSelect} className="space-y-3">
        {/* Scene Thumbnail */}
        <div className="relative aspect-video bg-gray-100 rounded overflow-hidden">
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
        </div>

        {/* Scene Info */}
        <div className="space-y-2">
          {isEditing ? (
            <div className="flex items-center space-x-2">
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-20 px-2 py-1 border rounded text-sm"
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
              <div className="flex items-center justify-between text-xs text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock className="w-3 h-3" />
                  <span>{scene.duration}s</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Music className="w-3 h-3" />
                  <span>{scene.audioFiles.length} audio</span>
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
  selectedScript
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

  // Recompute markers on selection changes
  useEffect(() => {
    // Log script and scene mapping for debugging
    console.log('SceneTimeline: Script/Scene mapping', {
      selectedScriptId,
      selectedChapterId,
      selectedSegmentId,
      versionToken,
      scriptScenes: selectedScript?.scene_descriptions?.length || 0,
      currentScenes: scenes.length,
      scriptCharacters: selectedScript?.characters?.length || 0
    });
    
    // Validate scene-scene_description mapping
    if (selectedScript?.scene_descriptions && scenes.length > 0) {
      console.log('SceneTimeline: Scene mapping validation', {
        scriptScenes: selectedScript.scene_descriptions.length,
        videoScenes: scenes.length,
        match: selectedScript.scene_descriptions.length === scenes.length
      });
    }
  }, [selectedScriptId, selectedChapterId, versionToken, selectedScript, scenes]);

  // Center active segment on change (optional)
  useEffect(() => {
    if (selectedSegmentId) {
      // Scroll active marker into view if needed
      // This could be implemented with refs to scroll to the selected scene card
      console.log('Active segment changed to:', selectedSegmentId);
    }
  }, [selectedSegmentId]);

  // Listen for timeline events
  useEffect(() => {
    const unsub = subscribe((evt) => {
      if (evt === 'TIMELINE_RECALC_REQUESTED' || evt === 'SEGMENT_CHANGED') {
        // Recompute sizes/positions if needed
        console.log('SceneTimeline: Recomputing layout due to', evt);
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
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>

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
