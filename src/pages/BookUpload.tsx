import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import {
  Upload,
  FileText,
  Brain,
  Sparkles,
  Settings,
  ArrowRight,
  Book,
  CheckCircle,
} from "lucide-react";
import { apiClient } from "../lib/api";

// Define Book type based on backend BookSchema
interface Book {
  id: string;
  title: string;
  author_name: string;
  description: string;
  // add other fields as needed
}

export default function BookUpload() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [uploadMethod, setUploadMethod] = useState<"file" | "text">("file");
  const [bookMode, setBookMode] = useState<"learning" | "entertainment">(
    "learning"
  );
  const [file, setFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [aiBook, setAiBook] = useState<Book | null>(null);
  const [details, setDetails] = useState({
    title: "",
    author_name: "",
    description: "",
  });
  const [saving, setSaving] = useState(false);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">Sign in required</p>
        </div>
      </div>
    );
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  // Step 3: AI Processing
  const handleProcessAI = async () => {
    setIsProcessing(true);
    setAiBook(null);
    try {
      const formData = new FormData();
      formData.append("book_type", bookMode);
      if (uploadMethod === "file" && file) {
        formData.append("file", file);
      } else if (uploadMethod === "text" && textContent) {
        formData.append("text_content", textContent);
      } else {
        toast.error("Please provide a file or text content.");
        setIsProcessing(false);
        return;
      }
      const book = (await apiClient.upload("/books/upload", formData)) as Book;
      setAiBook(book);
      setDetails({
        title: book.title || "",
        author_name: book.author_name || "",
        description: book.description || "",
      });
      setStep(4);
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "AI processing failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Step 4: Save/Update Book Details
  const handleDetailsChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setDetails({ ...details, [e.target.name]: e.target.value });
  };

  const handleSaveDetails = async () => {
    if (!aiBook) return;
    setSaving(true);
    try {
      await apiClient.put(`/books/${aiBook.id}`, details);
      toast.success("Book details updated!");
      navigate("/dashboard");
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "Failed to update book details.");
    } finally {
      setSaving(false);
    }
  };

  const steps = [
    {
      number: 1,
      title: "Upload Method",
      description: "Choose how to add your content",
    },
    {
      number: 2,
      title: "Content Mode",
      description: "Select learning or entertainment",
    },
    {
      number: 3,
      title: "AI Processing",
      description: "Let AI process your book",
    },
    {
      number: 4,
      title: "Book Details",
      description: "Edit and confirm book details",
    },
  ];

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Upload Your Book
          </h1>
          <p className="text-gray-600">
            Transform your content into an interactive AI-powered experience
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-12">
          <div className="flex items-center justify-between">
            {steps.map((stepItem, index) => (
              <div key={stepItem.number} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                    step >= stepItem.number
                      ? "bg-purple-600 border-purple-600 text-white"
                      : "border-gray-300 text-gray-500"
                  }`}
                >
                  {step > stepItem.number ? (
                    <CheckCircle className="h-6 w-6" />
                  ) : (
                    <span className="text-sm font-medium">
                      {stepItem.number}
                    </span>
                  )}
                </div>
                <div className="ml-3 min-w-0">
                  <p
                    className={`text-sm font-medium ${
                      step >= stepItem.number
                        ? "text-purple-600"
                        : "text-gray-500"
                    }`}
                  >
                    {stepItem.title}
                  </p>
                  <p className="text-xs text-gray-500">
                    {stepItem.description}
                  </p>
                </div>
                {index < steps.length - 1 && (
                  <ArrowRight className="h-5 w-5 text-gray-400 mx-4" />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
          {/* Step 1: Upload Method */}
          {step === 1 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                How would you like to add your content?
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <button
                  onClick={() => setUploadMethod("file")}
                  className={`p-8 rounded-2xl border-2 transition-all hover:scale-105 ${
                    uploadMethod === "file"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <Upload className="h-12 w-12 text-purple-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Upload File
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Upload a PDF, DOCX, TXT, or EPUB file of your book
                  </p>
                </button>

                <button
                  onClick={() => setUploadMethod("text")}
                  className={`p-8 rounded-2xl border-2 transition-all hover:scale-105 ${
                    uploadMethod === "text"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <FileText className="h-12 w-12 text-purple-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Paste Text
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Copy and paste your book content directly
                  </p>
                </button>
              </div>

              {uploadMethod === "file" && (
                <div className="mt-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select your book file
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-purple-400 transition-colors">
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.epub"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <label htmlFor="file-upload" className="cursor-pointer">
                      <Book className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600">
                        {file ? file.name : "Click to upload or drag and drop"}
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        PDF, DOCX, TXT, or EPUB up to 10MB
                      </p>
                    </label>
                  </div>
                </div>
              )}

              {uploadMethod === "text" && (
                <div className="mt-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Paste your book content
                  </label>
                  <textarea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    rows={12}
                    className="w-full border border-gray-300 rounded-xl p-4 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="Paste your book content here..."
                  />
                </div>
              )}

              <div className="flex justify-end mt-8">
                <button
                  onClick={handleNext}
                  className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-all"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Content Mode */}
          {step === 2 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Choose the experience mode
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <button
                  onClick={() => setBookMode("learning")}
                  className={`p-8 rounded-2xl border-2 transition-all hover:scale-105 ${
                    bookMode === "learning"
                      ? "border-green-500 bg-green-50"
                      : "border-gray-300 hover:border-green-300"
                  }`}
                >
                  <Brain className="h-12 w-12 text-green-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Learning Mode
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Convert into interactive tutorials, lessons, and quizzes
                  </p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>• AI-generated lessons</li>
                    <li>• Smart quizzes</li>
                    <li>• Progress tracking</li>
                    <li>• Verified badges</li>
                  </ul>
                </button>

                <button
                  onClick={() => setBookMode("entertainment")}
                  className={`p-8 rounded-2xl border-2 transition-all hover:scale-105 ${
                    bookMode === "entertainment"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <Sparkles className="h-12 w-12 text-purple-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Entertainment Mode
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Transform into interactive stories with branching narratives
                  </p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>• Choice-driven stories</li>
                    <li>• Voice characters</li>
                    <li>• AI-generated scenes</li>
                    <li>• Collectible NFTs</li>
                  </ul>
                </button>
              </div>
              <div className="flex justify-between mt-8">
                <button
                  onClick={handleBack}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-all"
                >
                  Back
                </button>
                <button
                  onClick={handleNext}
                  className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-all"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Step 3: AI Processing */}
          {step === 3 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                AI Processing
              </h2>
              <p className="text-gray-600 mb-4">
                Let AI analyze your book and auto-populate the details for you.
              </p>
              <div className="flex flex-col items-center justify-center min-h-[120px]">
                {isProcessing ? (
                  <div className="flex flex-col items-center">
                    <Settings className="h-10 w-10 animate-spin text-purple-600 mb-2" />
                    <span className="text-purple-600 font-medium">
                      Processing with AI...
                    </span>
                  </div>
                ) : (
                  <button
                    onClick={handleProcessAI}
                    className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-blue-700 transition-all text-lg"
                  >
                    Process with AI
                  </button>
                )}
              </div>
              <div className="flex justify-between mt-8">
                <button
                  onClick={handleBack}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-all"
                >
                  Back
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Book Details */}
          {step === 4 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Book Details
              </h2>
              <p className="text-gray-600 mb-4">
                Review and edit your book details before finalizing.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Title
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={details.title}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Author Name
                  </label>
                  <input
                    type="text"
                    name="author_name"
                    value={details.author_name}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    name="description"
                    value={details.description}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                    rows={4}
                  />
                </div>
              </div>
              <div className="flex justify-between mt-8">
                <button
                  onClick={handleBack}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-all"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveDetails}
                  disabled={saving}
                  className="px-8 py-4 bg-gradient-to-r from-green-600 to-blue-600 text-white rounded-xl font-semibold hover:from-green-700 hover:to-blue-700 transition-all text-lg disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save & Finish"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
