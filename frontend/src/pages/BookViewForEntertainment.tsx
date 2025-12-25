import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { useScriptSelection } from '../contexts/ScriptSelectionContext';
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";
import {
  FileText,
  BookOpen,
  Image,
  Music,
  Video,
  ChevronLeft,
  ChevronRight,
  Play,
  Download,
} from "lucide-react";
import { VideoScene } from "../services/videoService";
import { aiService } from "../services/aiService";
import { PipelineStatus } from "../components/VideoGeneration/PipelineStatus";
import type { PipelineStatus as PipelineStatusType } from "../types/pipelinestatus";
import ExistingGenerations from "../components/VideoGeneration/ExistingGenerations";
import videoGenerationAPI from "../lib/videoGenerationApi";
import PlotOverviewPanel from '../components/Plot/PlotOverviewPanel';
import ScriptGenerationPanel from '../components/Script/ScriptGenerationPanel';
import ImagesPanel from '../components/Images/ImagesPanel';
import { usePlotGeneration } from '../hooks/usePlotGeneration';
import { useScriptGeneration } from '../hooks/useScriptGeneration';
import AudioPanel from '../components/Audio/AudioPanel';
import { useImageGeneration } from '../hooks/useImageGeneration';
import { useAudioGeneration } from '../hooks/useAudioGeneration';
import VideoProductionPanel from '../components/Video/VideoProductionPanel';

interface Chapter {
  id: string;
  title: string;
  content: string;
}


