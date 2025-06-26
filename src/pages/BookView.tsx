import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { videoService } from "../services/videoService";
import { aiService } from "../services/aiService";

interface Chapter {
  id: string;
  title: string;
  content: string;
}

interface Book {
  id: string;
  title: string;
  author_name?: string;
  book_type: "learning" | "entertainment";
  progress: number;
  totalChapters: number;
  currentChapter: number;
  image: string;
  description: string;
}

export default function BookView() {
  const { id } = useParams();
  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(
    null
  );
  const [videoUrls, setVideoUrls] = useState<{ [chapterId: string]: string }>(
    {}
  );
  const [generating, setGenerating] = useState(false);
  const [videoStyle, setVideoStyle] = useState<"cartoon" | "realistic">(
    "cartoon"
  );

  useEffect(() => {
    async function fetchBookAndChapters() {
      setIsLoading(true);
      try {
        const bookData = await userService.getBook(id!);
        setBook(bookData as Book);
        const chapterData = await userService.getChapters(id!);
        if (Array.isArray(chapterData)) {
          setChapters(chapterData as Chapter[]);
          if (chapterData.length > 0) {
            setSelectedChapterId(chapterData[0].id);
          }
        } else {
          setChapters([]);
        }
      } catch {
        // handle error
      } finally {
        setIsLoading(false);
      }
    }
    if (id) fetchBookAndChapters();
  }, [id]);

  const selectedChapter =
    chapters.find((ch) => ch.id === selectedChapterId) || null;

  const handleGenerateVideo = async () => {
    if (!book || !selectedChapter) return;
    setGenerating(true);
    let script = selectedChapter.content;
    const platformStyle = book.book_type === "learning" ? "udemy" : "youtube";
    if (book.book_type === "learning") {
      script = await aiService.generateText(
        `Rewrite the following chapter as a ${platformStyle}-style tutorial script for a ${videoStyle} video: ${selectedChapter.title}\n${selectedChapter.content}`
      );
    } else {
      script = await aiService.generateText(
        `Rewrite the following chapter as a ${platformStyle}-style animated scene script for a ${videoStyle} video: ${selectedChapter.title}\n${selectedChapter.content}`
      );
    }
    const videoUrl = await videoService.generateVideo(script, videoStyle);
    setVideoUrls((prev) => ({ ...prev, [selectedChapter.id]: videoUrl }));
    setGenerating(false);
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="h-6 w-px bg-gray-300"></div>
              <h1 className="text-lg font-semibold text-gray-900 truncate">
                {book.title}
              </h1>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Progress: {book.progress}%
              </div>
              <div className="w-32 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    isEntertainmentBook
                      ? "bg-gradient-to-r from-purple-500 to-pink-600"
                      : "bg-gradient-to-r from-green-500 to-blue-600"
                  }`}
                  style={{ width: `${book.progress}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Chapter List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 sticky top-24">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                {book.book_type === "entertainment"
                  ? "Story Chapters"
                  : "Chapters"}
              </h2>
              <div className="space-y-2">
                {chapters.map((chapter) => (
                  <button
                    key={chapter.id}
                    onClick={() => setSelectedChapterId(chapter.id)}
                    className={`w-full text-left p-3 rounded-xl transition-all ${
                      selectedChapterId === chapter.id
                        ? "bg-purple-50 border-2 border-purple-200"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center ${
                          selectedChapterId === chapter.id
                            ? "bg-purple-500"
                            : "bg-gray-300"
                        }`}
                      >
                        <span className="text-xs font-medium text-white">
                          {chapter.title[0]}
                        </span>
                      </div>
                      <div>
                        <p
                          className={`text-sm font-medium ${
                            selectedChapterId === chapter.id
                              ? "text-purple-900"
                              : "text-gray-900"
                          }`}
                        >
                          {chapter.title}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
          {/* Main Content */}
          <div className="lg:col-span-3">
            {selectedChapter && (
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                <div
                  className={`p-6 text-white ${
                    book.book_type === "entertainment"
                      ? "bg-gradient-to-r from-purple-600 to-pink-600"
                      : "bg-gradient-to-r from-purple-600 to-blue-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-2xl font-bold mb-2">
                        {selectedChapter.title}
                      </h1>
                    </div>
                  </div>
                </div>
                <div className="p-8">
                  <div className="prose max-w-none">
                    <p className="text-gray-700 mb-6 leading-relaxed">
                      {selectedChapter.content}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 mt-6">
                    <select
                      className="border rounded-lg px-3 py-2 text-sm"
                      value={videoStyle}
                      onChange={(e) =>
                        setVideoStyle(e.target.value as "cartoon" | "realistic")
                      }
                      disabled={generating}
                    >
                      <option value="cartoon">Cartoon Style</option>
                      <option value="realistic">Realistic Style</option>
                    </select>
                    {book.book_type === "learning" ? (
                      <button
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        onClick={handleGenerateVideo}
                        disabled={generating}
                      >
                        {generating
                          ? "Generating Tutorial..."
                          : "Generate Tutorial"}
                      </button>
                    ) : (
                      <button
                        className="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:opacity-50"
                        onClick={handleGenerateVideo}
                        disabled={generating}
                      >
                        {generating ? "Generating Scene..." : "Generate Scene"}
                      </button>
                    )}
                  </div>
                  <div className="mt-6">
                    {videoUrls[selectedChapter.id] ? (
                      <video controls className="w-full rounded-lg">
                        <source
                          src={videoUrls[selectedChapter.id]}
                          type="video/mp4"
                        />
                        Your browser does not support the video tag.
                      </video>
                    ) : (
                      <div className="text-gray-400 text-sm">
                        No video generated yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
