import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";
import { FileText } from "lucide-react";
import { VideoScene } from "../services/videoService";
import { aiService } from "../services/aiService";
import { PipelineStatus } from "../components/VideoGeneration/PipelineStatus";
import type { PipelineStatus as PipelineStatusType } from "../types/pipelinestatus";
import ExistingGenerations from "../components/VideoGeneration/ExistingGenerations";
import videoGenerationAPI from "../lib/videoGenerationApi";

interface Chapter {
  id: string;
  title: string;
  content: string;
}

interface VideoGenerationResponse {
  video_generation_id: string;
  script_id: string;
  status: string;
  audio_task_id?: string;
  task_status?: string;
  message: string;
  script_info: {
    script_style: string;
    video_style: string;
    scenes: number;
    characters: number;
    created_at: string;
  };
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

export default function BookViewForEntertainment() {
  const { id } = useParams<{ id: string }>();

  // State declarations - all hooks at the top level
  const [book, setBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [videoUrls, setVideoUrls] = useState<Record<string, string>>({});
  const [videoScenes, setVideoScenes] = useState<Record<string, VideoScene>>(
    {}
  );
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
    Record<
      string,
      {
        script: string;
        scene_descriptions: string[];
        characters: string[];
        character_details: string;
        script_style: string;
      }
    >
  >({});
  const [loadingScript, setLoadingScript] = useState(false);
  const [generatedScripts, setGeneratedScripts] = useState<any[]>([]);
  const [selectedScript, setSelectedScript] = useState<any>(null);
  const [loadingScripts, setLoadingScripts] = useState(false);

  const [pipelineStatus, setPipelineStatus] =
    useState<PipelineStatusType>(null);
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



  // Add these handler functions after your existing function
  const handleContinueGeneration = async (videoGenId: string) => {
    try {
      setVideoGenerationId(videoGenId);
      setVideoStatus("resuming");

      // Call retry endpoint to continue generation
      const response = await aiService.retryVideoGeneration(videoGenId);

      console.log("✅ Retry response:", response);

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
      console.error("Error continuing generation:", error);

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
    // You can also open in a modal or new tab
    // window.open(videoUrl, '_blank');
  };

  // Add function to fetch scripts
  const fetchGeneratedScripts = async (chapterId: string) => {
    if (!chapterId) return;

    try {
      setLoadingScripts(true);
      const data = await userService.getChapterScripts(chapterId);
      setGeneratedScripts(data.scripts || []);
    } catch (error) {
      console.error("Error fetching scripts:", error);
      toast.error("Failed to fetch scripts");
    } finally {
      setLoadingScripts(false);
    }
  };

  // Add function to select a script
  const handleSelectScript = async (script: any) => {
    setSelectedScript(script);

    // Update the aiScriptResults to show this script is available
    setAiScriptResults((prev) => ({
      ...prev,
      [script.chapter_id]: {
        script: script.script,
        scene_descriptions: script.scene_descriptions,
        characters: script.characters,
        character_details: script.character_details,
        script_style: script.script_style,
        script_id: script.id,
      },
    }));

    toast.success(
      `Selected ${script.script_style} script for video generation`
    );
  };

  // Update your useEffect to fetch scripts when chapter changes
  useEffect(() => {
    if (selectedChapter) {
      fetchGeneratedScripts(selectedChapter.id);
    }
  }, [selectedChapter]);

  // Load book data
  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = (await userService.getBook(bookId)) as Book;
      setBook(bookData);

      // Set first chapter as selected by default
      if (bookData.chapters && bookData.chapters.length > 0) {
        setSelectedChapter(bookData.chapters[0]);
      }
    } catch (error) {
      console.error("Error loading book:", error);
      toast.error("Failed to load book");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!selectedChapter) return;

    try {
      setVideoStatus("starting");

      // Check if we have a selected script
      if (!selectedScript) {
        toast.error("Please select a script first!");
        return;
      }

      // Use the enhanced service method
      const result = await userService.generateEntertainmentVideo(
        selectedChapter.id,
        "basic",
        animationStyle,
        selectedScript.id
      );

      // Store task info for monitoring
      setVideoGenerationId(result.video_generation_id);
      setAudioTaskId(result.audio_task_id || null);
      setTaskStatus(result.task_status || null);
      setVideoStatus("processing");

      toast.success(`Video generation started! ${result.message}`);

      // Start polling for status updates
      pollVideoStatus(result.video_generation_id);
    } catch (error) {
      console.error("Error generating video:", error);
      toast.error(error.message || "Failed to start video generation");
      setVideoStatus("error");
    }
  };

  useEffect(() => {
    if (selectedChapter) {
      fetchGeneratedScripts(selectedChapter.id);
      fetchExistingGenerations(); // ✅ Add this line
    }
  }, [selectedChapter]);

  // Add this useEffect to handle status changes

// Update the existing generations fetch to be more reliable
const fetchExistingGenerations = useCallback(async () => {
  if (!selectedChapter) return;

  try {
    console.log('[FETCH] Getting existing generations for chapter:', selectedChapter.id);
    const response = await videoGenerationAPI.getChapterVideoGenerations(selectedChapter.id);
    
    // ✅ Fix: Extract the generations array from the response
    const generations = response.generations || [];
    console.log('[FETCH] Found generations:', generations.length);
    
    setExistingGenerations(generations); // ✅ Now using the array
    
    // If we have generations, show them
    if (generations.length > 0) {
      setShowExistingGenerations(true);
    }
  } catch (error) {
    console.error("Error fetching existing generations:", error);
    // Even on error, show the generation interface
    setShowExistingGenerations(true);
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
   // Update the pollVideoStatus function:
  
  const pollVideoStatus = async (videoGenId: string) => {
  const checkStatus = async () => {
    try {
      const data = await userService.getVideoGenerationStatus(videoGenId);
      
      console.log('[POLLING] Status update:', data.generation_status);
      
      // Update video status immediately
      setVideoStatus(data.generation_status);
      
      // Also fetch pipeline status for detailed view
      try {
        const pipelineData = await aiService.getPipelineStatus(videoGenId);
        setPipelineStatus(pipelineData);
        
        // Force a re-render by updating a timestamp
        setLastUpdated(Date.now());
      } catch (pipelineError) {
        console.warn("Pipeline status not available:", pipelineError);
      }

      // Update task status if available
      if (data.task_metadata?.audio_task_state) {
        setTaskStatus(data.task_metadata.audio_task_state);
      }

      if (data.generation_status === "completed" && data.video_url) {
        setVideoUrls((prev) => ({
          ...prev,
          [selectedChapter!.id]: data.video_url!,
        }));
        toast.success("Video generation completed!");
        setShowPipelineStatus(false);
        setShowExistingGenerations(true);
        return;
      }

      if (data.generation_status === "failed") {
        toast.error(data.error_message || "Video generation failed");
        setShowExistingGenerations(true);
        // Force refresh of existing generations
        setTimeout(() => {
          fetchExistingGenerations();
        }, 1000);
        return;
      }

      // Continue polling if still processing
      if (
        [
          "pending",
          "generating_audio", 
          "audio_completed",           // ✅ Added
          "generating_images",
          "images_completed",          // ✅ Added  
          "generating_video",
          "video_completed",           // ✅ Added
          "combining",
          "merging_audio",
          "applying_lipsync",
        ].includes(data.generation_status)
      ) {
        setTimeout(checkStatus, 2000); // Poll every 2 seconds for faster updates
      } else {
        // Unknown status, show existing generations
        setShowExistingGenerations(true);
      }
    } catch (error) {
      console.error("Error checking status:", error);
      toast.error("Error checking video status");
      setShowExistingGenerations(true);
    }
  };

  checkStatus();
};
  const formatStatus = (status: string | null | undefined): string => {
    if (!status) return "Initializing";
    return status.replace(/_/g, " ");
  };

  const handleGenerateScript = async () => {
    if (!selectedChapter) return;
    setLoadingScript(true);
    try {
      const result = await userService.generateScriptAndScenes(
        selectedChapter.id,
        scriptStyle
      );

      // Update local state
      setAiScriptResults((prev) => ({
        ...prev,
        [selectedChapter.id]: result,
      }));

      // Refresh the scripts list
      await fetchGeneratedScripts(selectedChapter.id);

      toast.success("AI Script & Scene Descriptions generated!");
    } catch (error) {
      console.error("Error generating script:", error);
      toast.error("Failed to generate script/scene descriptions");
    } finally {
      setLoadingScript(false);
    }
  };

  // Add the retry handler function after your existing functions
  const handleRetry = async () => {
    if (!videoGenerationId) return;

    setIsLoading(true);
    try {
      // Call your retry API endpoint
      await aiService.retryVideoGeneration(videoGenerationId);

      // Show success message
      toast.success("Retrying video generation...");

      // Restart status polling
      pollVideoStatus(videoGenerationId);
    } catch (error) {
      console.error("Retry failed:", error);
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
      console.error("Failed to refresh status:", error);
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

  // Render chapter content
  const renderChapterContent = () => {
    const content = selectedChapter?.content || "";
    const maxChars = 70;

    if (content.length <= maxChars) {
      return <p className="text-gray-700">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700">
          {showFullScript ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFullScript(!showFullScript)}
          className="text-blue-600 hover:text-blue-800 text-sm mt-1"
        >
          {showFullScript ? "Show Less" : "Show More"}
        </button>
      </div>
    );
  };

  if (isLoading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  if (!book) {
    return <div className="p-8 text-center text-red-500">Book not found.</div>;
  }

  const currentVideoUrl = selectedChapter
    ? videoUrls[selectedChapter.id]
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            <img
              src={book.cover_image_url || ""}
              alt={book.title}
              className="w-16 h-20 object-cover rounded-lg shadow-md"
            />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{book.title}</h1>
              <p className="text-gray-600">by {book.author_name}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                  Entertainment
                </span>
                <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">
                  {book.difficulty}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Chapter List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Chapters ({book.total_chapters})
              </h2>
              <div className="space-y-2">
                {book.chapters?.map((chapter, index) => (
                  <button
                    key={chapter.id}
                    onClick={() => setSelectedChapter(chapter)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedChapter?.id === chapter.id
                        ? "bg-blue-50 border-blue-200 border"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">
                          {chapter.title}
                        </p>
                        <p className="text-sm text-gray-500">
                          Chapter {index + 1}
                        </p>
                      </div>
                      {videoScenes[chapter.id] && (
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border">
              {selectedChapter && (
                <div className="p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">
                    {selectedChapter.title}
                  </h2>
                  <div className="prose max-w-none text-gray-700 leading-relaxed">
                    {renderChapterContent()}
                  </div>
                  {/* Video Generation Controls */}
                  <div className="flex items-center gap-4 mt-6">
                    <div className="mb-4">
                      <label
                        htmlFor="script-style"
                        className="block text-sm font-medium text-gray-700 mb-1"
                      >
                        Script Style:
                      </label>
                      <select
                        id="script-style"
                        value={scriptStyle}
                        onChange={(e) => setScriptStyle(e.target.value)}
                        className="border rounded px-2 py-1"
                      >
                        <option value="cinematic_movie">
                          Cinematic Movie (character dialog)
                        </option>
                        <option value="cinematic_narration">
                          Cinematic Narration (voice-over)
                        </option>
                      </select>
                    </div>

                    <button
                      className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded mb-4"
                      onClick={handleGenerateScript}
                      disabled={loadingScript}
                    >
                      {loadingScript
                        ? "Generating..."
                        : "Generate Script & Scene"}
                    </button>

                    <div className="mb-4">
                      <label
                        htmlFor="script-style"
                        className="block text-sm font-medium text-gray-700 mb-1"
                      >
                        Video Style:
                      </label>
                      <select
                        className="border rounded-lg px-3 py-2 text-sm"
                        value={animationStyle}
                        onChange={(e) =>
                          setAnimationStyle(
                            e.target.value as
                              | "cartoon"
                              | "realistic"
                              | "cinematic"
                              | "fantasy"
                          )
                        }
                      >
                        <option value="cartoon">Cartoon Style</option>
                        <option value="realistic">Realistic Style</option>
                        <option value="cinematic">Cinematic Style</option>
                        <option value="fantasy">Fantasy Style</option>
                      </select>
                    </div>

                    <button
                      className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded mb-4"
                      onClick={handleGenerateVideo}
                    >
                      Generate Video
                    </button>
                  </div>
                  {/* Add the Generated Scripts Card to your JSX (place it afteryour script generation card) */}
                  {selectedChapter && (
                    <div className="bg-white p-6 rounded-lg shadow-md">
                      <h3 className="text-lg font-semibold mb-4 flex items-center">
                        <FileText className="mr-2" />
                        Generated Scripts
                      </h3>

                      {loadingScripts ? (
                        <div className="flex items-center justify-center py-4">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                          <span className="ml-2">Loading scripts...</span>
                        </div>
                      ) : generatedScripts.length === 0 ? (
                        <div className="text-gray-500 text-center py-4">
                          <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
                          <p>No scripts generated yet.</p>
                          <p className="text-sm">
                            Use "Generate Script & Scene" above to create your
                            first script.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {generatedScripts.map((script) => (
                            <div
                              key={script.id}
                              className={`border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                                selectedScript?.id === script.id
                                  ? "border-blue-500 bg-blue-50"
                                  : "border-gray-200 hover:border-gray-300"
                              }`}
                              onClick={() => handleSelectScript(script)}
                            >
                              <div className="flex justify-between items-start mb-2">
                                <div>
                                  <h4 className="font-medium text-gray-900">
                                    {script.script_style === "cinematic_movie"
                                      ? "Character Dialog"
                                      : "Voice-over Narration"}
                                  </h4>
                                  <p className="text-sm text-gray-500">
                                    Created:{" "}
                                    {new Date(
                                      script.created_at
                                    ).toLocaleDateString()}
                                  </p>
                                </div>
                                {selectedScript?.id === script.id && (
                                  <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                                    Selected
                                  </span>
                                )}
                              </div>

                              <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
                                <div>
                                  <span className="font-medium">Scenes:</span>{" "}
                                  {script.scene_descriptions?.length || 0}
                                </div>
                                <div>
                                  <span className="font-medium">
                                    Characters:
                                  </span>{" "}
                                  {script.characters?.length || 0}
                                </div>
                                <div>
                                  <span className="font-medium">Length:</span>{" "}
                                  {script.script?.length || 0} chars
                                </div>
                              </div>

                              {script.script && (
                                <div className="mt-2">
                                  <p className="text-sm text-gray-700 line-clamp-2">
                                    {script.script.substring(0, 150)}...
                                  </p>
                                </div>
                              )}

                              <div className="mt-2 flex items-center justify-between">
                                <span
                                  className={`text-xs px-2 py-1 rounded-full ${
                                    script.status === "ready"
                                      ? "bg-green-100 text-green-800"
                                      : "bg-yellow-100 text-yellow-800"
                                  }`}
                                >
                                  {script.status}
                                </span>

                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    // Preview script in modal or expand
                                    setSelectedScript(script);
                                  }}
                                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                >
                                  View Details
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {generatedScripts.length > 0 && (
                        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                          <p className="text-sm text-blue-800">
                            💡 <strong>Tip:</strong> Click on any script to
                            select it for video generation.
                            {selectedScript
                              ? ` Currently selected: ${selectedScript.script_style}`
                              : " No script selected yet."}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  {selectedChapter && showExistingGenerations && (
                    <div className="mt-6">
                      <ExistingGenerations
                        chapterId={selectedChapter.id}
                        onContinueGeneration={handleContinueGeneration}
                        onWatchVideo={handleWatchVideo}
                        className="mb-6"
                      />
                    </div>
                  )}
                  {/* Generated Video Display */}
                  {currentVideoUrl && (
                    <div className="mt-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">
                          Generated Video
                        </h3>
                        {/* <button
                          onClick={handleDeleteVideo}
                          className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600 transition-colors"
                        >
                          Delete Video
                        </button> */}
                      </div>

                      <video
                        src={currentVideoUrl}
                        controls
                        className="w-full h-64 object-cover rounded-lg"
                      />
                    </div>
                  )}
                  {/* Add Task Status Display after video generation controls */}
                  {audioTaskId && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">
                        Task Information
                      </h4>
                      <div className="text-sm space-y-1">
                        <div className="flex justify-between">
                          <span className="text-blue-700">Audio Task ID:</span>
                          <code className="text-blue-800 bg-blue-100 px-1 rounded">
                            {audioTaskId.substring(0, 12)}...
                          </code>
                        </div>
                        {taskStatus && (
                          <div className="flex justify-between">
                            <span className="text-blue-700">Task Status:</span>
                            <span className="text-blue-800 font-medium">
                              {taskStatus}
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-blue-700">
                            Generation Status:
                          </span>
                          <span className="text-blue-800 font-medium capitalize">
                            {formatStatus(videoStatus)}
                          </span>
                          {/* <span className="text-blue-800 font-medium capitalize">
                            {videoStatus.replace("_", " ")}
                          </span> */}
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Also add a video player modal for watching completed  videos: */}

                  {currentVideoToWatch && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
                      <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-lg font-semibold">
                            Generated Video
                          </h3>
                          <button
                            onClick={() => setCurrentVideoToWatch(null)}
                            className="text-gray-500 hover:text-gray-700"
                          >
                            ✕
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
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                          >
                            Download
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
                  {/* Enhanced Video Status Display - replace your existing video status display */}
                  {videoStatus !== "idle" && !currentVideoUrl && (
                    <>
                      {/* Basic Status Display */}
                      <div className="mt-6 p-4 bg-gray-50 border rounded-lg">
                        <div className="flex items-center gap-3">
                          {videoStatus === "starting" && (
                            <>
                              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>Initializing video generation...</span>
                            </>
                          )}
                          {videoStatus === "generating_audio" && (
                            <>
                              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>
                                Step 1/5: Generating audio and voices...
                              </span>
                            </>
                          )}
                          {videoStatus === "generating_images" && (
                            <>
                              <div className="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>
                                Step 2/5: Creating character images...
                              </span>
                            </>
                          )}
                          {videoStatus === "generating_video" && (
                            <>
                              <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>Step 3/5: Generating video scenes...</span>
                            </>
                          )}
                          {videoStatus === "merging_audio" && (
                            <>
                              <div className="w-4 h-4 border-2 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>Step 4/5: Merging audio and video...</span>
                            </>
                          )}
                          {videoStatus === "applying_lipsync" && (
                            <>
                              <div className="w-4 h-4 border-2 border-pink-600 border-t-transparent rounded-full animate-spin"></div>
                              <span>Step 5/5: Applying lip sync...</span>
                            </>
                          )}
                          {videoStatus === "failed" && (
                            <>
                              <div className="w-4 h-4 bg-red-500 rounded-full"></div>
                              <span className="text-red-600">
                                Generation failed. Please try again.
                              </span>
                            </>
                          )}
                        </div>

                        {audioTaskId && (
                          <div className="mt-2 text-xs text-gray-500">
                            Tracking ID: {audioTaskId.substring(0, 8)}...
                          </div>
                        )}

                        {/* Toggle for detailed pipeline view */}
                        {pipelineStatus && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <button
                              onClick={() =>
                                setShowPipelineStatus(!showPipelineStatus)
                              }
                              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                            >
                              {showPipelineStatus
                                ? "Hide Detailed Status"
                                : "Show Detailed Status"}
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Detailed Pipeline Status */}
                      {pipelineStatus && showPipelineStatus && (
                        <div className="mt-4">
                          <PipelineStatus
                            pipelineStatus={pipelineStatus}
                            isLoading={isLoading}
                            onRefresh={handleRefreshStatus}
                            onRetry={handleRetry}
                            className="border-t-4 border-t-blue-500"
                          />
                        </div>
                      )}
                    </>
                  )}
                  {/* AI Script & Scene Descriptions Display (separate from video) */}
                  {selectedChapter && aiScriptResults[selectedChapter.id] && (
                    <div className="mt-6 p-4 bg-gray-50 border rounded-lg">
                      <h4 className="font-semibold text-gray-800 mb-2">
                        AI-Generated Script
                      </h4>
                      <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-white p-2 rounded border mb-4 overflow-x-auto">
                        {aiScriptResults[selectedChapter.id].script ||
                          "No script available."}
                      </pre>
                      <h4 className="font-semibold text-gray-800 mb-2">
                        Scene Descriptions
                      </h4>
                      {aiScriptResults[selectedChapter.id].scene_descriptions &&
                      aiScriptResults[selectedChapter.id].scene_descriptions
                        .length > 0 ? (
                        <ul className="list-decimal list-inside text-gray-700">
                          {aiScriptResults[
                            selectedChapter.id
                          ].scene_descriptions.map((desc, idx) => (
                            <li key={idx} className="mb-1">
                              {desc}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-gray-600">
                          No scene descriptions available.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
