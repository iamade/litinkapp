import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { videoService } from "../services/videoService";
import { toast } from "react-hot-toast";

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

interface LearningContent {
  id: string;
  type: "audio" | "video";
  title: string;
  content_url: string;
  duration: number;
  status: string;
  chapter_id: string;
  tavus_url?: string;
}

export default function BookViewForLearning() {
  const { id } = useParams<{ id: string }>();

  // State declarations - all hooks at the top level
  const [book, setBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [learningContent, setLearningContent] = useState<
    Record<string, LearningContent>
  >({});
  const [currentLearningContent, setCurrentLearningContent] =
    useState<LearningContent | null>(null);
  const [showFullContent, setShowFullContent] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Helper to lock buttons if any content is processing or loading
  const isLocked =
    !!audioLoading ||
    !!videoLoading ||
    (selectedChapter &&
      Object.values(learningContent).some(
        (c) => c.chapter_id === selectedChapter.id && c.status === "processing"
      ));

  // Load book data
  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = await userService.getBook(bookId);
      if (bookData && typeof bookData === "object") {
        setBook(bookData as Book);
        // Set first chapter as selected by default
        if (
          (bookData as Book).chapters &&
          (bookData as Book).chapters.length > 0
        ) {
          setSelectedChapter((bookData as Book).chapters[0]);
          // Load learning content for the first chapter
          await loadLearningContent((bookData as Book).chapters[0].id);
        }
      }
    } catch (error) {
      toast.error("Failed to load book");
    } finally {
      setIsLoading(false);
    }
  };

  // Load learning content for a chapter
  const loadLearningContent = async (chapterId: string) => {
    try {
      const response = await videoService.getLearningContent(chapterId);

      // Update learning content state
      const newLearningContent: Record<string, LearningContent> = {};

      response.content.forEach((item) => {
        if (
          item.content_type === "realistic_video" &&
          item.status === "ready" &&
          item.content_url
        ) {
          newLearningContent[chapterId] = {
            id: item.id,
            type: "video",
            title: "Realistic Video",
            content_url: item.content_url,
            duration: item.duration,
            status: item.status,
            chapter_id: chapterId,
          };

          // Set video URL for immediate display
          setVideoUrl(item.content_url);
        } else if (
          item.content_type === "audio_narration" &&
          item.status === "ready" &&
          item.content_url
        ) {
          // Set audio URL for immediate display
          setAudioUrl(item.content_url);
        }
      });

      setLearningContent((prev) => ({
        ...prev,
        ...newLearningContent,
      }));
    } catch (error) {
    }
  };

  // Handle chapter selection
  const handleChapterSelect = async (chapter: Chapter) => {
    setSelectedChapter(chapter);
    setVideoUrl(null); // Clear current video
    setAudioUrl(null); // Clear current audio
    setVideoError(null);
    setAudioError(null);
    setVideoLoading(false);
    setAudioLoading(false);

    // Load learning content for the selected chapter
    await loadLearningContent(chapter.id);
  };

  // Handle realistic video generation
  const handleRealisticVideo = async () => {
    if (!selectedChapter) return;

    setVideoLoading(true);
    setVideoError(null);

    try {
      const result = await videoService.generateRealisticVideo(
        selectedChapter.id
      );

      if (
        result.status === "ready" &&
        (result.content_url || result.video_url)
      ) {
        setVideoUrl((result.content_url || result.video_url) ?? null);
        setVideoLoading(false);
        toast.success("Realistic video generated successfully!");
      } else if (result.status === "processing") {
        setVideoLoading(true);
        pollVideoStatus(result.id);
      } else {
        setVideoError(result.error_message || "Failed to generate video");
        setVideoLoading(false);
        toast.error("Failed to generate realistic video");
      }
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to generate video";
      setVideoError(errorMessage);
      setVideoLoading(false);
      toast.error("Failed to generate realistic video");
    }
  };

  // Poll video status
  const pollVideoStatus = async (contentId: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await videoService.checkVideoStatus(contentId);

        if (
          status.status === "ready" &&
          (status.content_url || status.video_url)
        ) {
          setVideoUrl((status.content_url || status.video_url) ?? null);
          setVideoLoading(false);
          toast.success("Realistic video generated successfully!");
          return;
        } else if (status.status === "completed_no_download") {
          setVideoError("Video completed but no downloadable URL found");
          setVideoLoading(false);
          toast.error("Video completed but no downloadable URL found");
          return;
        } else if (status.status === "failed") {
          setVideoError(status.error_message || "Video generation failed");
          setVideoLoading(false);
          toast.error("Video generation failed");
          return;
        } else if (status.status === "timeout") {
          setVideoError("Video generation timed out. Please try again.");
          setVideoLoading(false);
          toast.error("Video generation timed out");
          return;
        } else if (
          status.status === "processing" &&
          status.tavus_url &&
          !status.content_url &&
          !status.video_url
        ) {
          // Show a message and keep polling
          setVideoError(
            "Video is being created. You can preview the hosted link below, but the downloadable video will appear here when ready."
          );
          setVideoLoading(true);
          // Optionally, you could set a fallback link to status.tavus_url
        }

        attempts++;
        if (attempts < maxAttempts) {
          const interval = attempts < 10 ? 10000 : 30000; // 10s for first 10, then 30s
          setTimeout(poll, interval);
        } else {
          setVideoError(
            "Video generation is taking longer than expected. Please check back later."
          );
          setVideoLoading(false);
          toast.error("Video generation is taking longer than expected");
        }
      } catch (error: unknown) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Error checking video status";
        setVideoError(errorMessage);
        setVideoLoading(false);
        toast.error("Error checking video status");
      }
    };

    poll();
  };

  // Handle audio narration
  const handleAudioNarration = async () => {
    if (!selectedChapter) return;

    setAudioLoading(true);
    setAudioError(null);
    setAudioUrl(null);

    try {
      const result = await videoService.generateAudioNarration(
        selectedChapter.id
      );

      if (result.status === "ready" && result.audio_url) {
        setAudioUrl(result.audio_url ?? null);
        setAudioLoading(false);
        toast.success("Audio narration generated successfully!");
      } else if (result.status === "failed") {
        setAudioError(
          result.error_message || "Failed to generate audio narration"
        );
        setAudioLoading(false);
        toast.error("Failed to generate audio narration");
      } else {
        setAudioError("Audio generation failed");
        setAudioLoading(false);
        toast.error("Failed to generate audio narration");
      }
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to generate audio";
      setAudioError(errorMessage);
      setAudioLoading(false);
      toast.error(errorMessage);
    }
  };

  // Update current learning content when selected chapter changes
  useEffect(() => {
    if (selectedChapter) {
      setCurrentLearningContent(learningContent[selectedChapter.id] || null);
    } else {
      setCurrentLearningContent(null);
    }
  }, [selectedChapter, learningContent]);

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
      return <p className="text-gray-700 dark:text-gray-300">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700 dark:text-gray-300">
          {showFullContent ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFullContent(!showFullContent)}
          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm mt-1"
        >
          {showFullContent ? "Show Less" : "Show More"}
        </button>
      </div>
    );
  };

  if (isLoading) {
    return <div className="p-8 text-center text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-[#0F0F23] min-h-screen">Loading...</div>;
  }

  if (!book) {
    return <div className="p-8 text-center text-red-500 bg-gray-50 dark:bg-[#0F0F23] min-h-screen">Book not found.</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0F0F23] transition-colors duration-300">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            <img
              src={book.cover_image_url || ""}
              alt={book.title}
              className="w-16 h-20 object-cover rounded-lg shadow-md"
            />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{book.title}</h1>
              <p className="text-gray-600 dark:text-gray-400">by {book.author_name}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 rounded-full">
                  Learning
                </span>
                <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 rounded-full">
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
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Chapters ({book.total_chapters})
              </h2>
              <div className="space-y-2">
                {book.chapters?.map((chapter, index) => (
                  <button
                    key={chapter.id}
                    onClick={() => handleChapterSelect(chapter)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedChapter?.id === chapter.id
                        ? "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 border"
                        : "hover:bg-gray-50 dark:hover:bg-gray-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {chapter.title}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Chapter {index + 1}
                        </p>
                      </div>
                      {learningContent[chapter.id] && (
                        <div className="flex items-center space-x-1">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <span className="text-xs text-green-600 dark:text-green-400">
                            {learningContent[chapter.id].type === "video"
                              ? "🎬"
                              : "🎵"}
                          </span>
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
              {selectedChapter && (
                <div className="p-6">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                    {selectedChapter.title}
                  </h2>
                  <div className="prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 leading-relaxed">
                    {renderChapterContent()}
                  </div>

                  {/* Learning Content Generation Controls */}
                  <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      Generate Learning Content
                    </h3>

                    <div className="space-y-4">
                      <div className="flex items-center space-x-4">
                        <button
                          onClick={handleAudioNarration}
                          disabled={!!isLocked}
                          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        >
                          {audioLoading ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          ) : (
                            <span>🎵</span>
                          )}
                          <span>Audio Narration</span>
                        </button>

                        <button
                          onClick={handleRealisticVideo}
                          disabled={!!isLocked}
                          className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                        >
                          {videoLoading ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          ) : (
                            <span>🎬</span>
                          )}
                          <span>Realistic Video</span>
                        </button>
                      </div>

                      {videoError && (
                        <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                          {videoError}
                        </div>
                      )}

                      {audioError && (
                        <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                          {audioError}
                        </div>
                      )}

                      {videoUrl && (
                        <div className="mt-4">
                          <h4 className="text-lg font-semibold mb-2">
                            Generated Video:
                          </h4>
                          <video
                            controls
                            className="w-full max-w-2xl rounded-lg shadow-lg"
                            src={videoUrl}
                          >
                            Your browser does not support the video tag.
                          </video>
                        </div>
                      )}

                      {audioUrl && (
                        <div className="mt-4">
                          <h4 className="text-lg font-semibold mb-2">
                            Generated Audio Narration:
                          </h4>
                          <audio
                            controls
                            className="w-full max-w-2xl"
                            src={audioUrl}
                          >
                            Your browser does not support the audio tag.
                          </audio>
                        </div>
                      )}

                      {learningContent[selectedChapter.id] && !videoUrl && (
                        <div className="mt-4 p-3 bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300 rounded">
                          <p>
                            Video content exists for this chapter but is not
                            currently loaded.
                          </p>
                          <button
                            onClick={() =>
                              setVideoUrl(
                                learningContent[selectedChapter.id].content_url
                              )
                            }
                            className="mt-2 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                          >
                            Load Video
                          </button>
                        </div>
                      )}

                      {videoError &&
                        currentLearningContent &&
                        currentLearningContent.status === "processing" &&
                        currentLearningContent.tavus_url && (
                          <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-400 dark:border-yellow-600 text-yellow-800 dark:text-yellow-300 rounded mt-2">
                            <span>
                              The video is still being processed. You can
                              preview the hosted video here (may not be ready):{" "}
                              <a
                                href={currentLearningContent.tavus_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline text-blue-700 dark:text-blue-400"
                              >
                                Hosted Video Link
                              </a>
                            </span>
                          </div>
                        )}
                    </div>

                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-4">
                      <p className="mb-2">
                        <strong>Audio Narration:</strong> ElevenLabs AI
                        teaching/narrating an audio tutorial based on RAG
                        embeddings
                      </p>
                      <p>
                        <strong>Realistic Video:</strong> Tavus AI as a
                        teacher/tutor teaching a tutorial based on RAG
                        embeddings
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
