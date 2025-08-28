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

export default function BookViewForEntertainment() {
  const { id } = useParams<{ id: string }>();

  // State declarations - all hooks at the top level
  const [book, setBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [videoUrls, setVideoUrls] = useState<Record<string, string>>({});
  const [videoScenes, setVideoScenes] = useState<Record<string, VideoScene>>(
    {}
  );
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

  // Handle video generation
  const handleGenerateVideo = async () => {
    if (!selectedChapter) return;

    try {
      const result = await videoService.generateEntertainmentVideo(
        selectedChapter.id,
        animationStyle,
        scriptStyle
      );

      if (result.video_url) {
        setVideoUrls((prev) => ({
          ...prev,
          [selectedChapter.id]: result.video_url,
        }));

        setVideoScenes((prev) => ({
          ...prev,
          [selectedChapter.id]: result,
        }));

        toast.success("Video generated successfully!");
      }
    } catch (error) {
      console.error("Error generating video:", error);
      toast.error("Failed to generate video");
    }
  };

  const handleGenerateScript = async () => {
    if (!selectedChapter) return;
    setLoadingScript(true);
    try {
      const result = await videoService.generateScriptAndScenes(
        selectedChapter.id,
        scriptStyle
      );
      setAiScriptResults((prev) => ({
        ...prev,
        [selectedChapter.id]: result,
      }));
      toast.success("AI Script & Scene Descriptions generated!");
    } catch {
      toast.error("Failed to generate script/scene descriptions");
    } finally {
      setLoadingScript(false);
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
