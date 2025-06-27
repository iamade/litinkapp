import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { videoService, VideoScene } from "../services/videoService";
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

export default function BookView() {
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [videoStyle, setVideoStyle] = useState<"cartoon" | "realistic">(
    "realistic"
  );
  const [videoUrls, setVideoUrls] = useState<Record<string, string>>({});
  const [videoScenes, setVideoScenes] = useState<Record<string, VideoScene>>(
    {}
  );
  const [generating, setGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [scriptStyle, setScriptStyle] = useState<string>("screenplay");

  useEffect(() => {
    if (id) {
      loadBook(id);
    }
  }, [id]);

  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = (await userService.getBook(bookId)) as Book;
      setBook(bookData);
      if (bookData.chapters && bookData.chapters.length > 0) {
        setSelectedChapter(bookData.chapters[0]);
      }
    } catch (error) {
      console.error("Error loading book:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!book || !selectedChapter) return;

    setGenerating(true);
    try {
      let videoScene: VideoScene;

      if (book.book_type === "learning") {
        // Generate tutorial video for learning content
        videoScene = await videoService.generateTutorialVideo(
          selectedChapter.id,
          "udemy" // You can make this configurable
        );
      } else {
        // Generate entertainment video for story content
        videoScene = await videoService.generateEntertainmentVideo(
          selectedChapter.id,
          videoStyle
        );
      }

      // Store the full video scene data
      setVideoScenes((prev) => ({ ...prev, [selectedChapter.id]: videoScene }));

      // Also store the video URL for backward compatibility
      if (videoScene.video_url) {
        setVideoUrls((prev) => ({
          ...prev,
          [selectedChapter.id]: videoScene.video_url,
        }));
      }
    } catch (error) {
      console.error("Error generating video:", error);
      // Fallback to legacy method if RAG generation fails
      await handleLegacyVideoGeneration();
    } finally {
      setGenerating(false);
    }
  };

  const handleLegacyVideoGeneration = async () => {
    // Optionally show an error or fallback message, but do not use a mock video URL
    toast.error("Video generation failed. Please try again later.");
  };

  const handleDeleteVideo = async () => {
    if (!selectedChapter) return;
    if (
      !window.confirm(
        "Are you sure you want to delete this video? You can regenerate it later."
      )
    )
      return;
    try {
      // Remove video from state
      setVideoScenes((prev) => {
        const newScenes = { ...prev };
        delete newScenes[selectedChapter.id];
        return newScenes;
      });
      setVideoUrls((prev) => {
        const newUrls = { ...prev };
        delete newUrls[selectedChapter.id];
        return newUrls;
      });
      toast.success("Video deleted successfully");
    } catch (error) {
      console.error("Error deleting video:", error);
      toast.error("Failed to delete video");
    }
  };

  // Mock book data - in real app, fetch based on ID
  const bookData = {
    id: 1,
    title: "Introduction to Machine Learning",
    author: "Dr. Sarah Chen",
    type: "learning",
    progress: 45,
    totalChapters: 8,
    currentChapter: 3,
    image:
      "https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=400",
    description:
      "Learn the fundamentals of machine learning with interactive tutorials and real-world examples.",
  };

  // Determine if this is an entertainment book
  const isEntertainmentBook = id === "2" || id === "4" || id === "6";

  if (isEntertainmentBook) {
    bookData.title = "The Crystal Chronicles";
    bookData.author = "Elena Mystral";
    bookData.type = "entertainment";
    bookData.description =
      "An interactive fantasy adventure where your choices shape the story.";
  }

  if (isLoading) return <div className="p-8 text-center">Loading...</div>;
  if (!book)
    return <div className="p-8 text-center text-red-500">Book not found.</div>;

  const currentVideoScene = selectedChapter
    ? videoScenes[selectedChapter.id]
    : null;
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
              src={
                book.cover_image_url !== null
                  ? book.cover_image_url
                  : bookData.image || ""
              }
              alt={book.title}
              className="w-16 h-20 object-cover rounded-lg shadow-md"
            />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{book.title}</h1>
              <p className="text-gray-600">by {book.author_name}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    book.book_type === "learning"
                      ? "bg-blue-100 text-blue-800"
                      : "bg-purple-100 text-purple-800"
                  }`}
                >
                  {book.book_type === "learning" ? "Learning" : "Entertainment"}
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

          {/* Chapter Content */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border">
              {selectedChapter && (
                <>
                  {/* Video Section */}
                  {(currentVideoScene || currentVideoUrl) && (
                    <div className="p-6 border-b">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">
                          AI-Generated Video
                        </h3>
                        <button
                          onClick={handleDeleteVideo}
                          className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600 transition-colors"
                          title="Delete this video"
                        >
                          Delete Video
                        </button>
                      </div>
                      <div className="relative">
                        <video
                          src={
                            currentVideoScene?.video_url ||
                            currentVideoUrl ||
                            undefined
                          }
                          poster={currentVideoScene?.thumbnail_url}
                          controls
                          className="w-full h-64 object-cover rounded-lg"
                        />
                        {currentVideoScene && (
                          <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
                            RAG-Enhanced
                          </div>
                        )}
                      </div>
                      {currentVideoScene && (
                        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-2">
                            Video Details
                          </h4>
                          <div className="text-sm text-gray-600 space-y-1">
                            <p>
                              <strong>Duration:</strong>{" "}
                              {currentVideoScene.duration}s
                            </p>
                            <p>
                              <strong>Style:</strong>{" "}
                              {currentVideoScene.metadata?.style}
                            </p>
                            <p>
                              <strong>Status:</strong>{" "}
                              {currentVideoScene.status}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Chapter Content */}
                  <div className="p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">
                      {selectedChapter.title}
                    </h2>
                    <div className="prose max-w-none text-gray-700 leading-relaxed">
                      {selectedChapter.content}
                    </div>

                    {/* Video Generation Controls */}
                    <div className="flex items-center gap-4 mt-6">
                      <select
                        className="border rounded-lg px-3 py-2 text-sm"
                        value={videoStyle}
                        onChange={(e) =>
                          setVideoStyle(
                            e.target.value as "cartoon" | "realistic"
                          )
                        }
                        disabled={generating}
                      >
                        <option value="cartoon">Cartoon Style</option>
                        <option value="realistic">Realistic Style</option>
                      </select>
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
                          <option value="screenplay">
                            Screenplay (character dialog)
                          </option>
                          <option value="narration">Narration (prose)</option>
                        </select>
                      </div>
                      {/* Place Generate Scene button directly under the dropdowns */}
                      <button
                        className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded mb-4"
                        onClick={handleGenerateVideo}
                        disabled={generating}
                      >
                        {generating ? "Generating..." : "Generate Scene"}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