interface Book {
  id: string;
  title: string;
  author_name: string;
  description: string;
  cover_image_url: string | null;
  book_type: string;
  difficulty: string;
  status: string;
  total_chapters: number;
  chapters: Chapter[];
  user_id: string;
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

interface AIScriptResult {
  script: string;
  scene_descriptions: (string | SceneDescription)[];
  characters: string[];
  character_details: string;
  script_style: string;
  script_id?: string;
}


interface WorkflowProgress {
  plot: "idle" | "generating" | "completed" | "error";
  script: "idle" | "generating" | "completed" | "error";
  images: "idle" | "generating" | "completed" | "error";
  audio: "idle" | "generating" | "completed" | "error";
  video: "idle" | "generating" | "completed" | "error";
}

type WorkflowTab = "plot" | "script" | "images" | "audio" | "video";

export default function BookViewForEntertainment() {
  const { id } = useParams();

  // Wire selectChapter and selectedScriptId from ScriptSelectionContext
  const { selectChapter, selectedScriptId } = useScriptSelection();

  // State declarations - all hooks at the top level
  const [book, setBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [videoUrls, setVideoUrls] = useState<Record<string, string>>({});
  const [videoGenerationId, setVideoGenerationId] = useState<string | null>(
    null
  );
  const [videoStatus, setVideoStatus] = useState<string | null>("idle");

  const [showFullScript, setShowFullScript] = useState(false);
  const [animationStyle, setAnimationStyle] = useState<
    "cartoon" | "realistic" | "cinematic" | "fantasy"
  >("realistic");
  const [scriptStyle, setScriptStyle] = useState("cinematic_movie");
  const [isLoading, setIsLoading] = useState(true);
  const [aiScriptResults, setAiScriptResults] = useState<
    Record<string, AIScriptResult>
  >({});

  const [loadingScript, setLoadingScript] = useState(false);

  const [pipelineStatus, setPipelineStatus] =
    useState<PipelineStatusType | null>(null);
  const [showPipelineStatus, setShowPipelineStatus] = useState(false);

  // Add new state for task tracking
  const [audioTaskId, setAudioTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);

  const [showExistingGenerations, setShowExistingGenerations] = useState(true);
  const [currentVideoToWatch, setCurrentVideoToWatch] = useState<string | null>(
    null
  );

  const [lastUpdated, setLastUpdated] = useState(Date.now());
  const [existingGenerations, setExistingGenerations] = useState<any[]>([]);

  // New workflow state
  const [activeTab, setActiveTab] = useState<WorkflowTab>("plot");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [workflowProgress, setWorkflowProgress] = useState<
    Record<string, WorkflowProgress>
  >({});

  // State for storing generated images and audio for video production
  const [generatedImageUrls, setGeneratedImageUrls] = useState<string[]>([]);
  const [generatedAudioFiles, setGeneratedAudioFiles] = useState<string[]>([]);

  // Ref to track if component is mounted
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Workflow tabs configuration
  const workflowTabs = [
    {
      id: "plot" as WorkflowTab,
      label: "Plot",
      icon: BookOpen,
      description: "Story overview & characters",
    },
    

    {
      id: "script" as WorkflowTab,
      label: "Script",
      icon: FileText,
      description: "Chapter scripts & scenes",
    },
    
    {
      id: "images" as WorkflowTab,
      label: "Images",
      icon: Image,
      description: "Scene & character images",
    },
    {
      id: "audio" as WorkflowTab,
      label: "Audio",
      icon: Music,
      description: "Music, effects & dialogue",
    },
    {
      id: "video" as WorkflowTab,
      label: "Video",
      icon: Video,
      description: "Final video production",
    },
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
  const updateProgress = (
    tab: WorkflowTab,
    status: WorkflowProgress[WorkflowTab]
  ) => {
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
  const ProgressIndicator: React.FC<{
    status: WorkflowProgress[WorkflowTab];
  }> = ({ status }) => {
    const getStatusColor = () => {
      switch (status) {
        case "completed":
          return "bg-green-500";
        case "generating":
          return "bg-blue-500 animate-pulse";
        case "error":
          return "bg-red-500";
        default:
          return "bg-gray-300";
      }
    };

    const getStatusIcon = () => {
      switch (status) {
        case "completed":
          return "✓";
        case "generating":
          return "⟳";
        case "error":
          return "✕";
        default:
          return "";
      }
    };

    return (
      <div
        className={`w-3 h-3 rounded-full ${getStatusColor()} flex items-center justify-center text-white text-xs font-bold`}
      >
        {getStatusIcon()}
      </div>
    );
  };

  // Add these handler functions after your existing function
  const handleContinueGeneration = async (videoGenId: string) => {
    try {
      setVideoGenerationId(videoGenId);
      setVideoStatus("resuming");

      // Call retry endpoint to continue generation
      const response = await aiService.retryVideoGeneration(videoGenId);


      // Show more detailed success message with safe property access
      const progressInfo = response?.existing_progress;
      let message = `Resuming from ${response?.retry_step || "next step"}`;

      if (progressInfo) {
        const existing = [];
        if (
          progressInfo.audio_files_count &&
          progressInfo.audio_files_count > 0
        ) {
          existing.push(`${progressInfo.audio_files_count} audio files`);
        }
        if (progressInfo.images_count && progressInfo.images_count > 0) {
          existing.push(`${progressInfo.images_count} images`);
        }
        if (progressInfo.videos_count && progressInfo.videos_count > 0) {
          existing.push(`${progressInfo.videos_count} videos`);
        }

        if (existing.length > 0) {
          message += `. Existing: ${existing.join(", ")}`;
        }

        if (progressInfo.progress_percentage) {
          message += ` (${progressInfo.progress_percentage.toFixed(
            0
          )}% complete)`;
        }
      }

      toast.success(message);

      // Start polling for status updates
      pollVideoStatus(videoGenId);

      // Hide existing generations during active generation
      setShowExistingGenerations(false);
    } catch (error: any) {

      let errorMessage = "Failed to continue video generation";

      // Safe error handling with proper type checking
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      } else if (typeof error === "string") {
        errorMessage = error;
      }

      toast.error(`Retry failed: ${errorMessage}`);
      setVideoStatus("error");
      setShowExistingGenerations(true);
    }
  };

  const handleWatchVideo = (videoUrl: string) => {
    setCurrentVideoToWatch(videoUrl);
  };


  // Add function to select a script
  const handleSelectScript = async (script: any) => {
    selectScript(script);

    // Update the aiScriptResults to show this script is available
    setAiScriptResults((prev) => ({
      ...prev,
      [script.chapter_id]: {
        script: script.script,
        scene_descriptions: script.scene_descriptions || [],
        characters: script.characters || [],
        character_details: script.character_details || "",
        script_style: script.script_style,
        script_id: script.id,
      },
    }));

    toast.success(
      `Selected ${script.script_style} script for video generation`
    );
  };



  // Add plot generation hook
  const {
    plotOverview,
    isGenerating: isGeneratingPlot,
    generatePlot,
    loadPlot
  } = usePlotGeneration(id || '');

  // Callback to refresh plot overview after character changes
  const refreshPlotOverview = useCallback(() => {
    return loadPlot();
  }, [loadPlot]);

  // Load plot on component mount and chapter change
  useEffect(() => {
    if (book) {
      loadPlot();
    }
  }, [book]);

  // Scripts are loaded by the useScriptGeneration hook

  // Load book data
  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = (await userService.getBook(bookId)) as Book;
      setBook(bookData);

      // Set first chapter as selected by default
      if (bookData.chapters && bookData.chapters.length > 0) {
        setSelectedChapter(bookData.chapters[0]);
        selectChapter(bookData.chapters[0].id, { reason: 'load' });
      }
    } catch (error) {
      toast.error("Failed to load book");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!selectedChapter) return;

    try {
      updateProgress("video", "generating");
      setVideoStatus("starting");

      // Use selected script if available, otherwise let backend use most recent
      const scriptId = selectedScript?.id;

      const result = await userService.generateEntertainmentVideo(
        selectedChapter.id,
        "basic",
        animationStyle,
        scriptId
      );

      setVideoGenerationId(result.video_generation_id);
      setAudioTaskId(result.audio_task_id || null);
      setTaskStatus(result.task_status || null);
      setVideoStatus("processing");

      toast.success(`Video generation started! ${result.message}`);
      
      // Start polling - the function now handles its own lifecycle
      pollVideoStatus(result.video_generation_id);
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail ||
                          error?.message ||
                          "Failed to start video generation";
      toast.error(errorMessage);
      setVideoStatus("error");
      updateProgress("video", "error");
    }
  };

  useEffect(() => {
    if (selectedChapter) {
      fetchExistingGenerations(); // ✅ Add this line
    }
  }, [selectedChapter]);

  // Add this useEffect to handle status changes

  // Update the existing generations fetch to be more reliable
  const fetchExistingGenerations = useCallback(async () => {
    if (!selectedChapter) return;

    try {
      const response = await videoGenerationAPI.getChapterVideoGenerations(
        selectedChapter.id
      );
      const generations = response.generations || [];

      if (mountedRef.current) {
        setExistingGenerations(generations); // ✅ Now using the array

        // If we have generations, show them
        if (generations.length > 0) {
          setShowExistingGenerations(true);
        }
      }
    } catch (error) {
      // Even on error, show the generation interface
      if (mountedRef.current) {
        setShowExistingGenerations(true);
      }
    }
  }, [selectedChapter]);

  useEffect(() => {
    if (videoStatus === "failed" && selectedChapter) {
      // Delay to ensure backend has updated the status
      const timer = setTimeout(() => {
        fetchExistingGenerations();
        setShowExistingGenerations(true);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [videoStatus, selectedChapter]);

  // Add status polling
  // Update the pollVideoStatus function with proper lifecycle management:

  const pollVideoStatus = (videoGenId: string) => {
    const checkStatus = async () => {
      // Check if component is still mounted
      if (!mountedRef.current) {
        return;
      }

      try {
        const data = await userService.getVideoGenerationStatus(videoGenId);

        // Check again if component is still mounted before updating state
        if (!mountedRef.current) {
          return;
        }

        setVideoStatus(data.generation_status);

        // Update pipeline status if component is still mounted
        if (mountedRef.current) {
          try {
            const pipelineData = await aiService.getPipelineStatus(videoGenId);
            if (mountedRef.current) {
              setPipelineStatus(pipelineData);
              setLastUpdated(Date.now());
            }
          } catch (pipelineError) {
          }

          if (data.task_metadata?.audio_task_state && mountedRef.current) {
            setTaskStatus(data.task_metadata.audio_task_state);
          }

          // Handle completion
          if (data.generation_status === "completed" && data.video_url && mountedRef.current) {
            setVideoUrls((prev) => ({
              ...prev,
              [selectedChapter!.id]: data.video_url!,
            }));
            updateProgress("video", "completed");
            toast.success("Video generation completed!");
            setShowPipelineStatus(false);
            setShowExistingGenerations(true);
            return; // Stop polling
          }

          // Handle failure
          if (data.generation_status === "failed" && mountedRef.current) {
            toast.error(data.error_message || "Video generation failed");
            updateProgress("video", "error");
            setShowExistingGenerations(true);
            setTimeout(() => {
              if (mountedRef.current) {
                fetchExistingGenerations();
              }
            }, 1000);
            return; // Stop polling
          }
        }

        // Continue polling for active statuses
        if (
          mountedRef.current &&
          [
            "pending",
            "generating_audio",
            "audio_completed",
            "generating_images",
            "images_completed",
            "generating_video",
            "video_completed",
            "combining",
            "merging_audio",
            "applying_lipsync",
          ].includes(data.generation_status)
        ) {
          setTimeout(checkStatus, 2000);
        } else if (mountedRef.current) {
          setShowExistingGenerations(true);
        }
      } catch (error) {
        if (mountedRef.current) {
          toast.error("Error checking video status");
          setShowExistingGenerations(true);
        }
      }
    };

    // Start polling
    checkStatus();
  };

  const formatStatus = (status: string | null | undefined): string => {
    if (!status) return "Initializing";
    return status.replace(/_/g, " ");
  };

  const handleGenerateScript = async () => {
    if (!selectedChapter) return;
    setLoadingScript(true);
    updateProgress("script", "generating");

    try {
      const result = await userService.generateScriptAndScenes(
        selectedChapter.id,
        scriptStyle
      );

      setAiScriptResults((prev) => ({
        ...prev,
        [selectedChapter.id]: result,
      }));

      updateProgress("script", "completed");
      toast.success("AI Script & Scene Descriptions generated!");
    } catch (error) {
      toast.error("Failed to generate script/scene descriptions");
      updateProgress("script", "error");
    } finally {
      setLoadingScript(false);
    }
  };

  // Add the retry handler function after your existing functions
  const handleRetry = async () => {
    if (!videoGenerationId) return;

    setIsLoading(true);
    try {
      await aiService.retryVideoGeneration(videoGenerationId);
      toast.success("Retrying video generation...");
      pollVideoStatus(videoGenerationId);
    } catch (error) {
      toast.error("Failed to retry video generation. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Add refresh handler for pipeline status
  const handleRefreshStatus = async () => {
    if (!videoGenerationId) return;

    setIsLoading(true);
    try {
      const status = await aiService.getPipelineStatus(videoGenerationId);
      setPipelineStatus(status);
    } catch (error) {
      toast.error("Failed to refresh status");
    } finally {
      setIsLoading(false);
    }
  };

  // Load book on component mount
  useEffect(() => {
    if (id) {
      loadBook(id);
    }
  }, [id]);

  useEffect(() => {
    if (selectedChapter) {
      fetchExistingGenerations();
    }
  }, [selectedChapter]);

  useEffect(() => {
    if (videoStatus === "failed" && selectedChapter) {
      const timer = setTimeout(() => {
        fetchExistingGenerations();
        setShowExistingGenerations(true);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [videoStatus, selectedChapter]);

  // Render chapter content
  const renderChapterContent = () => {
    const content = selectedChapter?.content || "";
    const maxChars = 70;

    if (content.length <= maxChars) {
      return <p className="text-gray-700 dark:text-gray-300">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700 dark:text-gray-300">
          {showFullScript ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFullScript(!showFullScript)}
          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm mt-1"
        >
          {showFullScript ? "Show Less" : "Show More"}
        </button>
      </div>
    );
  };



  const {
    generatedScripts,
    isLoading: isLoadingScripts,
    isGeneratingScript,
    loadScripts,
    generateScript,
    selectScript,
    updateScript,
    deleteScript
  } = useScriptGeneration(selectedChapter?.id || '');

  // Derive selectedScript from generatedScripts using context's selectedScriptId
  const selectedScript = React.useMemo(() => {
    return generatedScripts.find(script => script.id === selectedScriptId) || null;
  }, [generatedScripts, selectedScriptId]);

  useEffect(() => {
    if (selectedChapter) {
      fetchExistingGenerations();
      loadScripts(); // Load enhanced scripts
    }
  }, [selectedChapter, loadScripts]);

  // Add image generation hook
  const {
    sceneImages,
    characterImages,
    isLoading: isLoadingImages,
    loadImages,
  } = useImageGeneration(selectedChapter?.id || '');

  // Add audio generation hook
  const {
    files,
    isLoading: isLoadingAudio,
    loadAudio,
  } = useAudioGeneration({
    chapterId: selectedChapter?.id || '',
    scriptId: selectedScript?.id,
  });

  // Load images and audio when chapter changes
  useEffect(() => {
    if (selectedChapter) {
      loadImages();
      if (selectedScript?.id) {
        loadAudio();
      }
    }
  }, [selectedChapter, selectedScript?.id, loadImages, loadAudio]);

  // Update generated URLs when images/audio change
  useEffect(() => {
    // Extract image URLs from sceneImages
    const imageUrls = Object.values(sceneImages)
      .filter(img => img.imageUrl)
      .sort((a, b) => a.sceneNumber - b.sceneNumber)
      .map(img => img.imageUrl);
    setGeneratedImageUrls(imageUrls);
  }, [sceneImages]);

  useEffect(() => {
    // Extract audio file URLs from files
    const audioUrls: string[] = [];
    if (files) {
      files.forEach((file) => {
        if (file.url) {
          audioUrls.push(file.url);
        }
      });
    }
    setGeneratedAudioFiles(audioUrls);
  }, [files]);

  // Render workflow tab content
  const renderTabContent = () => {
    const currentProgress = getCurrentProgress();

    switch (activeTab) {

       case "plot":
         return (
          <PlotOverviewPanel
            bookId={book!.id}
            onCharacterChange={refreshPlotOverview}
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
            chapterId={selectedChapter.id}
            chapterTitle={selectedChapter.title}
            chapterContent={selectedChapter.content}
            generatedScripts={generatedScripts}
            selectedScript={selectedScript}
            isLoading={isLoadingScripts}
            isGeneratingScript={isGeneratingScript}
            onGenerateScript={generateScript}
            onSelectScript={selectScript}
            onUpdateScript={updateScript}
            onDeleteScript={deleteScript}
            plotOverview={plotOverview}
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
          chapterId={selectedChapter.id}
          chapterTitle={selectedChapter.title}
          selectedScript={selectedScript}
          plotOverview={plotOverview}
          onRefreshPlotOverview={refreshPlotOverview}
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
      chapterId={selectedChapter.id}
      chapterTitle={selectedChapter.title}
      selectedScript={selectedScript}
      plotOverview={plotOverview}
    />
  );

      case "video": {
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
            chapterId={selectedChapter.id}
            chapterTitle={selectedChapter.title}
            imageUrls={generatedImageUrls}
            audioFiles={generatedAudioFiles}
            plotOverview={plotOverview}
            onGenerateVideo={handleGenerateVideo}
            videoStatus={videoStatus}
            canGenerateVideo={!!selectedChapter && videoStatus !== "processing" && videoStatus !== "starting"}
          />
        );
      }

      default:
        return <div>Tab content not implemented</div>;
    }
  };

  // Check for valid id
  if (!id) {
    return <div className="p-8 text-center text-red-500">Invalid book id</div>;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-[#0F0F23]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-4 text-lg text-gray-700 dark:text-gray-300">Loading...</span>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-[#0F0F23] text-red-500">
        <p className="text-lg">Book not found.</p>
      </div>
    );
  }

  // DEBUG LOGGING

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0F0F23] transition-colors duration-300">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <img
                src={book.cover_image_url || ""}
                alt={book.title}
                className="w-16 h-20 object-cover rounded-lg shadow-md"
              />
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{book.title}</h1>
                <p className="text-gray-600 dark:text-gray-400">by {book.author_name}</p>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300 rounded-full">
                    Entertainment Production
                  </span>
                  <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 rounded-full">
                    {book.difficulty}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {/* Generate Video button moved to VideoProductionPanel */}
            </div>
          </div>
        </div>
      </div>

      <div className="flex min-h-screen">
        {/* Main Content Area - Much Wider */}
        <div
          className={`flex-1 transition-all duration-300 ${
            sidebarCollapsed ? "mr-16" : "mr-80"
          }`}
        >
          <div className="p-6">
            {/* Workflow Tabs */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
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
                            ? "border-blue-500 text-blue-600 dark:text-blue-400"
                            : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600"
                        }`}
                      >
                        <tab.icon className="w-5 h-5" />
                        <span>{tab.label}</span>
                        <ProgressIndicator status={tabProgress} />
                        {!isActive && (
                          <span className="text-xs text-gray-400 dark:text-gray-500 hidden lg:block">
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
        <div
          className={`fixed right-0 top-0 h-full bg-white dark:bg-gray-800 shadow-lg border-l border-gray-200 dark:border-gray-700 transition-all duration-300 ${
            sidebarCollapsed ? "w-16" : "w-80"
          }`}
        >
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
          <div className="h-full overflow-y-auto">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              {!sidebarCollapsed ? (
                <>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                    Chapters
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {book.total_chapters} chapters total
                  </p>
                </>
              ) : (
                <div className="flex justify-center">
                  <BookOpen className="w-6 h-6 text-gray-400" />
                </div>
              )}
            </div>

            <div className="p-2">
              {book.chapters?.map((chapter, index) => {
                const chapterProgress = workflowProgress[chapter.id];
                const completedSteps = chapterProgress
                  ? Object.values(chapterProgress).filter(
                      (status) => status === "completed"
                    ).length
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
                        ? "bg-blue-50 border-blue-200 border"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    {!sidebarCollapsed ? (
                      <>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate">
                              {chapter.title}
                            </p>
                            <p className="text-sm text-gray-500">
                              Chapter {index + 1}
                            </p>
                          </div>
                          {videoUrls[chapter.id] && (
                            <div className="w-2 h-2 bg-green-500 rounded-full ml-2"></div>
                          )}
                        </div>

                        {/* Progress Bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs text-gray-500">
                            <span>Progress</span>
                            <span>
                              {completedSteps}/{totalSteps}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${progressPercentage}%` }}
                            ></div>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center">
                        <span className="text-xs font-medium text-gray-600 mb-1">
                          {index + 1}
                        </span>
                        <div className="w-8 bg-gray-200 rounded-full h-1">
                          <div
                            className="bg-blue-600 h-1 rounded-full"
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

      {/* Video Player Modal */}
      {currentVideoToWatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Generated Video</h3>
              <button
                onClick={() => setCurrentVideoToWatch(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <video
              src={currentVideoToWatch}
              controls
              className="w-full max-h-96 rounded"
            />
            <div className="mt-4 flex justify-end space-x-2">
              <a
                href={currentVideoToWatch}
                download
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </a>
              <button
                onClick={() => setCurrentVideoToWatch(null)}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
