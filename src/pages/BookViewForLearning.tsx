import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
}

export default function BookViewForLearning() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

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
  const [isLoading, setIsLoading] = useState(true);

  // Load book data
  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = await userService.getBook(bookId);
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

  // Handle realistic video generation
  const handleRealisticVideo = async () => {
    if (!selectedChapter) return;

    setVideoLoading(true);
    setVideoError(null);

    try {
      const result = await videoService.generateRealisticVideo(
        selectedChapter.id
      );

      if (result.status === "ready" && result.video_url) {
        setVideoUrl(result.video_url);
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
      console.error("Error generating realistic video:", error);
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

        if (status.status === "ready" && status.video_url) {
          setVideoUrl(status.video_url);
          setVideoLoading(false);
          toast.success("Realistic video generated successfully!");
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
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          setVideoError(
            "Video generation is taking longer than expected. Please check back later."
          );
          setVideoLoading(false);
          toast.error("Video generation is taking longer than expected");
        }
      } catch (error: unknown) {
        console.error("Error polling video status:", error);
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
    try {
      // TODO: Implement audio narration generation
      toast.success("Audio narration feature coming soon!");
    } catch (error: unknown) {
      console.error("Error generating audio narration:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Failed to generate audio";
      toast.error(errorMessage);
    } finally {
      setAudioLoading(false);
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
      return <p className="text-gray-700">{content}</p>;
    }

    return (
      <div>
        <p className="text-gray-700">
          {showFullContent ? content : `${content.substring(0, maxChars)}...`}
        </p>
        <button
          onClick={() => setShowFullContent(!showFullContent)}
          className="text-blue-600 hover:text-blue-800 text-sm mt-1"
        >
          {showFullContent ? "Show Less" : "Show More"}
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
                <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                  Learning
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
                      {learningContent[chapter.id] && (
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

                  {/* Learning Content Generation Controls */}
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Generate Learning Content
                    </h3>

                    <div className="space-y-4">
                      <div className="flex items-center space-x-4">
                        <button
                          onClick={handleAudioNarration}
                          disabled={audioLoading}
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
                          disabled={videoLoading}
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
                    </div>

                    <div className="text-sm text-gray-600 mt-4">
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
