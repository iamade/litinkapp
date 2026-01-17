import React, { useState, useEffect } from 'react';
import { FileText, Edit2, Trash2, Camera, ChevronDown, ChevronRight, AlertTriangle, Check, X, Box, MapPin, User, Activity } from 'lucide-react';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import CharacterDropdown, { PlotCharacter } from './CharacterDropdown';

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
  character_ids?: string[];  // UUIDs of linked plot characters
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
  plotOverview?: {
    id?: string;
    script_story_type?: string;
    story_type?: string;
    genre?: string;
    characters?: PlotCharacter[];  // Plot characters for linking
    logline?: string;
    original_prompt?: string;
  } | null;
  onCreatePlotCharacter?: (name: string, entityType?: 'character' | 'object' | 'location') => Promise<PlotCharacter>;  // Create placeholder in plot
}

interface ScriptGenerationOptions {
  includeCharacterProfiles: boolean;
  targetDuration?: number | "auto";
  sceneCount?: number;
  focusAreas: string[];
  scriptStoryType?: string; // Added property for script story type
  customLogline?: string;
}

const ScriptGenerationPanel: React.FC<ScriptGenerationPanelProps> = ({
  chapterTitle,
  chapterContent,
  generatedScripts,
  isLoading,
  isGeneratingScript,
  onGenerateScript,
  onUpdateScript,
  onDeleteScript,
  plotOverview,
  onCreatePlotCharacter
}) => {
  const {
    selectedScriptId,
    isSwitching,
    selectScript,
  } = useScriptSelection();

  const [scriptToDelete, setScriptToDelete] = useState<string | null>(null);
  
  // Character editing state
  const [editingCharacterIdx, setEditingCharacterIdx] = useState<number | null>(null);
  const [editingCharacterName, setEditingCharacterName] = useState('');

  const confirmDelete = () => {
    if (scriptToDelete) {
      onDeleteScript(scriptToDelete);
      setScriptToDelete(null);
    }
  };

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
  const [scriptStoryType, setScriptStoryType] = useState<string>(
    plotOverview?.script_story_type || plotOverview?.story_type || "hero's journey"
  );
  const [logline, setLogline] = useState<string>((plotOverview as any)?.creative_directive || plotOverview?.logline || plotOverview?.original_prompt || "");
  const [generationOptions, setGenerationOptions] = useState<ScriptGenerationOptions>({
    includeCharacterProfiles: true,
    targetDuration: "auto",
    sceneCount: 5,
    focusAreas: [],
    scriptStoryType: plotOverview?.script_story_type || plotOverview?.story_type || "hero's journey",
    customLogline: plotOverview?.logline || ""
  });

  // Update state when plotOverview changes
  useEffect(() => {
    if (plotOverview) {
      const initialLogline = plotOverview.original_prompt || plotOverview.logline;
      if (initialLogline && !logline) {
        setLogline(initialLogline);
        setGenerationOptions(prev => ({
          ...prev,
          customLogline: initialLogline
        }));
      }
    }
  }, [plotOverview]);

  // Update scriptStoryType when plotOverview changes
  useEffect(() => {
    if (plotOverview?.script_story_type || plotOverview?.story_type) {
      const storyType = plotOverview.script_story_type || plotOverview.story_type || "hero's journey";
      setScriptStoryType(storyType);
      setGenerationOptions(prev => ({
        ...prev,
        scriptStoryType: storyType
      }));
    }
  }, [plotOverview?.script_story_type, plotOverview?.story_type]);
  const [activeView, setActiveView] = useState<'overview' | 'acts' | 'scenes' | 'dialogue' | 'performance'>('overview');
  const [showFullScript, setShowFullScript] = useState(false);
  const [isAddingCharacter, setIsAddingCharacter] = useState(false);
  const [newCharacterName, setNewCharacterName] = useState('');

  const handleGenerateScript = () => {
    onGenerateScript(scriptStyle, {
      ...generationOptions,
      scriptStoryType: scriptStoryType,
      customLogline: logline
    });
  };

  const ChapterContent: React.FC<{ content: string }> = ({ content }) => {
    const maxChars = 500;
    const [showFull, setShowFull] = useState(false);
    
    if (content.length <= maxChars) {
      return <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
          {showFull ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFull(!showFull)}
          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm mt-2 font-medium"
        >
          {showFull ? "Show Less" : "Show More"}
        </button>
      </div>
    );
  };

  const renderScriptGenerationForm = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Generate New Script</h4>
        <button
          onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
          className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <span>Advanced Options</span>
          {showAdvancedOptions ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Basic Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Script Style</label>
          <select
            value={scriptStyle}
            onChange={(e) => setScriptStyle(e.target.value as 'cinematic_movie' | 'cinematic_narration')}
            className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="cinematic_movie">Character Dialogue</option>
            <option value="cinematic_narration">Voice-over Narration</option>
          </select>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {scriptStyle === 'cinematic_movie' 
              ? 'Interactive dialogue between characters' 
              : 'Narrative voice-over storytelling'}
          </p>
        </div>
        {/* Original User Prompt - Reference (read-only) */}
        {plotOverview?.original_prompt && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Original User Prompt <span className="text-xs text-gray-500">(Reference)</span>
            </label>
            <div className="bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
              {plotOverview.original_prompt}
            </div>
          </div>
        )}

        {/* Story Logline - Reference (read-only) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Story Logline <span className="text-xs text-gray-500">(Reference)</span>
          </label>
          <div className="bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
            {plotOverview?.logline || 'Not yet generated'}
          </div>
        </div>

 {/* Creative Directive / Style Guide - Editable */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Creative Directive / Style Guide
            <span className="text-xs text-blue-600 dark:text-blue-400 ml-2">(Used for script generation)</span>
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            This combines your prompt and logline. Edit to customize the creative direction for this script.
          </p>
          <textarea
            value={logline}
            onChange={(e) => {
              setLogline(e.target.value);
              setGenerationOptions(prev => ({
                ...prev,
                customLogline: e.target.value
              }));
            }}
            placeholder="Combined creative direction for this script..."
            className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent min-h-[100px] resize-y"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Script Story Type
            {plotOverview && (
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">(from plot overview)</span>
            )}
          </label>
          <input
            type="text"
            value={scriptStoryType}
            onChange={(e) => {
              setScriptStoryType(e.target.value);
              setGenerationOptions(prev => ({
                ...prev,
                scriptStoryType: e.target.value
              }));
            }}
            placeholder="e.g., hero's journey, mystery thriller, underdog story"
            className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-500 dark:placeholder-gray-400"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Narrative framework for the script
          </p>
          

        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Target Duration</label>
          <select
            value={generationOptions.targetDuration || "auto"}
            onChange={(e) => setGenerationOptions(prev => ({
              ...prev,
              targetDuration: e.target.value === "auto" ? "auto" : parseInt(e.target.value) || "auto"
            }))}
            className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="auto">Auto (Full Story)</option>
            <option value="3">3 minutes</option>
            <option value="5">5 minutes</option>
            <option value="10">10 minutes</option>
            <option value="15">15 minutes</option>
            <option value="20">20 minutes</option>
            <option value="30">30 minutes</option>
          </select>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {generationOptions.targetDuration === "auto"
              ? "Automatically determine duration based on content length"
              : `${generationOptions.targetDuration} minute target duration`}
          </p>
        </div>
      </div>


      {/* Advanced Options */}
      {showAdvancedOptions && (
        <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Scene Count</label>
              <input
                type="number"
                min="3"
                max="15"
                value={generationOptions.sceneCount || 5}
                onChange={(e) => setGenerationOptions(prev => ({ 
                  ...prev, 
                  sceneCount: parseInt(e.target.value) || 5 
                }))}
                className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="includeCharacterProfiles" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Include Character Profiles
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Focus Areas</label>
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
                      ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Generated Scripts</h4>
          {generatedScripts.length > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded-full">
              {generatedScripts.length}
            </span>
          )}
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent"></div>
          <span className="ml-3 text-gray-700 dark:text-gray-300">Loading scripts...</span>
        </div>
      ) : generatedScripts.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No scripts generated yet</p>
          <p className="text-sm">Generate your first script using the form above</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Horizontal Script Cards */}
          <div className="flex gap-4 overflow-x-auto pb-3 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
            {generatedScripts.map((script) => {
              const isSelected = selectedScriptId === script.id;
              
              return (
                <ScriptCard
                  key={script.id}
                  script={script}
                  isSelected={isSelected}
                  isSwitching={isGeneratingScript || isSwitching}
                  onSelect={() => onChooseScript(script.id)}
                  onDelete={() => setScriptToDelete(script.id)}
                  onUpdate={(updates) => onUpdateScript(script.id, updates)}
                  className="flex-shrink-0 min-w-[280px] max-w-[320px]"
                  showPreview={false}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );

  const renderScriptViewer = () => {
    if (!selectedScript) {
      return (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Select a script to view details</p>
        </div>
      );
    }

    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        {/* Script Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                {selectedScript.script_name || (selectedScript.script_style === 'cinematic_movie' ? 'Character Dialogue Script' : 'Narration Script')}
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                {selectedScript.script_style === 'cinematic_movie' ? 'Character Dialogue Script' : 'Narration Script'} • Story Type: {selectedScript.scriptStoryType || 'N/A'} • {chapterTitle} • {selectedScript.scenes?.length || 0} scenes •
                {selectedScript.characters?.length || 0} characters
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                selectedScript.status === 'approved' ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300' :
                selectedScript.status === 'ready' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300' :
                'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300'
              }`}>
                {selectedScript.status}
              </span>
            </div>
          </div>

          {/* Script Navigation */}
          <div className="flex space-x-4">
            {['overview', 'acts', 'scenes', 'dialogue', 'performance'].map((view) => (
              <button
                key={view}
                onClick={() => setActiveView(view as typeof activeView)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeView === view
                    ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {view === 'performance' ? (
                  <div className="flex items-center space-x-1">
                    <Activity className="w-3 h-3" />
                    <span>Map</span>
                  </div>
                ) : (
                  view.charAt(0).toUpperCase() + view.slice(1)
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Script Content */}
        <div className="p-6">
          {activeView === 'overview' && renderScriptOverview(selectedScript)}
          {activeView === 'acts' && renderActsBreakdown(selectedScript)}
          {activeView === 'scenes' && renderScenesDetail(selectedScript)}
          {activeView === 'scenes' && renderScenesDetail(selectedScript)}
          {activeView === 'dialogue' && renderDialogueView(selectedScript)}
          {activeView === 'performance' && renderPerformanceMap(selectedScript)}
        </div>
      </div>
    );
  };

  // Helper function to count acts from script text
  const countActsFromScript = (script: ChapterScript): number => {
    if (script.acts && script.acts.length > 0) return script.acts.length;
    // Count unique ACT headers from script text
    const scriptText = script.script || '';
    const actMatches = scriptText.match(/\*?\*?ACT\s+[IVX]+\*?\*?(?:\s|$)/gi);
    if (actMatches) {
      // Get unique acts (case insensitive)
      const uniqueActs = new Set(actMatches.map(a => a.toUpperCase().replace(/\*/g, '').trim()));
      return uniqueActs.size;
    }
    return 0;
  };

  // Helper function to count scenes from script text
  const countScenesFromScript = (script: ChapterScript): number => {
    if (script.scenes && script.scenes.length > 0) return script.scenes.length;
    // Count SCENE headers from script text (more reliable than scene_descriptions which may have duplicates)
    const scriptText = script.script || '';
    const sceneMatches = scriptText.match(/\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+\d+\*?\*?/gi);
    if (sceneMatches) {
      return sceneMatches.length;
    }
    // Fallback to scene_descriptions if no matches in script text
    if (script.scene_descriptions && script.scene_descriptions.length > 0) {
      // Filter out duplicates - only count entries that start with ACT header
      const actScenes = script.scene_descriptions.filter((desc: any) => {
        const text = typeof desc === 'string' ? desc : desc?.visual_description || '';
        return text.match(/^\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE/i);
      });
      return actScenes.length > 0 ? actScenes.length : Math.ceil(script.scene_descriptions.length / 2);
    }
    return 0;
  };

  const renderScriptOverview = (script: ChapterScript) => {
    const actCount = countActsFromScript(script);
    const sceneCount = countScenesFromScript(script);

    return (
    <div className="space-y-6">
      {/* Script Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{actCount}</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">Acts</div>
        </div>
        <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{sceneCount}</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">Scenes</div>
        </div>
        <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{script.characters?.length || 0}</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">Characters</div>
        </div>
        <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {script.scenes?.reduce((total, scene) => total + scene.duration, 0) || 5}m
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">Duration</div>
        </div>
      </div>

      {/* Characters */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Characters</h4>
            <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full text-gray-600 dark:text-gray-400">
              {script.characters?.length || 0}
            </span>
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Click to link with Plot Overview • ✓ = linked • ⚠ = not linked
          </span>
        </div>

        
        {(() => {
           // Helper to process entities with their original checks
           const entities = (script.characters || []).map((name, idx) => {
             const linkedCharacterId = script.character_ids?.[idx];
             const linkedPlotChar = linkedCharacterId 
                 ? plotOverview?.characters?.find(c => c.id === linkedCharacterId)
                 : null;
             return { name, idx, linkedPlotChar, linkedCharacterId };
           });

           const objectsLocations = entities.filter(e => e.linkedPlotChar && (e.linkedPlotChar.entity_type === 'object' || e.linkedPlotChar.entity_type === 'location'));
           // Everything else goes to characters (unlinked ones are assumed characters until linked otherwise)
           const characters = entities.filter(e => !e.linkedPlotChar || (e.linkedPlotChar.entity_type !== 'object' && e.linkedPlotChar.entity_type !== 'location'));

           const renderEntityPill = (entity: typeof entities[0]) => {
              const { name, idx, linkedPlotChar, linkedCharacterId } = entity;
              const isLinked = !!linkedPlotChar;
              
              return editingCharacterIdx === idx ? (
                  <CharacterDropdown
                    key={idx}
                    value={editingCharacterName}
                    plotCharacters={plotOverview?.characters || []}
                    linkedCharacterId={linkedCharacterId}
                    onSelect={(plotChar) => {
                      if (selectedScript) {
                        const newCharacters = [...script.characters];
                        newCharacters[idx] = plotChar.name;
                        
                        const newCharacterIds = [...(script.character_ids || [])];
                        while (newCharacterIds.length <= idx) newCharacterIds.push('');
                        newCharacterIds[idx] = plotChar.id;
                        
                        onUpdateScript(selectedScript.id, { 
                          characters: newCharacters,
                          character_ids: newCharacterIds
                        });
                      }
                      setEditingCharacterIdx(null);
                      setEditingCharacterName('');
                    }}
                    onCreateNew={async (name, entityType = 'character') => {
                      if (onCreatePlotCharacter && selectedScript) {
                          try {
                            const newChar = await onCreatePlotCharacter(name, entityType);
                            const newCharacters = [...script.characters];
                            newCharacters[idx] = newChar.name;
                            
                            const newCharacterIds = [...(script.character_ids || [])];
                            while (newCharacterIds.length <= idx) newCharacterIds.push('');
                            newCharacterIds[idx] = newChar.id;
                            
                            onUpdateScript(selectedScript.id, { 
                              characters: newCharacters,
                              character_ids: newCharacterIds
                            });
                          } catch (error) {
                            console.error('Failed to create character:', error);
                          }
                      }
                      setEditingCharacterIdx(null);
                      setEditingCharacterName('');
                    }}
                    onCancel={() => {
                      setEditingCharacterIdx(null);
                      setEditingCharacterName('');
                    }}
                  />
                ) : (
                  <span
                    key={idx}
                    className={`group inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                      isLinked 
                        ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300'
                        : 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300'
                    }`}
                  >
                    <span className="text-xs mr-1">
                      {isLinked ? '✓' : '⚠'}
                    </span>
                    
                    <span
                      onClick={() => {
                        setEditingCharacterIdx(idx);
                        setEditingCharacterName(name);
                      }}
                      title={isLinked ? `Linked to: ${linkedPlotChar?.name}` : 'Click to link with Plot Overview'}
                      className="cursor-pointer hover:underline flex items-center gap-1"
                    >
                      {/* Icon based on type if linked */}
                      {linkedPlotChar?.entity_type === 'location' && <MapPin className="w-3 h-3" />}
                      {linkedPlotChar?.entity_type === 'object' && <Box className="w-3 h-3" />}
                      {!linkedPlotChar?.entity_type && <User className="w-3 h-3 opacity-50" />}
                      {name}
                    </span>
                    
                    {linkedPlotChar?.image_url && (
                      <img 
                        src={linkedPlotChar.image_url} 
                        alt={linkedPlotChar.name}
                        className="w-5 h-5 rounded-full object-cover ml-1"
                      />
                    )}
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (selectedScript) {
                          const newCharacters = script.characters.filter((_, i) => i !== idx);
                          const newCharacterIds = (script.character_ids || []).filter((_, i) => i !== idx);
                          onUpdateScript(selectedScript.id, {
                            characters: newCharacters,
                            character_ids: newCharacterIds
                          });
                        }
                      }}
                      className="ml-1 p-0.5 rounded-full hover:bg-red-200 dark:hover:bg-red-800/50 text-gray-500 hover:text-red-600 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Remove from script"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </span>
                );
           };

           return (
             <div className="space-y-4">
               {/* Character List */}
               <div className="flex flex-wrap gap-2">
                 {characters.map(renderEntityPill)}
               </div>

               {/* Object/Location List */}
               {objectsLocations.length > 0 && (
                 <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                       <Box className="w-4 h-4" /> Objects & Locations
                    </h5>
                    <div className="flex flex-wrap gap-2">
                       {objectsLocations.map(renderEntityPill)}
                    </div>
                 </div>
               )}
             </div>
           );
        })()}
          
          {/* Add Character Button/Input - Keeps existing logic but visually separated */}
          
          {/* Add Character Button/Input */}
          {isAddingCharacter ? (
            <div className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/50 rounded-full">
              <input
                type="text"
                value={newCharacterName}
                onChange={(e) => setNewCharacterName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newCharacterName.trim() && selectedScript) {
                    const newCharacters = [...(script.characters || []), newCharacterName.trim()];
                    onUpdateScript(selectedScript.id, { characters: newCharacters });
                    setNewCharacterName('');
                    setIsAddingCharacter(false);
                  } else if (e.key === 'Escape') {
                    setNewCharacterName('');
                    setIsAddingCharacter(false);
                  }
                }}
                placeholder="Character name..."
                className="w-32 px-2 py-0.5 text-sm bg-transparent border-none focus:outline-none text-blue-800 dark:text-blue-300 placeholder-blue-400 dark:placeholder-blue-500"
                autoFocus
              />
              <button
                onClick={() => {
                  if (newCharacterName.trim() && selectedScript) {
                    const newCharacters = [...(script.characters || []), newCharacterName.trim()];
                    onUpdateScript(selectedScript.id, { characters: newCharacters });
                    setNewCharacterName('');
                    setIsAddingCharacter(false);
                  }
                }}
                disabled={!newCharacterName.trim()}
                className="p-0.5 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 disabled:opacity-50"
                title="Add character"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <button
                onClick={() => {
                  setNewCharacterName('');
                  setIsAddingCharacter(false);
                }}
                className="p-0.5 text-gray-500 hover:text-red-600 dark:hover:text-red-400"
                title="Cancel"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsAddingCharacter(true)}
              className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title="Add a character manually"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add
            </button>
          )}
      </div>

      {/* Script Preview */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Script Preview</h4>
        <div className={`bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 overflow-y-auto ${showFullScript ? '' : 'max-h-96'}`}>
          {script.script && script.script.trim() ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300 font-mono">
              {showFullScript ? script.script : script.script.substring(0, 1000) + (script.script.length > 1000 ? '...' : '')}
            </pre>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No script content available</p>
              <p className="text-xs mt-1">The script may still be generating or encountered an error.</p>
            </div>
          )}
        </div>
        {script.script && script.script.length > 1000 && (
          <button
            onClick={() => setShowFullScript(!showFullScript)}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm mt-2 font-medium"
          >
            {showFullScript ? "Show Less" : "Show More"}
          </button>
        )}
      </div>
    </div>
  );
  };

  const renderActsBreakdown = (script: ChapterScript) => {
    // Parse acts from script text if not provided as structured data
    const parseActsFromScript = (): { act_number: string; title: string; scenes: string[]; content: string }[] => {
      if (script.acts && script.acts.length > 0) {
        return script.acts.map(act => ({
          act_number: String(act.act_number),
          title: act.title || '',
          scenes: act.scenes?.map(String) || [],
          content: act.description || ''
        }));
      }

      const scriptText = script.script || '';
      const acts: { act_number: string; title: string; scenes: string[]; content: string }[] = [];
      
      // Split by ACT markers
      const actPattern = /\*?\*?ACT\s+([IVX]+)\*?\*?/gi;
      const matches = [...scriptText.matchAll(actPattern)];
      
      if (matches.length === 0) return [];

      matches.forEach((match, idx) => {
        const actNum = match[1];
        const startIdx = match.index! + match[0].length;
        const endIdx = idx < matches.length - 1 ? matches[idx + 1].index! : scriptText.length;
        const actContent = scriptText.substring(startIdx, endIdx).trim();
        
        // Count scenes in this act
        const sceneMatches = actContent.match(/\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+\d+\*?\*?/gi) || [];
        
        acts.push({
          act_number: actNum,
          title: `Act ${actNum}`,
          scenes: sceneMatches.map((_, i) => String(i + 1)),
          content: actContent.substring(0, 200) + (actContent.length > 200 ? '...' : '')
        });
      });

      return acts;
    };

    const parsedActs = parseActsFromScript();

    return (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Acts Structure</h4>
      
      {parsedActs.length > 0 ? (
        <div className="space-y-4">
          {parsedActs.map((act, idx) => (
            <div key={idx} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-lg font-medium text-gray-900 dark:text-white">
                  {act.title}
                </h5>
                <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center space-x-1">
                    <Camera className="w-4 h-4" />
                    <span>{act.scenes.length} scenes</span>
                  </div>
                </div>
              </div>
              <p className="text-gray-700 dark:text-gray-300 text-sm">{act.content}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>No acts structure available</p>
          <p className="text-sm">Acts will be generated automatically in future updates</p>
        </div>
      )}
    </div>
  );
  };

  const renderScenesDetail = (script: ChapterScript) => {
    // Parse scenes from script text
    const parseScenesFromScript = (): { scene_number: number; header: string; location: string; content: string }[] => {
      const scriptText = script.script || '';
      const scenes: { scene_number: number; header: string; location: string; content: string }[] = [];
      
      // Find all ACT-SCENE headers
      const scenePattern = /(\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+\d+\*?\*?)/gi;
      const matches = [...scriptText.matchAll(scenePattern)];
      
      if (matches.length === 0) {
        // Fallback to scene_descriptions if available
        if (script.scene_descriptions && script.scene_descriptions.length > 0) {
          return script.scene_descriptions
            .filter((desc: any, idx: number) => {
              // Only include non-duplicate entries (filter out location-only entries)
              const text = typeof desc === 'string' ? desc : '';
              return text.match(/^\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE/i) || idx % 2 === 0;
            })
            .map((desc: any, idx: number) => ({
              scene_number: idx + 1,
              header: `Scene ${idx + 1}`,
              location: '',
              content: typeof desc === 'string' ? desc : (desc?.visual_description || JSON.stringify(desc))
            }));
        }
        return [];
      }

      matches.forEach((match, idx) => {
        const startIdx = match.index!;
        const endIdx = idx < matches.length - 1 ? matches[idx + 1].index! : scriptText.length;
        const sceneContent = scriptText.substring(startIdx, endIdx).trim();
        
        // Extract location (INT./EXT. line)
        const locationMatch = sceneContent.match(/(?:INT\.|EXT\.)[^\n]+/i);
        const location = locationMatch ? locationMatch[0] : '';
        
        // Get first few lines of content (excluding header and location)
        const lines = sceneContent.split('\n').slice(1, 6);
        const contentLines = lines.filter(l => l.trim() && !l.trim().match(/^(?:INT\.|EXT\.)/i));
        const content = contentLines.join(' ').substring(0, 300);
        
        scenes.push({
          scene_number: idx + 1,
          header: match[0].replace(/\*/g, '').trim(),
          location: location,
          content: content + (content.length >= 300 ? '...' : '')
        });
      });

      return scenes;
    };

    const parsedScenes = parseScenesFromScript();

    return (
    <div className="space-y-4">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Scenes Breakdown</h4>
      
      {parsedScenes.length > 0 ? (
        <div className="space-y-4">
          {parsedScenes.map((scene, idx) => (
            <div key={idx} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-medium text-gray-900 dark:text-white">{scene.header}</h5>
                {scene.location && (
                  <span className="text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded">
                    {scene.location}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">{scene.content}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Camera className="mx-auto h-8 w-8 mb-2 opacity-50" />
          <p>No scenes available</p>
        </div>
      )}
    </div>
  );
  };

  const renderDialogueView = (script: ChapterScript) => (
    <div className="space-y-4">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Full Script</h4>

      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
        <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg max-h-96 overflow-y-auto">
          {script.script && script.script.trim() ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed">
              {script.script}
            </pre>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No script content available</p>
              <p className="text-xs mt-1">The script may still be generating or encountered an error.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderPerformanceMap = (script: ChapterScript) => {
    // 1. Parsing logic (duplicated for isolation)
    const scriptText = script.script || '';
    // Match basic scene headers
    const scenePattern = /(\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+(\d+(?:\.\d+)?)\*?\*?)/gi;
    const matches = [...scriptText.matchAll(scenePattern)];
    
    // Fallback if no text but we have scene definitions
    let displayScenes: { number: number; label: string; energy: number; description: string }[] = [];
    
    // Heuristic for Energy
    const calculateEnergy = (text: string) => {
        let score = 5; // Neutral baseline
        const high = ['shout', 'scream', 'yell', 'attack', 'run', 'fight', 'explosion', 'urgent', 'anger', 'furious', 'fast', 'quick', 'loud', 'argue', 'chase'];
        const low = ['whisper', 'cry', 'sob', 'sad', 'slow', 'quiet', 'calm', 'wait', 'pause', 'silence', 'sleep', 'dream', 'solitary'];
        
        const lower = text.toLowerCase();
        high.forEach(w => { if (lower.includes(w)) score += 1; });
        low.forEach(w => { if (lower.includes(w)) score -= 1; });
        return Math.max(1, Math.min(10, score));
    };

    if (matches.length > 0) {
        displayScenes = matches.map((match, idx) => {
            const startIdx = match.index!;
            const endIdx = idx < matches.length - 1 ? matches[idx + 1].index! : scriptText.length;
            const content = scriptText.substring(startIdx, endIdx);
            const energy = calculateEnergy(content);
            return {
                number: idx + 1,
                label: `Scene ${idx + 1}`,
                energy,
                description: content.substring(0, 100) + '...'
            };
        });
    } else if (script.scenes && script.scenes.length > 0) {
        displayScenes = script.scenes.map((s, idx) => ({
            number: s.scene_number || idx + 1,
            label: `Scene ${s.scene_number || idx + 1}`,
            energy: calculateEnergy(s.visual_description + ' ' + s.action + ' ' + s.dialogue),
            description: s.visual_description.substring(0, 100) + '...'
        }));
    } else if (script.scene_descriptions && script.scene_descriptions.length > 0) {
        displayScenes = script.scene_descriptions.map((s: any, idx) => ({
            number: s.scene_number || idx + 1,
            label: `Scene ${s.scene_number || idx + 1}`,
            energy: calculateEnergy(typeof s === 'string' ? s : s.visual_description || ''),
            description: (typeof s === 'string' ? s : s.visual_description || '').substring(0, 100) + '...'
        }));
    }

    if (displayScenes.length === 0) {
        return (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Activity className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>No scene data available for analysis</p>
            </div>
        );
    }

    // SVG Chart

    const points = displayScenes.map((s, i) => {
        const x = (i / (displayScenes.length - 1 || 1)) * 100;
        const y = 100 - (s.energy * 10); // Map 0-10 to 100-0%
        return `${x},${y}`;
    }).join(' ');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                   <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Emotional Performance Map</h4>
                   <p className="text-sm text-gray-600 dark:text-gray-400">Visualizing narrative energy across {displayScenes.length} scenes</p>
                </div>
            </div>

            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <div className="h-[250px] w-full relative">
                    {/* Y-Axis Labels */}
                    <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-xs text-gray-400">
                        <span>High</span>
                        <span>Neutral</span>
                        <span>Low</span>
                    </div>

                    {/* Chart Area */}
                    <div className="absolute left-12 right-0 top-4 bottom-8 border-l border-b border-gray-200 dark:border-gray-700">
                         {/* SVG Line */}
                         <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                            {/* Grid lines */}
                            <line x1="0" y1="50" x2="100" y2="50" stroke="currentColor" strokeOpacity="0.1" strokeDasharray="4" />
                            
                            {/* Path */}
                            <polyline 
                                points={points} 
                                fill="none" 
                                stroke="#8b5cf6" 
                                strokeWidth="3" // Increased visibility
                                vectorEffect="non-scaling-stroke"
                            />
                            
                            {/* Points */}
                            {displayScenes.map((s, i) => (
                                <circle
                                    key={i}
                                    cx={(i / (displayScenes.length - 1 || 1)) * 100}
                                    cy={100 - (s.energy * 10)}
                                    r="1.5"
                                    fill="white"
                                    stroke="#8b5cf6"
                                    strokeWidth="0.5" // Adjust relative to viewbox
                                    vectorEffect="non-scaling-stroke" // Keep uniform size
                                    className="hover:r-2 transition-all cursor-pointer"
                                >
                                    <title>{s.label}: Energy {s.energy}/10</title>
                                </circle>
                            ))}
                         </svg>
                    </div>

                     {/* X-Axis Labels */}
                    <div className="absolute left-12 right-0 bottom-0 flex justify-between text-xs text-gray-400 pt-2">
                        <span>Start</span>
                        <span>End</span>
                    </div>
                </div>
            </div>

            {/* Key Moments */}
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {displayScenes.filter(s => s.energy >= 7 || s.energy <= 3).map((scene, idx) => (
                    <div key={idx} className={`p-4 rounded-lg border ${
                        scene.energy >= 7 
                        ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800' 
                        : 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800'
                    }`}>
                        <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-gray-900 dark:text-white">{scene.label}</span>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                                scene.energy >= 7 ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                            }`}>
                                {scene.energy >= 7 ? 'High Energy' : 'Introspective'}
                            </span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                            {scene.description}
                        </p>
                    </div>
                ))}
             </div>
        </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Script Generation</h3>
          <p className="text-gray-600 dark:text-gray-400">Create detailed scripts and scene breakdowns for {chapterTitle}</p>
        </div>
      </div>

      {/* Chapter Content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{chapterTitle}</h4>
        <div className="prose max-w-none text-gray-700 dark:text-gray-300">
          <ChapterContent content={chapterContent} />
        </div>
      </div>

      {/* Script Generation Form */}
      {renderScriptGenerationForm()}

      {/* Scripts List */}
      {renderScriptsList()}

      {/* Selected Script Viewer */}
      {selectedScript && renderScriptViewer()}

      {/* Delete Confirmation Modal */}
      {scriptToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 border border-gray-200 dark:border-gray-700 transform transition-all scale-100">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Delete Script?</h3>
            </div>
            
            <p className="text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
              Are you sure you want to delete this script? This action cannot be undone.
            </p>
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setScriptToDelete(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium shadow-sm transition-colors flex items-center gap-2"
              >
                <Trash2 size={18} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Script Card Component
interface ScriptCardProps {
  script: ChapterScript;
  isSelected?: boolean;
  isSwitching?: boolean;
  onSelect?: () => void;
  onUpdate: (updates: Partial<ChapterScript>) => void;
  onDelete: () => void;
  className?: string;
  showPreview?: boolean;
}

const ScriptCard: React.FC<ScriptCardProps> = ({ 
  script, 
  isSelected, 
  isSwitching, 
  onSelect, 
  onDelete, 
  onUpdate,
  className = '',
  showPreview = true
}) => {
  const [showActions, setShowActions] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [tempName, setTempName] = useState(script.script_name || "");

  useEffect(() => {
    // Sync tempName with prop and handle defaults
    const defaultName = script.script_style?.includes('cinematic') ? 'Character Dialogue' : 'Voice-over Narration';
    setTempName(script.script_name || defaultName);
  }, [script.script_name, script.script_style]);

  const handleSaveName = (e?: React.FormEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (tempName.trim()) {
      onUpdate({ script_name: tempName });
      setIsEditingName(false);
    }
  };

  // Count scenes from script text
  const getSceneCount = (): number => {
    const scriptText = script.script || '';
    const sceneMatches = scriptText.match(/\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+\d+\*?\*?/gi);
    if (sceneMatches && sceneMatches.length > 0) {
      return sceneMatches.length;
    }
    // Fallback
    return script.scene_descriptions ? Math.ceil(script.scene_descriptions.length / 2) : 0;
  };

  return (
    <div
      className={`relative border rounded-lg p-4 transition-all hover:shadow-md ${
        isSelected ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
      } ${isSwitching ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${className}`}
      onClick={!isSwitching ? onSelect : undefined}
      onMouseEnter={() => !isSwitching && setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          {isEditingName ? (
            <form onSubmit={handleSaveName} onClick={e => e.stopPropagation()} className="flex items-center gap-1 mb-1">
              <input
                type="text"
                value={tempName}
                onChange={e => setTempName(e.target.value)}
                className="flex-1 min-w-[200px] border rounded px-2 py-1 text-sm dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                autoFocus
                onKeyDown={e => { if(e.key === 'Escape') { setIsEditingName(false); e.stopPropagation(); } }}
              />
              <button type="submit" className="p-1 hover:bg-green-100 rounded text-green-600 dark:hover:bg-green-900/30"><Check size={16}/></button>
              <button type="button" onClick={() => setIsEditingName(false)} className="p-1 hover:bg-red-100 rounded text-red-600 dark:hover:bg-red-900/30"><X size={16}/></button>
            </form>
          ) : (
            <h4 className="font-semibold text-gray-900 dark:text-white group flex items-center gap-2">
              {script.script_name || (script.script_style?.includes('cinematic') ? 'Character Dialogue' : 'Voice-over Narration')}
            </h4>
          )}
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {script.script_style === 'cinematic' || script.script_style === 'cinematic_movie' ? 'Character Dialogue' : 'Voice-over Narration'} • Story Type: {(script as any).script_story_type || 'N/A'} • Created: {new Date(script.created_at).toLocaleDateString()}
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
                    const defaultName = script.script_style?.includes('cinematic') ? 'Character Dialogue' : 'Voice-over Narration';
                    setTempName(script.script_name || defaultName);
                    setIsEditingName(true);
                  }}
                className="p-1 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="p-1 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400 mb-3">
        <div>
          <span className="font-medium">Scenes:</span> {getSceneCount()}
        </div>
        <div>
          <span className="font-medium">Characters:</span> {script.characters?.length || 0}
        </div>
        <div>
          <span className="font-medium">Length:</span> {script.script?.length || 0} chars
        </div>
      </div>



      {showPreview && (script.script && script.script.trim() ? (
        <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded text-sm">
          <p className="text-gray-700 dark:text-gray-300 line-clamp-3">
            {script.script.substring(0, 200)}...
          </p>
        </div>
      ) : (
        <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded text-sm text-center text-gray-500 dark:text-gray-400">
          <p className="text-xs">No preview available</p>
        </div>
      ))}

      <div className="mt-3 flex items-center justify-between">
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${
          script.status === 'approved' ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300' :
          script.status === 'ready' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300' :
          'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300'
        }`}>
          {script.status}
        </span>

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isSwitching) onSelect?.();
          }}
          className={`text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium ${
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

// Scene Detail Card Component removed as it was unused
export default ScriptGenerationPanel;