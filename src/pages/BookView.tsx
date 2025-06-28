import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { videoService, VideoScene } from "../services/videoService";
import { toast } from "react-hot-toast";

// Service Content Display Component
interface ServiceContentDisplayProps {
  content: string;
  maxChars: number;
}

const ServiceContentDisplay: React.FC<ServiceContentDisplayProps> = ({
  content,
  maxChars,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const shouldTruncate = content.length > maxChars;
  const displayContent = isExpanded ? content : content.substring(0, maxChars);

  return (
    <div className="bg-white rounded border p-3">
      <div className="text-sm text-gray-800 whitespace-pre-wrap">
        {displayContent}
        {shouldTruncate && !isExpanded && "..."}
      </div>
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          {isExpanded ? "Show Less" : "Show More"}
        </button>
      )}
    </div>
  );
};

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
  const [videoUrls, setVideoUrls] = useState<Record<string, string>>({});
  const [videoScenes, setVideoScenes] = useState<Record<string, VideoScene>>(
    {}
  );
  const [isLoading, setIsLoading] = useState(true);
  const [scriptStyle, setScriptStyle] = useState<string>("cinematic_movie");
  const [animationStyle, setAnimationStyle] = useState<string>("animated");
  const [currentVideoScene, setCurrentVideoScene] = useState<VideoScene | null>(
    null
  );
  const [showFullScript, setShowFullScript] = useState(false);

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
    if (!selectedChapter) return;

    try {
      const result = await videoService.generateEntertainmentVideo(
        selectedChapter.id,
        animationStyle,
        scriptStyle
      );
      setCurrentVideoScene(result);
      console.log("Video generation result:", result);
    } catch (error) {
      console.error("Error generating video:", error);
    }
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

  const currentVideoUrl = selectedChapter
    ? videoUrls[selectedChapter.id]
    : null;

  // Chapter content display with reduced character limit
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

  // Full script display with Show More/Show Less
  const renderFullScript = () => {
    if (!currentVideoScene?.script) return null;

    const script = currentVideoScene.script;
    const maxChars = 200;

    return (
      <div className="bg-gray-50 p-4 rounded-lg mb-4">
        <h4 className="font-semibold text-gray-800 mb-2">Generated Script</h4>
        <div className="text-sm text-gray-700">
          {script.length <= maxChars ? (
            <pre className="whitespace-pre-wrap">{script}</pre>
          ) : (
            <div>
              <pre className="whitespace-pre-wrap">
                {showFullScript
                  ? script
                  : `${script.substring(0, maxChars)}...`}
              </pre>
              <button
                onClick={() => setShowFullScript(!showFullScript)}
                className="text-blue-600 hover:text-blue-800 text-sm mt-2"
              >
                {showFullScript ? "Show Less" : "Show More"}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Character list display
  const renderCharacters = () => {
    if (
      !currentVideoScene?.characters ||
      currentVideoScene.characters.length === 0
    )
      return null;

    return (
      <div className="bg-blue-50 p-4 rounded-lg mb-4">
        <h4 className="font-semibold text-blue-800 mb-2">
          Characters in Script
        </h4>
        <div className="flex flex-wrap gap-2">
          {currentVideoScene.characters.map(
            (character: string, index: number) => (
              <span
                key={index}
                className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm"
              >
                {character}
              </span>
            )
          )}
        </div>
      </div>
    );
  };

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
                              {((
                                currentVideoScene.metadata as Record<
                                  string,
                                  unknown
                                >
                              )?.style as string) || "Unknown"}
                            </p>
                            <p>
                              <strong>Status:</strong>{" "}
                              {currentVideoScene.status}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Service Inputs Display */}
                      {currentVideoScene?.service_inputs && (
                        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-3">
                            AI Service Inputs
                          </h4>
                          <div className="space-y-4">
                            {/* ElevenLabs Input */}
                            <div className="border-l-4 border-green-500 pl-4">
                              <h5 className="font-medium text-green-700 mb-2">
                                🎤 ElevenLabs (Audio Generation)
                              </h5>
                              <p className="text-sm text-gray-600 mb-2">
                                Content Type:{" "}
                                {
                                  currentVideoScene.service_inputs.elevenlabs
                                    .content_type
                                }
                              </p>
                              <p className="text-sm text-gray-600 mb-2">
                                Character Count:{" "}
                                {
                                  currentVideoScene.service_inputs.elevenlabs
                                    .character_count
                                }
                              </p>
                              <ServiceContentDisplay
                                content={
                                  currentVideoScene.service_inputs.elevenlabs
                                    .content
                                }
                                maxChars={170}
                              />
                            </div>

                            {/* KlingAI Input */}
                            <div className="border-l-4 border-purple-500 pl-4">
                              <h5 className="font-medium text-purple-700 mb-2">
                                🎬 KlingAI (Video Generation)
                              </h5>
                              <p className="text-sm text-gray-600 mb-2">
                                Content Type:{" "}
                                {
                                  currentVideoScene.service_inputs.klingai
                                    .content_type
                                }
                              </p>
                              <p className="text-sm text-gray-600 mb-2">
                                Character Count:{" "}
                                {
                                  currentVideoScene.service_inputs.klingai
                                    .character_count
                                }
                              </p>
                              <ServiceContentDisplay
                                content={
                                  currentVideoScene.service_inputs.klingai
                                    .content
                                }
                                maxChars={170}
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Full Script Display */}
                      {renderFullScript()}

                      {/* Characters Display */}
                      {renderCharacters()}

                      {/* Character Details */}
                      {currentVideoScene?.character_details && (
                        <div className="mt-4 p-4 bg-green-50 rounded-lg">
                          <h4 className="font-medium text-green-800 mb-2">
                            Character Details
                          </h4>
                          <p className="text-sm text-green-700">
                            {currentVideoScene.character_details}
                          </p>
                        </div>
                      )}

                      {/* Parsed Script Sections (Debug) */}
                      {currentVideoScene?.parsed_sections && (
                        <div className="mt-4 p-4 bg-yellow-50 rounded-lg">
                          <h4 className="font-medium text-yellow-800 mb-2">
                            Parsed Script Sections
                          </h4>
                          <div className="space-y-3">
                            {currentVideoScene.parsed_sections
                              .scene_descriptions && (
                              <div>
                                <h5 className="font-medium text-yellow-700 text-sm">
                                  Scene Descriptions (KlingAI):
                                </h5>
                                <div className="text-xs text-yellow-600 bg-yellow-100 p-2 rounded max-h-32 overflow-y-auto">
                                  {currentVideoScene.parsed_sections.scene_descriptions.map(
                                    (desc: string, index: number) => (
                                      <div key={index} className="mb-1">
                                        • {desc}
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
                            {currentVideoScene.parsed_sections
                              .narrator_dialogue && (
                              <div>
                                <h5 className="font-medium text-yellow-700 text-sm">
                                  Narrator Dialogue (ElevenLabs):
                                </h5>
                                <div className="text-xs text-yellow-600 bg-yellow-100 p-2 rounded max-h-32 overflow-y-auto">
                                  {currentVideoScene.parsed_sections.narrator_dialogue.map(
                                    (dialogue: string, index: number) => (
                                      <div key={index} className="mb-1">
                                        • "{dialogue}"
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
                            {currentVideoScene.parsed_sections
                              .character_dialogue && (
                              <div>
                                <h5 className="font-medium text-yellow-700 text-sm">
                                  Character Dialogue (ElevenLabs):
                                </h5>
                                <div className="text-xs text-yellow-600 bg-yellow-100 p-2 rounded max-h-32 overflow-y-auto">
                                  {currentVideoScene.parsed_sections.character_dialogue.map(
                                    (dialogue: string, index: number) => (
                                      <div key={index} className="mb-1">
                                        • "{dialogue}"
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
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
                      {renderChapterContent()}
                    </div>

                    {/* Video Generation Controls */}
                    <div className="flex items-center gap-4 mt-6">
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
                        className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded mb-4"
                        onClick={handleGenerateVideo}
                      >
                        Generate Scene
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
