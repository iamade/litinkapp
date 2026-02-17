import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { projectService, Project } from "../services/projectService";
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";
import { 
  ArrowLeft, 
  FileText, 
  Settings, 
  MoreVertical, 
  Play, 
  BookOpen, 
  Clock,
  ExternalLink,
  Image,
  Music,
  Video,
  ChevronLeft,
  ChevronRight,
  Edit2,
  Check,
  X
} from "lucide-react";

// Import generation panels
import PlotOverviewPanel from '../components/Plot/PlotOverviewPanel';
import ProjectPlotPanel from '../components/Plot/ProjectPlotPanel';
import ScriptGenerationPanel from '../components/Script/ScriptGenerationPanel';
import ImagesPanel from '../components/Images/ImagesPanel';
import AudioPanel from '../components/Audio/AudioPanel';
import VideoProductionPanel from '../components/Video/VideoProductionPanel';
import ConsultationPanel from '../components/Consultation/ConsultationPanel';

// Import hooks
import { usePlotGeneration } from '../hooks/usePlotGeneration';
import { useScriptGeneration } from '../hooks/useScriptGeneration';
import { useImageGeneration } from '../hooks/useImageGeneration';
import { useAudioGeneration } from '../hooks/useAudioGeneration';
import { useScriptSelection } from '../contexts/ScriptSelectionContext';
import { useStoryboardOptional } from '../contexts/StoryboardContext';
import { useAuth } from '../contexts/AuthContext';
import { videoGenerationAPI } from '../lib/videoGenerationApi';
import { useVideoGenerationStatus } from '../hooks/useVideoGenerationStatus';

// Types
interface ChapterArtifact {
  id: string;
  artifact_type: string;
  content: {
    title: string;
    content: string;
    chapter_number: number;
    summary?: string;
    chapter_id?: string;  // Actual chapter ID from books.chapters table
  };
  version: number;
  project_id: string;
  // Cinematic Universe fields
  content_type_label?: string;  // Film, Episode, Part, etc.
  script_order?: number;        // Order in the cinematic universe sequence
  is_script?: boolean;          // True if this is an uploaded script
}

// Helper to get dynamic label for chapters/scripts
const getDynamicLabel = (artifact: ChapterArtifact, index: number): { label: string; plural: string } => {
  const label = artifact.content_type_label || 'Chapter';
  const number = artifact.script_order || artifact.content.chapter_number || index + 1;
  
  // Map labels to plurals
  const pluralMap: Record<string, string> = {
    'Film': 'Films',
    'Episode': 'Episodes', 
    'Part': 'Parts',
    'Chapter': 'Chapters',
    'Script': 'Scripts',
  };
  
  return {
    label: `${label} ${number}`,
    plural: pluralMap[label] || `${label}s`
  };
};

// Helper to get the actual chapter ID for API calls
// For uploaded books, content.chapter_id contains the real chapter table ID
// For prompt-only projects, we use the artifact/project ID
const getActualChapterId = (chapter: ChapterArtifact | null): string => {
  if (!chapter) return '';
  // Prefer content.chapter_id (actual Chapter table ID) if available
  return chapter.content?.chapter_id || chapter.id;
};

interface WorkflowProgress {
  consultation?: "idle" | "generating" | "completed" | "error";
  plot: "idle" | "generating" | "completed" | "error";
  script: "idle" | "generating" | "completed" | "error";
  images: "idle" | "generating" | "completed" | "error";
  audio: "idle" | "generating" | "completed" | "error";
  video: "idle" | "generating" | "completed" | "error";
}

type WorkflowTab = "consultation" | "plot" | "script" | "images" | "audio" | "video";

interface ChapterContentModalProps {
  chapter: ChapterArtifact | null;
  onClose: () => void;
}

