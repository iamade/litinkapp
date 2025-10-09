import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { BookOpen, Film, Music, Sparkles, Wand2 } from "lucide-react";
import { toast } from "react-hot-toast";

export default function CreatorMode() {
  const { user } = useAuth();
  const [bookPrompt, setBookPrompt] = useState("");
  const [scriptPrompt, setScriptPrompt] = useState("");
  const [videoPrompt, setVideoPrompt] = useState("");
  const [generating, setGenerating] = useState<string | null>(null);

  if (!user || user.role !== "author") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">Author access required for Creator Mode</p>
          <p className="text-gray-500">Please sign in as an author to create content.</p>
        </div>
      </div>
    );
  }

  const handleGenerateBook = async () => {
    if (!bookPrompt.trim()) {
      toast.error("Please enter a prompt for the book.");
      return;
    }
    setGenerating("book");
    try {
      // TODO: Integrate with backend service for book generation
      // await bookService.generateBook(bookPrompt);
      toast.success("Book generation started! Check your dashboard for progress.");
      setBookPrompt("");
    } catch {
      toast.error("Failed to generate book. Please try again.");
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateScript = async () => {
    if (!scriptPrompt.trim()) {
      toast.error("Please enter a prompt for the script.");
      return;
    }
    setGenerating("script");
    try {
      // TODO: Integrate with backend service for script generation
      // await scriptService.generateScript(scriptPrompt);
      toast.success("Script generation started! Check your dashboard for progress.");
      setScriptPrompt("");
    } catch {
      toast.error("Failed to generate script. Please try again.");
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateVideo = async () => {
    if (!videoPrompt.trim()) {
      toast.error("Please enter a prompt for the video.");
      return;
    }
    setGenerating("video");
    try {
      // TODO: Integrate with backend service for video generation
      // await videoService.generateVideo(videoPrompt);
      toast.success("Video generation started! Check your dashboard for progress.");
      setVideoPrompt("");
    } catch {
      toast.error("Failed to generate video. Please try again.");
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4 flex items-center justify-center">
            <Wand2 className="h-10 w-10 text-purple-600 mr-3" />
            Creator Mode
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Unleash your creativity with AI-powered content generation. Create books, scripts, and videos
            by providing prompts and letting our advanced AI bring your ideas to life.
          </p>
        </div>

        {/* Content Creation Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Books Section */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mr-4">
                <BookOpen className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Create Books</h2>
                <p className="text-sm text-gray-600">Generate interactive books with AI</p>
              </div>
            </div>
            <div className="space-y-4">
              <textarea
                value={bookPrompt}
                onChange={(e) => setBookPrompt(e.target.value)}
                placeholder="Describe your book idea... (e.g., 'A fantasy adventure about a young wizard discovering ancient magic in a hidden forest')"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                rows={4}
              />
              <button
                onClick={handleGenerateBook}
                disabled={generating === "book"}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-4 rounded-xl font-medium hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {generating === "book" ? (
                  <div className="flex items-center justify-center">
                    <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </div>
                ) : (
                  "Generate Book"
                )}
              </button>
            </div>
          </div>

          {/* Scripts Section */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-blue-600 rounded-xl flex items-center justify-center mr-4">
                <Film className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Create Scripts</h2>
                <p className="text-sm text-gray-600">Write movie scripts with AI assistance</p>
              </div>
            </div>
            <div className="space-y-4">
              <textarea
                value={scriptPrompt}
                onChange={(e) => setScriptPrompt(e.target.value)}
                placeholder="Describe your script idea... (e.g., 'A thriller about a detective solving a mystery in a futuristic city')"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                rows={4}
              />
              <button
                onClick={handleGenerateScript}
                disabled={generating === "script"}
                className="w-full bg-gradient-to-r from-green-600 to-blue-600 text-white py-3 px-4 rounded-xl font-medium hover:from-green-700 hover:to-blue-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {generating === "script" ? (
                  <div className="flex items-center justify-center">
                    <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </div>
                ) : (
                  "Generate Script"
                )}
              </button>
            </div>
          </div>

          {/* Videos Section */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center mr-4">
                <Music className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Create Videos</h2>
                <p className="text-sm text-gray-600">Produce film or music videos with AI</p>
              </div>
            </div>
            <div className="space-y-4">
              <textarea
                value={videoPrompt}
                onChange={(e) => setVideoPrompt(e.target.value)}
                placeholder="Describe your video idea... (e.g., 'A music video for a pop song featuring dancers in a neon-lit cityscape')"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                rows={4}
              />
              <button
                onClick={handleGenerateVideo}
                disabled={generating === "video"}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-4 rounded-xl font-medium hover:from-purple-700 hover:to-pink-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {generating === "video" ? (
                  <div className="flex items-center justify-center">
                    <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </div>
                ) : (
                  "Generate Video"
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="mt-12 bg-gradient-to-r from-purple-50 to-blue-50 rounded-2xl p-8 text-center">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">How It Works</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-purple-600">1</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Enter Your Prompt</h4>
              <p className="text-gray-600">Describe your creative idea in detail to guide the AI generation process.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-blue-600">2</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">AI Generation</h4>
              <p className="text-gray-600">Our advanced AI processes your prompt and creates high-quality content.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-green-600">3</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Review & Publish</h4>
              <p className="text-gray-600">Review the generated content and publish it to share with your audience.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}