import React, { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
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

// Add interface for chapter structure
interface Chapter {
  title: string;
  content: string;
}

// Add new type for editable chapters
interface EditableChapter {
  title: string;
  content: string;
}

// Define Book type based on backend BookSchema
interface Book {
  id: string;
  title: string;
  author_name: string | null;
  description: string | null;
  cover_image_url: string | null;
  book_type: string;
  difficulty: string;
  tags: string[] | null;
  language: string | null;
  status: string;
  total_chapters: number;
  estimated_duration: number | string | null;
  chapters: Chapter[] | null;
  error_message?: string;
  progress_message?: string;
  processing_time_seconds?: number;
}

export default function BookUpload() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(1);
  const [uploadMethod, setUploadMethod] = useState<"file" | "text">("file");
  const [bookMode, setBookMode] = useState<"learning" | "entertainment">(
    "learning"
  );
  const [file, setFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [aiBook, setAiBook] = useState<Book | null>(null);
  const [details, setDetails] = useState<{
    title: string;
    author_name: string;
    description: string;
    cover_image_url: string;
    book_type: string;
    difficulty: string;
    tags: string[];
    language: string;
    estimated_duration: string;
  }>({
    title: "",
    author_name: "",
    description: "",
    cover_image_url: "",
    book_type: "learning",
    difficulty: "medium",
    tags: [],
    language: "en",
    estimated_duration: "",
  });
  const [saving, setSaving] = useState(false);
  const [authorNameError, setAuthorNameError] = useState("");
  const [coverSource, setCoverSource] = useState<"upload" | "extract">(
    "upload"
  );
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string>("");
  const [coverPage, setCoverPage] = useState<string>("");
  const [coverError, setCoverError] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [formError, setFormError] = useState("");
  const coverInputRef = useRef<HTMLInputElement>(null);
  // New state for editable chapters
  const [editableChapters, setEditableChapters] = useState<EditableChapter[]>(
    []
  );
  const [savingChapters, setSavingChapters] = useState(false);
  const [chapterError, setChapterError] = useState("");
  const [processingStatus, setProcessingStatus] = useState("");
  const [processingFailed, setProcessingFailed] = useState(false);

  useEffect(() => {
    // Check if we are resuming a book from the dashboard
    if (location.state?.resumeBook) {
      const bookToResume = location.state.resumeBook as Book;

      // Set the AI book object
      setAiBook(bookToResume);

      // Set the editable chapters
      setEditableChapters(
        (bookToResume.chapters as EditableChapter[])?.map((ch) => ({
          title: ch.title,
          content: ch.content,
        })) || []
      );

      // Set book details
      setDetails({
        title: bookToResume.title || "",
        author_name: bookToResume.author_name || "",
        description: bookToResume.description || "",
        cover_image_url: bookToResume.cover_image_url || "",
        book_type: bookToResume.book_type || "learning",
        difficulty: bookToResume.difficulty || "medium",
        tags: bookToResume.tags || [],
        language: bookToResume.language || "en",
        estimated_duration: bookToResume.estimated_duration
          ? String(bookToResume.estimated_duration)
          : "",
      });

      // Jump to the chapter review step
      setStep(4);
    }
  }, [location.state]);

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
    setProcessingFailed(false);
    setAiBook(null);
    setEditableChapters([]);
    setProcessingStatus("Initializing...");
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
        setProcessingStatus("");
        return;
      }
      const book = (await apiClient.upload("/books/upload", formData)) as Book;
      setAiBook(book);
      setProcessingStatus("Uploading book...");

      // Poll for status changes
      const pollInterval = setInterval(async () => {
        try {
          const response = await apiClient.get<Book>(
            `/books/${book.id}/status`
          );
          const updatedBook = response as Book;
          setAiBook(updatedBook);

          // Update processing status based on book status
          if (updatedBook.progress_message) {
            setProcessingStatus(updatedBook.progress_message);
          } else {
            switch (updatedBook.status) {
              case "QUEUED":
                setProcessingStatus("Queued for processing...");
                break;
              case "PROCESSING":
                setProcessingStatus("Extracting content...");
                break;
              case "GENERATING":
                setProcessingStatus("Generating chapters with AI...");
                break;
              case "READY":
                setProcessingStatus("Book is ready!");
                break;
              case "FAILED":
                setProcessingStatus("Processing failed");
                break;
              default:
                setProcessingStatus("Processing...");
            }
          }

          // Stop polling if the book processing has failed
          if (updatedBook.status === "FAILED") {
            clearInterval(pollInterval);
            setProcessingFailed(true);
            toast.error(
              updatedBook.error_message ||
                "Book processing failed. Please try again."
            );
            setIsProcessing(false);
            setProcessingStatus("");
          } else if (updatedBook.status === "READY") {
            // Proceed to the next step only when the book is fully ready
            clearInterval(pollInterval);

            // Set editable chapters for review
            if (updatedBook.chapters) {
              setEditableChapters(
                updatedBook.chapters.map((ch: Chapter) => ({
                  title: ch.title || "",
                  content: ch.content || "",
                }))
              );
            }
            setDetails({
              title: updatedBook.title || "",
              author_name: updatedBook.author_name || "",
              description: updatedBook.description || "",
              cover_image_url: updatedBook.cover_image_url || "",
              book_type: updatedBook.book_type || "learning",
              difficulty: updatedBook.difficulty || "medium",
              tags: updatedBook.tags || [],
              language: updatedBook.language || "en",
              estimated_duration: updatedBook.estimated_duration
                ? String(updatedBook.estimated_duration)
                : "",
            });
            setStep(4); // Go to chapter review step
            setIsProcessing(false);
            setProcessingStatus("");
          }
        } catch (error) {
          console.error("Error polling book status:", error);
          clearInterval(pollInterval);
          setIsProcessing(false);
          setProcessingStatus("");
          toast.error("Could not get book status. Please check the dashboard.");
        }
      }, 7000); // Poll every 7 seconds

      // Cleanup polling on component unmount
      return () => clearInterval(pollInterval);
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "AI processing failed.");
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  // Retry processing for failed books
  const handleRetryProcessing = async () => {
    if (!aiBook) return;

    setIsProcessing(true);
    setProcessingFailed(false);
    setProcessingStatus("Retrying processing...");

    try {
      // Call the retry endpoint
      const retryResponse = await apiClient.post<Book>(
        `/books/${aiBook.id}/retry`,
        {}
      );
      const updatedBook = retryResponse as Book;
      setAiBook(updatedBook);

      // Start polling again
      const pollInterval = setInterval(async () => {
        try {
          const response = await apiClient.get<Book>(
            `/books/${aiBook.id}/status`
          );
          const bookStatus = response as Book;
          setAiBook(bookStatus);

          if (bookStatus.progress_message) {
            setProcessingStatus(bookStatus.progress_message);
          }

          if (bookStatus.status === "FAILED") {
            clearInterval(pollInterval);
            setProcessingFailed(true);
            toast.error(
              bookStatus.error_message ||
                "Processing failed again. Please try again."
            );
            setIsProcessing(false);
            setProcessingStatus("");
          } else if (bookStatus.status === "READY") {
            clearInterval(pollInterval);

            if (bookStatus.chapters) {
              setEditableChapters(
                bookStatus.chapters.map((ch: Chapter) => ({
                  title: ch.title || "",
                  content: ch.content || "",
                }))
              );
            }

            setDetails({
              title: bookStatus.title || "",
              author_name: bookStatus.author_name || "",
              description: bookStatus.description || "",
              cover_image_url: bookStatus.cover_image_url || "",
              book_type: bookStatus.book_type || "learning",
              difficulty: bookStatus.difficulty || "medium",
              tags: bookStatus.tags || [],
              language: bookStatus.language || "en",
              estimated_duration: bookStatus.estimated_duration
                ? String(bookStatus.estimated_duration)
                : "",
            });

            setStep(4);
            setIsProcessing(false);
            setProcessingStatus("");
            toast.success("Book processing completed successfully!");
          }
        } catch (error) {
          console.error("Error polling book status:", error);
          clearInterval(pollInterval);
          setIsProcessing(false);
          setProcessingStatus("");
          toast.error("Could not get book status. Please check the dashboard.");
        }
      }, 7000);

      return () => clearInterval(pollInterval);
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "Failed to retry processing.");
      setIsProcessing(false);
      setProcessingStatus("");
      setProcessingFailed(true);
    }
  };

  // Step 4: Save Chapters (after user review)
  const handleSaveChapters = async () => {
    if (!aiBook) return;
    setSavingChapters(true);
    setChapterError("");
    // Validate chapters
    if (
      !editableChapters.length ||
      editableChapters.some((ch) => !ch.title.trim())
    ) {
      setChapterError("Each chapter must have a title.");
      setSavingChapters(false);
      return;
    }
    try {
      await apiClient.post(
        `/books/${aiBook.id}/save-chapters`,
        editableChapters
      );
      setStep(5); // Proceed to Book Details
      toast.success("Chapters saved! Now complete book details.");
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "Failed to save chapters.");
      setChapterError(error.message || "Failed to save chapters.");
    } finally {
      setSavingChapters(false);
    }
  };

  // Step 4: Save/Update Book Details
  const handleDetailsChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setDetails((prev) => ({
      ...prev,
      [name]:
        name === "tags"
          ? value
              .split(",")
              .map((t: string) => t.trim())
              .filter(Boolean)
          : name === "estimated_duration"
          ? value.replace(/[^0-9]/g, "")
          : value,
    }));
  };

  // Cover image upload handler
  const handleCoverFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCoverFile(file);
      setCoverPreview(URL.createObjectURL(file));
      setDetails((prev) => ({ ...prev, cover_image_url: "" }));
    }
  };

  // Tag input handlers
  const handleTagInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTagInput(e.target.value);
  };
  const handleTagInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === "Enter" || e.key === ",") && tagInput.trim()) {
      e.preventDefault();
      if (!details.tags.includes(tagInput.trim())) {
        setDetails((prev) => ({
          ...prev,
          tags: [...prev.tags, tagInput.trim()],
        }));
      }
      setTagInput("");
    }
  };
  const handleRemoveTag = (tag: string) => {
    setDetails((prev) => ({
      ...prev,
      tags: prev.tags.filter((t) => t !== tag),
    }));
  };

  // Cover image extraction handler
  const handleExtractCover = async () => {
    setCoverError("");
    if (!coverPage || isNaN(Number(coverPage)) || Number(coverPage) < 1) {
      setCoverError("Enter a valid page number");
      return;
    }
    if (!aiBook) return;
    try {
      // Call backend endpoint to extract cover from page (implement this endpoint if not present)
      const res = await apiClient.post<{ cover_image_url: string }>(
        `/books/${aiBook.id}/extract-cover`,
        { page: Number(coverPage) }
      );
      setDetails((prev) => ({ ...prev, cover_image_url: res.cover_image_url }));
      setCoverPreview(res.cover_image_url);
      setCoverError("");
    } catch {
      setCoverError("Failed to extract cover from page.");
    }
  };

  // Cover image upload to backend
  const uploadCoverImage = async () => {
    if (!coverFile || !aiBook) return null;
    const formData = new FormData();
    formData.append("cover_image", coverFile);
    try {
      const res = await apiClient.upload<{ cover_image_url: string }>(
        `/books/${aiBook.id}/upload-cover`,
        formData
      );
      return res.cover_image_url;
    } catch {
      setCoverError("Failed to upload cover image.");
      return null;
    }
  };

  const handleSaveDetails = async () => {
    if (!aiBook) return;
    setFormError("");
    if (!details.title.trim()) {
      setFormError("Title is required.");
      return;
    }
    if (!details.author_name || !details.author_name.trim()) {
      setAuthorNameError("Author name is required.");
      return;
    } else {
      setAuthorNameError("");
    }
    if (!details.book_type) {
      setFormError("Book type is required.");
      return;
    }
    if (!details.difficulty) {
      setFormError("Difficulty is required.");
      return;
    }
    // Handle cover image upload if needed
    let coverUrl = details.cover_image_url;
    if (coverSource === "upload" && coverFile) {
      const uploaded = await uploadCoverImage();
      if (uploaded) coverUrl = uploaded;
    }
    // If extract, cover_image_url is already set by extract handler
    setSaving(true);
    try {
      const payload = {
        ...details,
        cover_image_url: coverUrl,
        estimated_duration: details.estimated_duration
          ? Number(details.estimated_duration)
          : null,
      };
      await apiClient.put(`/books/${aiBook.id}`, payload);
      toast.success("Book details updated!");
      navigate("/dashboard");
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "Failed to update book details.");
    } finally {
      setSaving(false);
    }
  };

  // Chapter editing handlers
  const handleChapterChange = (
    idx: number,
    field: keyof EditableChapter,
    value: string
  ) => {
    setEditableChapters((prev) =>
      prev.map((ch, i) => (i === idx ? { ...ch, [field]: value } : ch))
    );
  };
  const handleAddChapter = () => {
    setEditableChapters((prev) => [...prev, { title: "", content: "" }]);
  };
  const handleRemoveChapter = (idx: number) => {
    setEditableChapters((prev) => prev.filter((_, i) => i !== idx));
  };
  const handleMoveChapter = (idx: number, direction: "up" | "down") => {
    setEditableChapters((prev) => {
      const arr = [...prev];
      if (direction === "up" && idx > 0) {
        [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
      } else if (direction === "down" && idx < arr.length - 1) {
        [arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]];
      }
      return arr;
    });
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
      title: "Chapter Review",
      description: "Review and edit extracted chapters",
    },
    {
      number: 5,
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
                    {processingStatus && (
                      <span className="text-gray-600 text-sm mt-2 text-center max-w-md">
                        {processingStatus}
                      </span>
                    )}
                  </div>
                ) : processingFailed ? (
                  <div className="flex flex-col items-center">
                    <div className="text-red-500 text-sm mb-4 text-center max-w-md">
                      Processing failed. Please check the error message above
                      and try again.
                    </div>
                    <button
                      onClick={handleRetryProcessing}
                      className="px-8 py-4 bg-gradient-to-r from-red-600 to-orange-600 text-white rounded-xl font-semibold hover:from-red-700 hover:to-orange-700 transition-all text-lg"
                    >
                      Retry Processing
                    </button>
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

          {/* Step 4: Chapter Review */}
          {step === 4 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Review & Edit Chapters
              </h2>
              <p className="text-gray-600 mb-4">
                Review, edit, reorder, or add chapters. Only confirmed chapters
                will be saved.
              </p>
              {chapterError && (
                <div className="text-red-500 text-sm mb-2">{chapterError}</div>
              )}
              <div className="space-y-4">
                {editableChapters.map((ch, idx) => (
                  <div
                    key={idx}
                    className="border border-gray-200 rounded-xl p-4 bg-gray-50 relative"
                  >
                    <div className="flex items-center mb-2">
                      <span className="font-semibold text-gray-700 mr-2">
                        Chapter {idx + 1}
                      </span>
                      <button
                        type="button"
                        className="ml-2 text-xs text-blue-500 hover:underline"
                        onClick={() => handleMoveChapter(idx, "up")}
                        disabled={idx === 0}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="ml-1 text-xs text-blue-500 hover:underline"
                        onClick={() => handleMoveChapter(idx, "down")}
                        disabled={idx === editableChapters.length - 1}
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        className="ml-2 text-xs text-red-500 hover:underline"
                        onClick={() => handleRemoveChapter(idx)}
                      >
                        Remove
                      </button>
                    </div>
                    <input
                      type="text"
                      className="w-full border border-gray-300 rounded-xl px-3 py-2 mb-2"
                      placeholder="Chapter Title"
                      value={ch.title}
                      onChange={(e) =>
                        handleChapterChange(idx, "title", e.target.value)
                      }
                    />
                    <textarea
                      className="w-full border border-gray-300 rounded-xl px-3 py-2"
                      placeholder="Chapter Content"
                      rows={4}
                      value={ch.content}
                      onChange={(e) =>
                        handleChapterChange(idx, "content", e.target.value)
                      }
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className="mt-2 px-4 py-2 bg-green-100 text-green-700 rounded hover:bg-green-200"
                  onClick={handleAddChapter}
                >
                  + Add Chapter
                </button>
              </div>
              <div className="flex justify-between mt-8">
                <button
                  onClick={handleBack}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-all"
                  disabled={savingChapters}
                >
                  Back
                </button>
                <button
                  onClick={handleSaveChapters}
                  disabled={savingChapters}
                  className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-blue-700 transition-all text-lg disabled:opacity-50"
                >
                  {savingChapters ? "Saving..." : "Confirm Chapters"}
                </button>
              </div>
              {step === 4 &&
                aiBook &&
                aiBook.processing_time_seconds !== undefined && (
                  <div className="mt-4 text-green-700 text-center text-sm font-medium">
                    Processing time: {aiBook.processing_time_seconds} seconds
                  </div>
                )}
            </div>
          )}

          {/* Step 5: Book Details */}
          {step === 5 && (
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
                    value={details.title ?? ""}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Author Name{" "}
                    {(!details.author_name || authorNameError) && (
                      <span className="text-red-500">*</span>
                    )}
                  </label>
                  <input
                    type="text"
                    name="author_name"
                    value={details.author_name ?? ""}
                    onChange={handleDetailsChange}
                    className={`w-full border rounded-xl px-3 py-2 ${
                      authorNameError ? "border-red-500" : "border-gray-300"
                    }`}
                  />
                  {authorNameError && (
                    <div className="text-xs text-red-500 mt-1">
                      {authorNameError}
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    name="description"
                    value={details.description ?? ""}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                    rows={4}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cover Image
                  </label>
                  <div className="flex items-center space-x-4 mb-2">
                    <label className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={coverSource === "upload"}
                        onChange={() => setCoverSource("upload")}
                      />
                      <span>Upload New Cover</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={coverSource === "extract"}
                        onChange={() => setCoverSource("extract")}
                      />
                      <span>Extract from PDF</span>
                    </label>
                  </div>

                  {coverSource === "upload" && (
                    <div className="p-4 border-2 border-dashed rounded-xl">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleCoverFileChange}
                        ref={coverInputRef}
                        className="hidden"
                      />
                      <div
                        className="cursor-pointer"
                        onClick={() => coverInputRef.current?.click()}
                      >
                        {coverPreview ? (
                          <img
                            src={coverPreview}
                            alt="Cover preview"
                            className="w-full h-auto rounded-lg"
                          />
                        ) : (
                          <div className="text-center text-gray-500">
                            <p>Click to upload a cover image</p>
                            <p className="text-sm">(e.g., PNG, JPG, WEBP)</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  {coverSource === "extract" && (
                    <div>
                      <input
                        type="text"
                        placeholder="Enter page number for cover"
                        value={coverPage}
                        onChange={(e) => setCoverPage(e.target.value)}
                        className="w-full border border-gray-300 rounded-xl px-3 py-2"
                      />
                      <button
                        onClick={handleExtractCover}
                        className="mt-2 bg-indigo-500 text-white px-4 py-2 rounded-xl"
                      >
                        Extract Cover
                      </button>
                    </div>
                  )}
                  {coverError && (
                    <p className="text-red-500 text-sm mt-1">{coverError}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Book Type
                  </label>
                  <select
                    name="book_type"
                    value={details.book_type}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  >
                    <option value="learning">Learning</option>
                    <option value="entertainment">Entertainment</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Difficulty
                  </label>
                  <select
                    name="difficulty"
                    value={details.difficulty}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tags
                  </label>
                  <div className="flex flex-wrap gap-2 items-center border border-gray-300 rounded-xl px-3 py-2">
                    {details.tags?.map((tag) => (
                      <span
                        key={tag}
                        className="bg-gray-200 text-gray-800 px-2 py-1 rounded-full text-sm flex items-center"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(tag)}
                          className="ml-2 text-red-500 hover:text-red-700"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                    <input
                      type="text"
                      value={tagInput}
                      onChange={handleTagInputChange}
                      onKeyDown={handleTagInputKeyDown}
                      placeholder="Add a tag and press Enter"
                      className="flex-grow outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Language
                  </label>
                  <input
                    type="text"
                    name="language"
                    value={details.language ?? ""}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estimated Duration
                  </label>
                  <input
                    type="text"
                    name="estimated_duration"
                    value={details.estimated_duration ?? ""}
                    onChange={handleDetailsChange}
                    className="w-full border border-gray-300 rounded-xl px-3 py-2"
                  />
                </div>
                {formError && (
                  <div className="text-red-500 text-sm">{formError}</div>
                )}
                <div className="flex justify-between mt-6">
                  <button
                    onClick={() => setStep(4)}
                    className="bg-gray-200 text-gray-800 px-6 py-2 rounded-xl"
                  >
                    Back to Chapters
                  </button>
                  <button
                    onClick={handleSaveDetails}
                    disabled={saving}
                    className="bg-green-500 text-white px-6 py-2 rounded-xl disabled:bg-green-300"
                  >
                    {saving ? "Saving..." : "Save and Continue"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 6 && (
            <div className="text-center">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">
                Book Created Successfully!
              </h2>
              <p className="text-gray-600 mb-6">
                Your book is now ready. You can view it in your library or start
                a new one.
              </p>
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => navigate("/dashboard")}
                  className="bg-indigo-500 text-white px-6 py-2 rounded-xl"
                >
                  Go to Dashboard
                </button>
                <button
                  onClick={() => {
                    setStep(1);
                    setFile(null);
                    setTextContent("");
                    setAiBook(null);
                  }}
                  className="bg-gray-200 text-gray-800 px-6 py-2 rounded-xl"
                >
                  Create Another Book
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