const ChapterContentModal: React.FC<ChapterContentModalProps> = ({ chapter, onClose }) => {
  if (!chapter) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
              Chapter {chapter.content.chapter_number}
            </span>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {chapter.content.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors text-gray-500 dark:text-gray-400"
          >
            <X size={24} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className="prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
            {chapter.content.content}
          </div>
        </div>
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-2xl flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-white font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

const ProjectView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [artifacts, setArtifacts] = useState<any[]>([]);

  // Workflow mode states
  const [isWorkflowMode, setIsWorkflowMode] = useState(false);
  const [activeTab, setActiveTab] = useState<WorkflowTab>("plot");
  const [selectedChapter, setSelectedChapter] = useState<ChapterArtifact | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [workflowProgress, setWorkflowProgress] = useState<Record<string, WorkflowProgress>>({});
  const [videoStatus, setVideoStatus] = useState<string | null>("idle");
  // isLimitModalOpen states removed as unused
  
  // Terminology settings modal
  const [showTerminologyModal, setShowTerminologyModal] = useState(false);
  const [selectedTerminology, setSelectedTerminology] = useState<string>('Chapter');
  const [isSavingTerminology, setIsSavingTerminology] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);

  const [editedTitle, setEditedTitle] = useState("");
  const [viewChapter, setViewChapter] = useState<ChapterArtifact | null>(null);

  // Video generation polling
  const [generatingShotIds, setGeneratingShotIds] = useState<Set<string>>(new Set());
  const [latestVideoUrl, setLatestVideoUrl] = useState<string | null>(null);
  const [videoGenerations, setVideoGenerations] = useState<any[]>([]);
  const safetyTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const {
    startPolling,
    stopPolling,
    isComplete,
    isFailed,
    isGenerating: isVideoGenerating,
    generation,
    progress: generationProgress,
  } = useVideoGenerationStatus();

  // Context hooks
  const { selectChapter, selectedScriptId } = useScriptSelection();
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, []);

  // Load latest video generation for selected chapter (for Preview tab on page load)
  useEffect(() => {
    if (!selectedChapter) {
      setLatestVideoUrl(null);
      return;
    }

    const chapterId = getActualChapterId(selectedChapter);
    if (!chapterId) return;

    let cancelled = false;
    const loadLatestVideoGen = async () => {
      try {
        const result = await videoGenerationAPI.getChapterVideoGenerations(chapterId);
        if (cancelled) return;
        if (result.generations && result.generations.length > 0) {
          // Store all generations for the carousel
          setVideoGenerations(result.generations);
          // Latest generation is first (sorted by created_at desc)
          const latest = result.generations[0];
          if (latest.video_url) {
            setLatestVideoUrl(latest.video_url);
          } else {
            setLatestVideoUrl(null);
          }
        } else {
          setVideoGenerations([]);
          setLatestVideoUrl(null);
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load video generations:', error);
          setLatestVideoUrl(null);
        }
      }
    };

    loadLatestVideoGen();
    return () => { cancelled = true; };
  }, [selectedChapter]);

  useEffect(() => {
    if (id) {
      loadProject(id);
    }
  }, [id]);

  const loadProject = async (projectId: string) => {
    try {
      setLoading(true);
      const data = await projectService.getProject(projectId);
      setProject(data);
      if (data.artifacts) {
        setArtifacts(data.artifacts);
        // Set first chapter as selected
        const chapters = data.artifacts
          .filter((a: any) => a.artifact_type === 'CHAPTER' || a.artifact_type === 'chapter')
          .sort((a: any, b: any) => (a.content.chapter_number || 0) - (b.content.chapter_number || 0));
        if (chapters.length > 0) {
          setSelectedChapter(chapters[0]);
        }
      }
    } catch (error) {
      console.error("Failed to load project", error);
      toast.error("Failed to load project details");
      navigate("/creator");
    } finally {
      setLoading(false);
    }
  };

  // Get chapter artifacts
  const chapters = artifacts
    .filter(a => a.artifact_type === 'CHAPTER' || a.artifact_type === 'chapter')
    .sort((a, b) => (a.content.chapter_number || 0) - (b.content.chapter_number || 0));

  // Detect prompt-only project (no chapters, has input_prompt, no source material)
  const isPromptOnlyProject = chapters.length === 0 && 
    project?.input_prompt && 
    !project?.source_material_url;

  // Create a virtual "chapter" for prompt-only projects to work with generation panels
  const virtualChapter: ChapterArtifact | null = isPromptOnlyProject && project ? {
    id: project.id, // Use project ID as the chapter ID
    artifact_type: 'virtual',
    content: {
      title: project.title || 'Project Content',
      content: project.input_prompt || '',
      chapter_number: 1,
      summary: project.input_prompt || '',
    },
    version: 1,
    project_id: project.id,
  } : null;

  // Auto-redirect to workflow mode for prompt-only projects
  useEffect(() => {
    if (!loading && isPromptOnlyProject && !isWorkflowMode) {
      setIsWorkflowMode(true);
      // Set the virtual chapter as selected
      if (virtualChapter) {
        setSelectedChapter(virtualChapter);
      }
    }
  }, [loading, isPromptOnlyProject, isWorkflowMode, virtualChapter]);

  // Plot generation hook - use project ID with isProject flag
  const {
    plotOverview,
    loadPlot
  } = usePlotGeneration(id || '', {
    isProject: true,
    inputPrompt: project?.input_prompt,
    projectType: project?.project_type,
  });

  // Callback to refresh plot overview
  const refreshPlotOverview = useCallback(() => {
    return loadPlot();
  }, [loadPlot]);

  // Load plot when in workflow mode
  useEffect(() => {
    if (isWorkflowMode && project) {
      loadPlot();
    }
  }, [isWorkflowMode, project, loadPlot]);

  // Script generation hook
  const {
    generatedScripts,
    isLoading: isLoadingScripts,
    isGeneratingScript,
    loadScripts,
    generateScript,
    updateScript,
    deleteScript
  } = useScriptGeneration(getActualChapterId(selectedChapter));

  // Derive selectedScript
  const selectedScript = React.useMemo(() => {
    return generatedScripts.find(script => script.id === selectedScriptId) || null;
  }, [generatedScripts, selectedScriptId]);

  // Image and audio generation hooks
  const {
    sceneImages,
    loadImages,
  } = useImageGeneration(getActualChapterId(selectedChapter), selectedScriptId || null);

  const {
    files,
    loadAudio,
  } = useAudioGeneration({
    chapterId: getActualChapterId(selectedChapter),
    scriptId: selectedScript?.id,
  });

  // Load scripts when chapter changes
  useEffect(() => {
    if (selectedChapter && isWorkflowMode) {
      loadScripts();
      loadImages();
      if (selectedScript?.id) {
        loadAudio();
      }
    }
  }, [selectedChapter, isWorkflowMode, loadScripts, loadImages, loadAudio, selectedScript?.id]);

  // Get generated URLs for video production
  const [generatedImageUrls, setGeneratedImageUrls] = useState<string[]>([]);
  const [generatedAudioFiles, setGeneratedAudioFiles] = useState<string[]>([]);

  useEffect(() => {
    const imageUrls = Object.values(sceneImages)
      .flat()
      .filter((img: any) => {
        const normalizedScriptId = img.script_id || img.scriptId;
        return img.imageUrl && (!selectedScriptId || normalizedScriptId === selectedScriptId);
      })
      .sort((a: any, b: any) => a.sceneNumber - b.sceneNumber)
      .map((img: any) => img.imageUrl);
    setGeneratedImageUrls(imageUrls);
  }, [sceneImages]);

  useEffect(() => {
    const audioUrls: string[] = [];
    if (files) {
      files.forEach((file: any) => {
        if (file.url) {
          audioUrls.push(file.url);
        }
      });
    }
    setGeneratedAudioFiles(audioUrls);
  }, [files]);

  // Detect if this is a multi-script project (needs consultation)
  const isMultiScriptProject = project?.pipeline_steps?.includes('consultation');

  // Filter video generations by selected script at the top level
  const filteredVideoGenerations = React.useMemo(() => {
    if (!selectedScriptId || !videoGenerations) return videoGenerations;
    return videoGenerations.filter(gen => gen.script_id === selectedScriptId);
  }, [videoGenerations, selectedScriptId]);
  
  // Workflow tabs configuration - conditionally include consultation
  const workflowTabs = [
    ...(isMultiScriptProject ? [{ id: "consultation" as WorkflowTab, label: "Cinematic\nuniverse setup", icon: BookOpen, description: "AI-guided creative setup" }] : []),
    { id: "plot" as WorkflowTab, label: "Plot", icon: BookOpen, description: "Story overview & characters" },
    { id: "script" as WorkflowTab, label: "Script", icon: FileText, description: "Chapter scripts & scenes" },
    { id: "images" as WorkflowTab, label: "Images", icon: Image, description: "Scene & character images" },
    { id: "audio" as WorkflowTab, label: "Audio", icon: Music, description: "Music, effects & dialogue" },
    { id: "video" as WorkflowTab, label: "Video", icon: Video, description: "Final video production" },
  ];

  // Get progress for current chapter
  const getCurrentProgress = (): WorkflowProgress => {
    return selectedChapter
      ? workflowProgress[selectedChapter.id] || {
          plot: "idle",
          script: "idle",
          images: "idle",
          audio: "idle",
          video: "idle",
        }
      : {
          plot: "idle",
          script: "idle",
          images: "idle",
          audio: "idle",
          video: "idle",
        };
  };

  // Update progress for current chapter
  const updateProgress = (tab: WorkflowTab, status: WorkflowProgress[WorkflowTab]) => {
    if (!selectedChapter) return;
    setWorkflowProgress((prev) => ({
      ...prev,
      [selectedChapter.id]: {
        ...getCurrentProgress(),
        [tab]: status,
      },
    }));
  };

  // Progress indicator component
  const ProgressIndicator: React.FC<{ status: WorkflowProgress[WorkflowTab] }> = ({ status }) => {
    const getStatusColor = () => {
      switch (status) {
        case "completed": return "bg-green-500";
        case "generating": return "bg-blue-500 animate-pulse";
        case "error": return "bg-red-500";
        default: return "bg-gray-300";
      }
    };

    const getStatusIcon = () => {
      switch (status) {
        case "completed": return "✓";
        case "generating": return "⟳";
        case "error": return "✕";
        default: return "";
      }
    };

    return (
      <div className={`w-3 h-3 rounded-full ${getStatusColor()} flex items-center justify-center text-white text-xs font-bold`}>
        {getStatusIcon()}
      </div>
    );
  };

  // Handle video generation
  const storyboardContext = useStoryboardOptional();
  const handleGenerateVideo = async (selectedShotIds?: string[], overrideAudioIds?: string[]) => {
    if (!selectedChapter) return;

    // selectedScriptId is already available from useScriptSelection() hook at component level
    if (!selectedScriptId) {
      toast.error('Please select a script first');
      return;
    }

    updateProgress("video", "generating");
    setVideoStatus("starting");

    // Track which shots are being generated
    if (selectedShotIds && selectedShotIds.length > 0) {
      setGeneratingShotIds(new Set(selectedShotIds));
    } else {
      setGeneratingShotIds(new Set(['__all__']));
    }

    // Get selected audio IDs: preferably from override (e.g. specific scene generation) or fallback to context
    const selectedAudioIds = overrideAudioIds || (storyboardContext?.selectedAudioIds
      ? Array.from(storyboardContext.selectedAudioIds)
      : undefined);

    // Debug logging to verify selections reach the API
    console.log('[handleGenerateVideo] selectedShotIds:', selectedShotIds);
    console.log('[handleGenerateVideo] selectedAudioIds:', selectedAudioIds);
    console.log('[handleGenerateVideo] overrideAudioIds:', overrideAudioIds);

    try {
      const response = await videoGenerationAPI.startVideoGeneration(
        selectedScriptId,
        getActualChapterId(selectedChapter),
        'free',
        selectedShotIds,
        selectedAudioIds
      );

      if (response.video_generation_id) {
        // Start polling for generation status
        startPolling(response.video_generation_id);
        setVideoStatus("processing");

        // Safety timeout to clear generating spinner if polling never resolves
        if (safetyTimeoutRef.current) {
          clearTimeout(safetyTimeoutRef.current);
        }
        safetyTimeoutRef.current = setTimeout(() => {
          setGeneratingShotIds(prev => {
            if (prev.size > 0) {
              console.warn('[SAFETY] Clearing stale generatingShotIds after 5min timeout');
              setVideoStatus("idle");
              return new Set();
            }
            return prev;
          });
        }, 5 * 60 * 1000); // 5 minutes max

        const shotMsg = selectedShotIds?.length
          ? `for ${selectedShotIds.length} selected shot${selectedShotIds.length > 1 ? 's' : ''}`
          : 'for all shots';
        toast.success(`Video generation started ${shotMsg}!`);
      }
    } catch (error) {
      console.error('Failed to start video generation:', error);
      toast.error('Failed to start video generation');
      setVideoStatus("ready");
      setGeneratingShotIds(new Set());
      updateProgress("video", "idle");
    }
  };

  // React to video generation polling status changes
  useEffect(() => {
    if (isComplete) {
      if (safetyTimeoutRef.current) {
        clearTimeout(safetyTimeoutRef.current);
        safetyTimeoutRef.current = null;
      }
      setVideoStatus("completed");
      setGeneratingShotIds(new Set());
      updateProgress("video", "completed");
      // Update latestVideoUrl from polling data so Preview tab shows the video immediately
      if (generation?.video_url) {
        setLatestVideoUrl(generation.video_url);
      }
      toast.success('Video generation completed!');
    } else if (isFailed) {
      if (safetyTimeoutRef.current) {
        clearTimeout(safetyTimeoutRef.current);
        safetyTimeoutRef.current = null;
      }
      setVideoStatus("failed");
      setGeneratingShotIds(new Set());
      updateProgress("video", "error");
      stopPolling();
      toast.error(generation?.error_message || 'Video generation failed. Please try again.');
    } else if (isVideoGenerating) {
      setVideoStatus("processing");
    }
  }, [isComplete, isFailed, isVideoGenerating, stopPolling]);

  // Handle video generation deletion
  const handleDeleteVideoGeneration = async (genId: string) => {
    await videoGenerationAPI.deleteGeneration(genId);
    setVideoGenerations(prev => prev.filter(g => g.id !== genId));
    toast.success('Generation deleted successfully');
  };

  // Render tab content
  const renderTabContent = () => {
    if (!project) return null;

    switch (activeTab) {
      case "consultation":
        return (
          <ConsultationPanel
            projectId={project.id}
            inputPrompt={project.input_prompt}
            onConsultationComplete={() => {
              // Move to plot tab after consultation is accepted
              setActiveTab("plot");
              // Reload project to get updated structure
              loadProject(project.id);
            }}
            onSkip={() => setActiveTab("plot")}
            onNavigateToScript={(artifactId) => {
              // Find the chapter matching this artifact and switch to script tab
              const chapter = chapters.find((c) => c.id === artifactId);
              if (chapter) {
                setSelectedChapter(chapter);
                selectChapter(chapter.id, { reason: 'user' });
              }
              setActiveTab("script");
            }}
          />
        );
        
      case "plot":
        // Use ProjectPlotPanel for prompt-only projects, PlotOverviewPanel for book-based
        if (isPromptOnlyProject && project.input_prompt) {
          return (
            <ProjectPlotPanel
              projectId={project.id}
              projectTitle={project.title}
              inputPrompt={project.input_prompt}
              projectType={project.project_type}
              onCharacterChange={refreshPlotOverview}
            />
          );
        }
        return (
          <PlotOverviewPanel
            bookId={project.id}
            onCharacterChange={refreshPlotOverview}
            isProject={true}
            inputPrompt={project.input_prompt}
            projectType={project.project_type}
          />
        );

      case "script":
        if (!selectedChapter) {
          return (
            <div className="text-center py-12 text-gray-500">
              <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Please select a chapter to generate scripts</p>
            </div>
          );
        }
        return (
          <ScriptGenerationPanel
            chapterId={getActualChapterId(selectedChapter)}
            chapterTitle={selectedChapter.content.title}
            chapterContent={selectedChapter.content.content}
            generatedScripts={generatedScripts}
            isLoading={isLoadingScripts}
            isGeneratingScript={isGeneratingScript}
            onGenerateScript={generateScript}
            onUpdateScript={updateScript}
            onDeleteScript={deleteScript}
            plotOverview={plotOverview}
            onCreatePlotCharacter={async (name: string, entityType: 'character' | 'object' | 'location' = 'character') => {
              if (!id) throw new Error('No project ID');
              const result = await userService.createProjectCharacter(id, name, entityType);
              // Refresh plot overview to get updated characters list
              await loadPlot();
              return { ...result, entity_type: result.entity_type as 'character' | 'object' | 'location' };
            }}
          />
        );

      case "images":
        if (!selectedChapter) {
          return (
            <div className="text-center py-12 text-gray-500">
              <Image className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Please select a chapter to generate images</p>
            </div>
          );
        }
        return (
          <ImagesPanel
            chapterId={getActualChapterId(selectedChapter)}
            chapterTitle={selectedChapter.content.title}
            selectedScript={selectedScript}
            plotOverview={plotOverview}
            onRefreshPlotOverview={refreshPlotOverview}
            userTier={user?.subscription_tier || 'free'}
          />
        );

      case "audio":
        if (!selectedChapter) {
          return (
            <div className="text-center py-12 text-gray-500">
              <Music className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Please select a chapter to manage audio</p>
            </div>
          );
        }
        return (
          <AudioPanel
            chapterId={getActualChapterId(selectedChapter)}
            chapterTitle={selectedChapter.content.title}
            selectedScript={selectedScript}
            plotOverview={plotOverview}
          />
        );

      case "video":
        if (!selectedChapter) {
          return (
            <div className="text-center py-12 text-gray-500">
              <Video className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Please select a chapter to produce videos</p>
            </div>
          );
        }
        return (
          <VideoProductionPanel
            chapterId={getActualChapterId(selectedChapter)}
            chapterTitle={selectedChapter.content.title}
            imageUrls={generatedImageUrls}
            audioFiles={generatedAudioFiles}
            onGenerateVideo={handleGenerateVideo}
            videoStatus={videoStatus}
            canGenerateVideo={!!selectedChapter && videoStatus !== "processing" && videoStatus !== "starting"}
            selectedScript={selectedScript}
            generatingShotIds={generatingShotIds}
            generationProgress={generationProgress}
            videoUrl={generation?.video_url || latestVideoUrl || undefined}
            videoGenerations={filteredVideoGenerations}
            onDeleteGeneration={handleDeleteVideoGeneration}
          />
        );

      default:
        return <div>Tab content not implemented</div>;
    }
  };



  const handleStartRename = () => {
    setEditedTitle(project?.title || "");
    setIsEditingTitle(true);
  };

  const handleSaveRename = async () => {
    if (!project || !editedTitle.trim()) {
      setIsEditingTitle(false);
      return;
    }

    try {
      const updatedProject = await projectService.updateProject(project.id, {
        title: editedTitle.trim()
      });
      setProject(updatedProject);
      toast.success("Project renamed successfully");
      setIsEditingTitle(false);
    } catch (error) {
      console.error("Failed to rename project:", error);
      toast.error("Failed to rename project");
    }
  };

  const handleCancelRename = () => {
    setIsEditingTitle(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-gray-500">
        <h2 className="text-xl font-semibold mb-2">Project Not Found</h2>
        <button 
          onClick={() => navigate("/creator")}
          className="text-purple-600 hover:text-purple-700 font-medium flex items-center gap-2"
        >
          <ArrowLeft size={16} />
          Back to Creator Studio
        </button>
      </div>
    );
  }

  // WORKFLOW MODE VIEW
  if (isWorkflowMode) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button 
                  onClick={() => navigate("/creator")}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <ArrowLeft size={20} />
                </button>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white">{project.title}</h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Creator Mode • {chapters.length} {chapters.length > 0 && chapters[0].content_type_label 
                      ? getDynamicLabel(chapters[0], 0).plural 
                      : 'Chapters'}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className={`text-xs px-2 py-1 rounded-full border ${
                  project.status === 'completed' ? 'bg-green-100 text-green-700 border-green-200' :
                  project.status === 'published' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                  'bg-purple-100 text-purple-700 border-purple-200'
                }`}>
                  {project.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex min-h-screen">
          {/* Main Content Area */}
          <div className={`flex-1 min-w-0 overflow-hidden transition-all duration-300 ${sidebarCollapsed ? "mr-16" : "mr-80"}`}>
            <div className="p-6 overflow-x-auto">
              {/* Workflow Tabs */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
                <div className="border-b border-gray-200 dark:border-gray-700">
                  <nav className="flex space-x-8 px-6" aria-label="Tabs">
                    {workflowTabs.map((tab) => {
                      const isActive = activeTab === tab.id;
                      const currentProgress = getCurrentProgress();
                      const tabProgress = currentProgress[tab.id];

                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center space-x-3 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                            isActive
                              ? "border-purple-500 text-purple-600"
                              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                          }`}
                        >
                          <tab.icon className="w-5 h-5" />
                          <span>{tab.label}</span>
                          <ProgressIndicator status={tabProgress} />
                          {!isActive && (
                            <span className="text-xs text-gray-400 hidden lg:block">
                              {tab.description}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </nav>
                </div>

                {/* Tab Content */}
                <div className="p-6">{renderTabContent()}</div>
              </div>
            </div>
          </div>

          {/* Right Sidebar - Chapter List */}
          <div className={`fixed right-0 top-0 h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700 transition-all duration-300 ${
            sidebarCollapsed ? "w-16" : "w-80"
          }`}>
            {/* Sidebar Toggle */}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="absolute -left-3 top-20 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-full p-1 shadow-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              {sidebarCollapsed ? (
                <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-300" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-300" />
              )}
            </button>

            {/* Sidebar Content */}
            <div className="h-full overflow-y-auto pt-16">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                {!sidebarCollapsed ? (
                  <>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                      {chapters.length > 0 && chapters[0].content_type_label 
                        ? getDynamicLabel(chapters[0], 0).plural 
                        : 'Chapters'}
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {chapters.length} {chapters.length > 0 && chapters[0].content_type_label 
                        ? getDynamicLabel(chapters[0], 0).plural.toLowerCase() 
                        : 'chapters'} total
                    </p>
                  </>
                ) : (
                  <div className="flex justify-center">
                    <BookOpen className="w-6 h-6 text-gray-400" />
                  </div>
                )}
              </div>

              <div className="p-2">
                {chapters.map((chapter, index) => {
                  const chapterProgress = workflowProgress[chapter.id];
                  const completedSteps = chapterProgress
                    ? Object.values(chapterProgress).filter((status) => status === "completed").length
                    : 0;
                  const totalSteps = 5;
                  const progressPercentage = (completedSteps / totalSteps) * 100;

                  return (
                    <button
                      key={chapter.id}
                      onClick={() => {
                        setSelectedChapter(chapter);
                        selectChapter(chapter.id, { reason: 'user' });
                      }}
                      className={`w-full text-left p-3 rounded-lg transition-colors mb-2 ${
                        selectedChapter?.id === chapter.id
                          ? "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-700 border"
                          : "hover:bg-gray-50 dark:hover:bg-gray-700"
                      }`}
                    >
                      {!sidebarCollapsed ? (
                        <>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 dark:text-white truncate">
                                {chapter.content.title}
                              </p>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {getDynamicLabel(chapter, index).label}
                              </p>
                            </div>
                          </div>

                          {/* Progress Bar */}
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                              <span>Progress</span>
                              <span>{completedSteps}/{totalSteps}</span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                              <div
                                className="bg-purple-600 h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${progressPercentage}%` }}
                              ></div>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="flex flex-col items-center">
                          <span className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
                            {chapter.script_order || chapter.content.chapter_number || index + 1}
                          </span>
                          <div className="w-8 bg-gray-200 dark:bg-gray-600 rounded-full h-1">
                            <div
                              className="bg-purple-600 h-1 rounded-full"
                              style={{ width: `${progressPercentage}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // OVERVIEW MODE VIEW (default)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => navigate("/creator")}
                className="p-2 -ml-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                {isEditingTitle ? (
                  <div className="flex items-center gap-2 mb-1">
                    <input
                      type="text"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="text-xl font-bold text-gray-900 dark:text-white bg-transparent border-b-2 border-purple-500 focus:outline-none min-w-[200px]"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename();
                        if (e.key === 'Escape') handleCancelRename();
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleSaveRename(); }}
                      className="p-1 hover:bg-green-100 dark:hover:bg-green-900 rounded-full text-green-600 dark:text-green-400"
                    >
                      <Check size={18} />
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleCancelRename(); }}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded-full text-red-600 dark:text-red-400"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ) : (
                  <div 
                    className="flex items-center gap-3 mb-1 group cursor-pointer -ml-2 px-2 py-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    onClick={handleStartRename}
                    title="Click to rename project"
                  >
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                      {project.title}
                    </h1>
                    <Edit2 size={16} className="text-gray-400 group-hover:text-purple-600 transition-colors" />
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      project.status === 'completed' ? 'bg-green-100 text-green-700 border-green-200' :
                      project.status === 'published' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                      'bg-gray-100 text-gray-600 border-gray-200'
                    }`}>
                      {project.status.replace('_', ' ')}
                    </span>
                  </div>
                )}
                <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    Last updated {new Date(project.updated_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <BookOpen size={12} />
                    {chapters.length} {chapters.length > 0 && chapters[0].content_type_label 
                      ? getDynamicLabel(chapters[0], 0).plural 
                      : 'Chapters'}
                  </span>
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <button 
                onClick={() => {
                  setSelectedTerminology(project?.content_terminology || 'Chapter');
                  setShowTerminologyModal(true);
                }}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                title="Project Settings"
              >
                <Settings size={20} />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <MoreVertical size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content: Chapters */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {chapters.length > 0 && chapters[0].content_type_label 
                  ? getDynamicLabel(chapters[0], 0).plural 
                  : 'Chapters'}
              </h2>
              <button className="px-4 py-2 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors">
                Regenerate All
              </button>
            </div>

            {chapters.length === 0 ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
                <FileText size={48} className="mx-auto text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Content Yet</h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                  Upload a book or source material to extract chapters, or generate them from a prompt.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {chapters.map((chapter) => (
                  <div 
                    key={chapter.id}
                    className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow cursor-pointer"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                            Chapter {chapter.content.chapter_number}
                          </span>
                        </div>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate pr-4">
                          {chapter.content.title}
                        </h3>
                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                          {chapter.content.content}
                        </p>
                      </div>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setViewChapter(chapter);
                        }}
                        className="p-2 text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="View full chapter content"
                      >
                        <ExternalLink size={18} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar: Project Info & Actions */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                Actions
              </h2>
              <div className="space-y-3">
                <button 
                  onClick={() => setIsWorkflowMode(true)}
                  disabled={chapters.length === 0}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors shadow-sm"
                >
                  <Play size={18} />
                  Start Generation
                </button>

              </div>
            </div>

            {/* Project Details */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                Project Details
              </h2>
              <dl className="space-y-4">
                <div>
                  <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Type</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{project.project_type}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Mode</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{project.workflow_mode}</dd>
                </div>
                {project.input_prompt && (
                  <div>
                    <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Original Prompt</dt>
                    <dd className="mt-1 text-sm text-gray-600 dark:text-gray-300 italic">" {project.input_prompt} "</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      </div>
      
      {/* Chapter View Modal */}
      <ChapterContentModal 
        chapter={viewChapter} 
        onClose={() => setViewChapter(null)} 
      />

      {/* Terminology Settings Modal */}
      {showTerminologyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Content Terminology</h3>
              <button
                onClick={() => setShowTerminologyModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X size={20} />
              </button>
            </div>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Choose how content units are labeled throughout this project.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Content Type
                </label>
                <select
                  value={selectedTerminology}
                  onChange={(e) => setSelectedTerminology(e.target.value)}
                  className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="Film">Film (Film 1, Film 2...)</option>
                  <option value="Episode">Episode (Episode 1, Episode 2...)</option>
                  <option value="Part">Part (Part 1, Part 2...)</option>
                  <option value="Chapter">Chapter (Chapter 1, Chapter 2...)</option>
                  <option value="Script">Script (Script 1, Script 2...)</option>
                </select>
              </div>
              
              <div className="pt-2 text-xs text-gray-500 dark:text-gray-400">
                This will update how content is labeled in the sidebar and headers.
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowTerminologyModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!project) return;
                  setIsSavingTerminology(true);
                  try {
                    await projectService.updateProject(project.id, { 
                      content_terminology: selectedTerminology 
                    });
                    // Update local project state
                    setProject({ ...project, content_terminology: selectedTerminology });
                    // Update all artifacts' content_type_label
                    setArtifacts((prevArtifacts: any[]) => 
                      prevArtifacts.map((a: any) => ({ ...a, content_type_label: selectedTerminology }))
                    );
                    setShowTerminologyModal(false);
                  } catch (error) {
                    console.error('Failed to save terminology:', error);
                  } finally {
                    setIsSavingTerminology(false);
                  }
                }}
                disabled={isSavingTerminology}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg font-medium shadow-sm transition-colors flex items-center gap-2"
              >
                {isSavingTerminology ? 'Saving...' : 'Apply to Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectView;
