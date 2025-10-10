import React, { useState, useEffect } from 'react';
import { FileText, Edit2, Trash2, Clock, Camera, ChevronDown, ChevronRight } from 'lucide-react';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';

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


interface ChapterScript {
  id: string;
  chapter_id: string;
  script_style: string;
  script_name: string;
  script: string;
  scene_descriptions: SceneDescription[];
  characters: string[];
  character_details: string;
  acts: Act[];
  beats: Beat[];
  scenes: Scene[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
  scriptStoryType?: string; // Added property for story type
}

interface Act {
  act_number: number;
  title: string;
  description: string;
  duration: number;
  scenes: number[];
}

interface Beat {
  beat_number: number;
  act: number;
  title: string;
  description: string;
  emotional_tone: string;
  duration: number;
}

interface Scene {
  scene_number: number;
  act: number;
  beat: string;
  location: string;
  time_of_day: string;
  characters: string[];
  dialogue: string;
  action: string;
  visual_description: string;
  duration: number;
  camera_notes?: string;
  audio_notes?: string;
}

interface ScriptGenerationPanelProps {
  chapterId: string;
  chapterTitle: string;
  chapterContent: string;
  generatedScripts: ChapterScript[];
  isLoading: boolean;
  isGeneratingScript: boolean;
  onGenerateScript: (scriptStyle: string, options: ScriptGenerationOptions) => void;
  onUpdateScript: (scriptId: string, updates: Partial<ChapterScript>) => void;
  onDeleteScript: (scriptId: string) => void;
}

interface ScriptGenerationOptions {
  includeCharacterProfiles: boolean;
  targetDuration?: number | "auto";
  sceneCount?: number;
  focusAreas: string[];
  scriptStoryType?: string; // Added property for script story type
}

const ScriptGenerationPanel: React.FC<ScriptGenerationPanelProps> = ({
  chapterTitle,
  chapterContent,
  generatedScripts,
  isLoading,
  isGeneratingScript,
  onGenerateScript,
  onUpdateScript,
  onDeleteScript
}) => {
  const {
    selectedScriptId,
    isSwitching,
    selectScript,
  } = useScriptSelection();

  // Derive selected script from context
  const selectedScript = generatedScripts.find(script => script.id === selectedScriptId) || null;

  // Initialize selection when scripts load and none is selected
  useEffect(() => {
    if (!selectedScriptId && generatedScripts && generatedScripts.length > 0) {
      selectScript(generatedScripts[0].id, { reason: 'load' });
    }
  }, [selectedScriptId, generatedScripts?.length]);

  // Handle script selection
  const onChooseScript = (id: string) => {
    if (id !== selectedScriptId) {
      selectScript(id, { reason: 'user' });
    }
  };
  const [scriptStyle, setScriptStyle] = useState<'cinematic_movie' | 'cinematic_narration'>('cinematic_movie');
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [generationOptions, setGenerationOptions] = useState<ScriptGenerationOptions>({
    includeCharacterProfiles: true,
    targetDuration: "auto",
    sceneCount: 5,
    focusAreas: []
  });
  const [activeView, setActiveView] = useState<'overview' | 'acts' | 'scenes' | 'dialogue'>('overview');
  const [expandedScenes, setExpandedScenes] = useState<Set<number>>(new Set());
  const [showFullScript, setShowFullScript] = useState(false);

  const handleGenerateScript = () => {
    console.log('[DEBUG] ScriptGenerationPanel - handleGenerateScript called with:', {
      scriptStyle,
      generationOptions,
      scriptStoryType: generationOptions.scriptStoryType || "default"
    });
    onGenerateScript(scriptStyle, {
      ...generationOptions,
      scriptStoryType: generationOptions.scriptStoryType || "default"
    });
  };

  const toggleSceneExpansion = (sceneNumber: number) => {
    setExpandedScenes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sceneNumber)) {
        newSet.delete(sceneNumber);
      } else {
        newSet.add(sceneNumber);
      }
      return newSet;
    });
  };

  const ChapterContent: React.FC<{ content: string }> = ({ content }) => {
    const maxChars = 500;
    const [showFull, setShowFull] = useState(false);
    
    if (content.length <= maxChars) {
      return <p className="text-gray-700 leading-relaxed">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700 leading-relaxed">
          {showFull ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFull(!showFull)}
          className="text-blue-600 hover:text-blue-800 text-sm mt-2 font-medium"
        >
          {showFull ? "Show Less" : "Show More"}
        </button>
      </div>
    );
  };

  const renderScriptGenerationForm = () => (
    <div className="bg-white rounded-lg border p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-semibold text-gray-900">Generate New Script</h4>
        <button
          onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
          className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-800"
        >
          <span>Advanced Options</span>
          {showAdvancedOptions ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Basic Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Script Style</label>
          <select
            value={scriptStyle}
            onChange={(e) => setScriptStyle(e.target.value as 'cinematic_movie' | 'cinematic_narration')}
            className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="cinematic_movie">Character Dialogue</option>
            <option value="cinematic_narration">Voice-over Narration</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {scriptStyle === 'cinematic_movie' 
              ? 'Interactive dialogue between characters' 
              : 'Narrative voice-over storytelling'}
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Script Story Type</label>
          <input
            type="text"
            value={generationOptions.scriptStoryType || ""}
            onChange={(e) => setGenerationOptions(prev => ({
              ...prev,
              scriptStoryType: e.target.value
            }))}
            className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter story type"
          />
          

        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Target Duration</label>
          <select
            value={generationOptions.targetDuration || "auto"}
            onChange={(e) => setGenerationOptions(prev => ({
              ...prev,
              targetDuration: e.target.value === "auto" ? "auto" : parseInt(e.target.value) || "auto"
            }))}
            className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="auto">Auto (Full Story)</option>
            <option value="3">3 minutes</option>
            <option value="5">5 minutes</option>
            <option value="10">10 minutes</option>
            <option value="15">15 minutes</option>
            <option value="20">20 minutes</option>
            <option value="30">30 minutes</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {generationOptions.targetDuration === "auto"
              ? "Automatically determine duration based on content length"
              : `${generationOptions.targetDuration} minute target duration`}
          </p>
        </div>
      </div>

      {/* Advanced Options */}
      {showAdvancedOptions && (
        <div className="space-y-4 pt-4 border-t">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Scene Count</label>
              <input
                type="number"
                min="3"
                max="15"
                value={generationOptions.sceneCount || 5}
                onChange={(e) => setGenerationOptions(prev => ({ 
                  ...prev, 
                  sceneCount: parseInt(e.target.value) || 5 
                }))}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeCharacterProfiles"
                checked={generationOptions.includeCharacterProfiles}
                onChange={(e) => setGenerationOptions(prev => ({ 
                  ...prev, 
                  includeCharacterProfiles: e.target.checked 
                }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="includeCharacterProfiles" className="ml-2 text-sm text-gray-700">
                Include Character Profiles
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Focus Areas</label>
            <div className="flex flex-wrap gap-2">
              {['Action', 'Dialogue', 'Character Development', 'Atmosphere', 'Tension', 'Comedy'].map((area) => (
                <button
                  key={area}
                  onClick={() => setGenerationOptions(prev => ({
                    ...prev,
                    focusAreas: prev.focusAreas.includes(area)
                      ? prev.focusAreas.filter(a => a !== area)
                      : [...prev.focusAreas, area]
                  }))}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    generationOptions.focusAreas.includes(area)
                      ? 'bg-blue-100 text-blue-800 border border-blue-300'
                      : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                  }`}
                >
                  {area}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleGenerateScript}
          disabled={isGeneratingScript}
          className="flex items-center space-x-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-purple-400 disabled:cursor-not-allowed"
        >
          {isGeneratingScript ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              <span>Generating...</span>
            </>
          ) : (
            <>
              <FileText className="w-4 h-4" />
              <span>Generate Script</span>
            </>
          )}
        </button>
      </div>
    </div>
  );

  const renderScriptsList = () => (
    <div className="space-y-4">
      <h4 className="text-lg font-semibold text-gray-900">Generated Scripts</h4>
      
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent"></div>
          <span className="ml-3">Loading scripts...</span>
        </div>
      ) : generatedScripts.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No scripts generated yet</p>
          <p className="text-sm">Generate your first script using the form above</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {generatedScripts.map((script) => (
            <ScriptCard
              key={script.id}
              script={script}
              isSelected={selectedScriptId === script.id}
              isSwitching={isSwitching}
              onSelect={() => onChooseScript(script.id)}
              onUpdate={(updates) => onUpdateScript(script.id, updates)}
              onDelete={() => onDeleteScript(script.id)}
            />
          ))}
        </div>
      )}
    </div>
  );

  const renderScriptViewer = () => {
    if (!selectedScript) {
      return (
        <div className="text-center py-12 text-gray-500">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Select a script to view details</p>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-lg border">
        {/* Script Header */}
        <div className="p-6 border-b">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                {selectedScript.script_name || (selectedScript.script_style === 'cinematic_movie' ? 'Character Dialogue Script' : 'Narration Script')}
              </h3>
              <p className="text-gray-600">
                {selectedScript.script_style === 'cinematic_movie' ? 'Character Dialogue Script' : 'Narration Script'} • Story Type: {selectedScript.scriptStoryType || 'N/A'} • {chapterTitle} • {selectedScript.scenes?.length || 0} scenes •
                {selectedScript.characters?.length || 0} characters
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                selectedScript.status === 'approved' ? 'bg-green-100 text-green-800' :
                selectedScript.status === 'ready' ? 'bg-blue-100 text-blue-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {selectedScript.status}
              </span>
            </div>
          </div>

          {/* Script Navigation */}
          <div className="flex space-x-4">
            {['overview', 'acts', 'scenes', 'dialogue'].map((view) => (
              <button
                key={view}
                onClick={() => setActiveView(view as typeof activeView)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeView === view
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
                }`}
              >
                {view.charAt(0).toUpperCase() + view.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Script Content */}
        <div className="p-6">
          {activeView === 'overview' && renderScriptOverview(selectedScript)}
          {activeView === 'acts' && renderActsBreakdown(selectedScript)}
          {activeView === 'scenes' && renderScenesDetail(selectedScript)}
          {activeView === 'dialogue' && renderDialogueView(selectedScript)}
        </div>
      </div>
    );
  };

  const renderScriptOverview = (script: ChapterScript) => (
    <div className="space-y-6">
      {/* Script Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{script.acts?.length || 0}</div>
          <div className="text-sm text-gray-600">Acts</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{script.scenes?.length || script.scene_descriptions?.length || 0}</div>
          <div className="text-sm text-gray-600">Scenes</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{script.characters?.length || 0}</div>
          <div className="text-sm text-gray-600">Characters</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">
            {script.scenes?.reduce((total, scene) => total + scene.duration, 0) || 5}m
          </div>
          <div className="text-sm text-gray-600">Duration</div>
        </div>
      </div>

      {/* Characters */}
      {script.characters && script.characters.length > 0 && (
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">Characters</h4>
          <div className="flex flex-wrap gap-2">
            {script.characters.map((character, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
              >
                {character}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Script Preview */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-3">Script Preview</h4>
        <div className={`bg-gray-50 border rounded-lg p-4 overflow-y-auto ${showFullScript ? '' : 'max-h-96'}`}>
          {script.script && script.script.trim() ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
              {showFullScript ? script.script : script.script.substring(0, 1000) + (script.script.length > 1000 ? '...' : '')}
            </pre>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No script content available</p>
              <p className="text-xs mt-1">The script may still be generating or encountered an error.</p>
            </div>
          )}
        </div>
        {script.script && script.script.length > 1000 && (
          <button
            onClick={() => setShowFullScript(!showFullScript)}
            className="text-blue-600 hover:text-blue-800 text-sm mt-2 font-medium"
          >
            {showFullScript ? "Show Less" : "Show More"}
          </button>
        )}
      </div>
    </div>
  );

  const renderActsBreakdown = (script: ChapterScript) => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-gray-900">Acts Structure</h4>
      
      {script.acts && script.acts.length > 0 ? (
        <div className="space-y-4">
          {script.acts.map((act, idx) => (
            <div key={idx} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-lg font-medium text-gray-900">
                  Act {act.act_number}: {act.title}
                </h5>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>{act.duration}m</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Camera className="w-4 h-4" />
                    <span>{act.scenes} scenes</span>
                  </div>
                </div>
              </div>
              <p className="text-gray-700">{act.description}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <p>No acts structure available</p>
          <p className="text-sm">Acts will be generated automatically in future updates</p>
        </div>
      )}
    </div>
  );

  const renderScenesDetail = (script: ChapterScript) => (
    <div className="space-y-4">
      <h4 className="text-lg font-semibold text-gray-900">Scenes Breakdown</h4>
      
      {script.scene_descriptions && script.scene_descriptions.length > 0 ? (
        <div className="space-y-4">
          {script.scene_descriptions.map((scene, idx) => {
            if (typeof scene === 'object' && scene !== null) {
              return (
                <SceneDetailCard
                  key={idx}
                  scene={scene}
                  isExpanded={expandedScenes.has(scene.scene_number)}
                  onToggleExpand={() => toggleSceneExpansion(scene.scene_number)}
                />
              );
            } else {
              return (
                <div key={idx} className="border rounded-lg p-4 bg-gray-50">
                  <p className="text-gray-700">{typeof scene === 'string' ? scene : JSON.stringify(scene)}</p>
                </div>
              );
            }
          })}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <Camera className="mx-auto h-8 w-8 mb-2 opacity-50" />
          <p>No scenes available</p>
        </div>
      )}
    </div>
  );

  const renderDialogueView = (script: ChapterScript) => (
    <div className="space-y-4">
      <h4 className="text-lg font-semibold text-gray-900">Full Script</h4>

      <div className="bg-white border rounded-lg p-6">
        <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
          {script.script && script.script.trim() ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono leading-relaxed">
              {script.script}
            </pre>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No script content available</p>
              <p className="text-xs mt-1">The script may still be generating or encountered an error.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Script Generation</h3>
          <p className="text-gray-600">Create detailed scripts and scene breakdowns for {chapterTitle}</p>
        </div>
      </div>

      {/* Chapter Content */}
      <div className="bg-white rounded-lg border p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">{chapterTitle}</h4>
        <div className="prose max-w-none text-gray-700">
          <ChapterContent content={chapterContent} />
        </div>
      </div>

      {/* Script Generation Form */}
      {renderScriptGenerationForm()}

      {/* Scripts List */}
      {renderScriptsList()}

      {/* Selected Script Viewer */}
      {selectedScript && renderScriptViewer()}
    </div>
  );
};

// Script Card Component
interface ScriptCardProps {
  script: ChapterScript;
  isSelected: boolean;
  isSwitching: boolean;
  onSelect: () => void;
  onUpdate: (updates: Partial<ChapterScript>) => void;
  onDelete: () => void;
}

const ScriptCard: React.FC<ScriptCardProps> = ({ script, isSelected, isSwitching, onSelect, onDelete }) => {
  const [showActions, setShowActions] = useState(false);

  return (
    <div
      className={`border rounded-lg p-4 transition-all hover:shadow-md ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      } ${isSwitching ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
      onClick={!isSwitching ? onSelect : undefined}
      onMouseEnter={() => !isSwitching && setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">
            {script.script_name || (script.script_style === 'cinematic_movie' ? 'Character Dialogue' : 'Voice-over Narration')}
          </h4>
          <p className="text-sm text-gray-500">
            {script.script_style === 'cinematic_movie' ? 'Character Dialogue' : 'Voice-over Narration'} • Story Type: {script.scriptStoryType || 'N/A'} • Created: {new Date(script.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {isSelected && (
            <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
              Selected
            </span>
          )}
          {showActions && (
            <div className="flex space-x-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  // Edit functionality
                }}
                className="p-1 text-gray-400 hover:text-blue-600"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="p-1 text-gray-400 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm text-gray-600 mb-3">
        <div>
          <span className="font-medium">Scenes:</span> {script.scene_descriptions?.length || 0}
        </div>
        <div>
          <span className="font-medium">Characters:</span> {script.characters?.length || 0}
        </div>
        <div>
          <span className="font-medium">Length:</span> {script.script?.length || 0} chars
        </div>
      </div>

      {script.script && script.script.trim() ? (
        <div className="bg-gray-50 p-3 rounded text-sm">
          <p className="text-gray-700 line-clamp-3">
            {script.script.substring(0, 200)}...
          </p>
        </div>
      ) : (
        <div className="bg-gray-50 p-3 rounded text-sm text-center text-gray-500">
          <p className="text-xs">No preview available</p>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${
          script.status === 'approved' ? 'bg-green-100 text-green-800' :
          script.status === 'ready' ? 'bg-blue-100 text-blue-800' :
          'bg-yellow-100 text-yellow-800'
        }`}>
          {script.status}
        </span>

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isSwitching) onSelect();
          }}
          className={`text-blue-600 hover:text-blue-800 text-sm font-medium ${
            isSwitching ? 'cursor-not-allowed opacity-50' : ''
          }`}
          disabled={isSwitching}
        >
          View Details →
        </button>
      </div>
    </div>
  );
};

// Scene Detail Card Component
interface SceneDetailCardProps {
  scene: SceneDescription;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const SceneDetailCard: React.FC<SceneDetailCardProps> = ({
  scene,
  isExpanded,
  onToggleExpand,
}) => {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleExpand}
            className="text-gray-400 hover:text-gray-600"
          >
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>
          <h5 className="font-medium text-gray-900">
            Scene {scene.scene_number}: {scene.location}
          </h5>
        </div>
        <div className="flex items-center space-x-4 text-sm text-gray-600">
          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full">
            {scene.time_of_day}
          </span>
          <div className="flex items-center space-x-1">
            <Clock className="w-4 h-4" />
            <span>{scene.estimated_duration}s</span>
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-700 mb-3">{scene.visual_description}</p>

      {isExpanded && (
        <div className="space-y-3 pt-3 border-t">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Key Actions</label>
              <p className="text-sm text-gray-700">{scene.key_actions}</p>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Audio Requirements</label>
              <p className="text-sm text-gray-700">{scene.audio_requirements}</p>
            </div>
          </div>

          {scene.characters && scene.characters.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Characters</label>
              <div className="flex flex-wrap gap-1">
                {scene.characters.map((character, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs"
                  >
                    {character}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ScriptGenerationPanel;