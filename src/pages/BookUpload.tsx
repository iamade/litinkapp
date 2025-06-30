import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { apiClient } from "../lib/api";
import { stripeService } from "../services/stripeService";
import {
  Upload,
  FileText,
  Brain,
  Sparkles,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Loader,
  CreditCard,
} from "lucide-react";
import { toast } from "react-hot-toast";

interface BookWithChapters {
  id: string;
  title: string;
  chapters: Array<{ title: string; content: string }>;
}

export default function BookUpload() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Check if we're resuming from a regenerate-chapters call
  const resumeBook = location.state?.resumeBook as BookWithChapters | undefined;

  const [currentStep, setCurrentStep] = useState(resumeBook ? 4 : 1);
  const [uploadMethod, setUploadMethod] = useState<"file" | "text">("file");
  const [contentMode, setContentMode] = useState<"learning" | "entertainment">(
    "learning"
  );
  const [file, setFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [bookId, setBookId] = useState<string | null>(resumeBook?.id || null);
  const [chapters, setChapters] = useState<
    Array<{ title: string; content: string }>
  >(resumeBook?.chapters || []);
  const [paymentRequired, setPaymentRequired] = useState(false);
  const [checkingPayment, setCheckingPayment] = useState(false);

  // Check payment requirement when component mounts
  useEffect(() => {
    if (!resumeBook) {
      checkPaymentRequirement();
    }
  }, []);

  const checkPaymentRequirement = async () => {
    try {
      setCheckingPayment(true);
      const response = await apiClient.get("/books/check-payment-required");
      setPaymentRequired(response.payment_required);
      
      if (response.payment_required) {
        toast.info("Payment required for additional book uploads");
      }
    } catch (error) {
      console.error("Error checking payment requirement:", error);
      toast.error("Failed to check payment requirement");
    } finally {
      setCheckingPayment(false);
    }
  };

  const handlePayment = async () => {
    try {
      // Create a temporary book record to get the book ID for payment
      const tempBookData = {
        title: file?.name || "Untitled Text",
        book_type: contentMode,
        status: "PENDING_PAYMENT"
      };

      const tempBook = await apiClient.post("/books/temp-create", tempBookData);
      
      // Create Stripe checkout session
      const checkoutSession = await stripeService.createBookUploadCheckoutSession(tempBook.id);
      
      // Redirect to Stripe checkout
      stripeService.redirectToCheckout(checkoutSession.checkout_url);
      
    } catch (error) {
      console.error("Error initiating payment:", error);
      toast.error("Failed to initiate payment");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (selectedFile.size > maxSize) {
        toast.error("File size must be less than 10MB");
        return;
      }

      const allowedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
      ];
      if (!allowedTypes.includes(selectedFile.type)) {
        toast.error("Please upload a PDF, DOCX, or TXT file");
        return;
      }

      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file && !textContent.trim()) {
      toast.error("Please select a file or enter text content");
      return;
    }

    // If payment is required, handle payment first
    if (paymentRequired) {
      await handlePayment();
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append("book_type", contentMode);

      if (uploadMethod === "file" && file) {
        formData.append("file", file);
      } else if (uploadMethod === "text" && textContent.trim()) {
        formData.append("text_content", textContent.trim());
      }

      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 10, 90));
      }, 500);

      const response = await apiClient.upload<any>("/books/upload", formData);

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.payment_required) {
        // This shouldn't happen with the new flow, but handle it just in case
        setPaymentRequired(true);
        toast.error("Payment required for additional uploads");
        return;
      }

      setBookId(response.id);
      toast.success("Book uploaded successfully!");
      setCurrentStep(3);

      // Poll for processing completion
      pollBookStatus(response.id);
    } catch (error: any) {
      console.error("Upload error:", error);
      if (error.message?.includes("402")) {
        setPaymentRequired(true);
        toast.error("Payment required. Please complete payment to continue.");
      } else {
        toast.error(error.message || "Upload failed. Please try again.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const pollBookStatus = async (id: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await apiClient.get(`/books/${id}/status`);

        if (status.status === "READY") {
          setChapters(status.chapters || []);
          setCurrentStep(4);
          toast.success("Book processing completed!");
          return;
        } else if (status.status === "FAILED") {
          toast.error("Book processing failed. Please try again.");
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          toast.error("Processing is taking longer than expected.");
        }
      } catch (error) {
        console.error("Error polling book status:", error);
        toast.error("Error checking book status");
      }
    };

    poll();
  };

  const handleChapterEdit = (index: number, field: string, value: string) => {
    const updatedChapters = [...chapters];
    updatedChapters[index] = { ...updatedChapters[index], [field]: value };
    setChapters(updatedChapters);
  };

  const handleSaveChapters = async () => {
    if (!bookId) return;

    try {
      await apiClient.post(`/books/${bookId}/save-chapters`, chapters);
      toast.success("Chapters saved successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error saving chapters:", error);
      toast.error("Failed to save chapters");
    }
  };

  const nextStep = () => {
    if (currentStep === 1) {
      // Check payment requirement before proceeding
      if (paymentRequired) {
        handlePayment();
        return;
      }
    }
    setCurrentStep(currentStep + 1);
  };

  const prevStep = () => setCurrentStep(currentStep - 1);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">
            Please sign in to upload books
          </p>
        </div>
      </div>
    );
  }

  if (checkingPayment) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader className="h-12 w-12 text-purple-600 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">Checking payment requirements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Upload Your Book
          </h1>
          <p className="text-gray-600">
            Transform your book into an AI-powered interactive experience
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-12">
          <div className="flex items-center justify-center space-x-8">
            {[
              { step: 1, label: "Upload Method", icon: Upload },
              { step: 2, label: "Content Mode", icon: Brain },
              { step: 3, label: "Processing", icon: Loader },
              { step: 4, label: "Review", icon: CheckCircle },
            ].map(({ step, label, icon: Icon }) => (
              <div key={step} className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center border-2 ${
                    currentStep >= step
                      ? "bg-purple-600 border-purple-600 text-white"
                      : "border-gray-300 text-gray-400"
                  }`}
                >
                  <Icon className="h-6 w-6" />
                </div>
                <span
                  className={`mt-2 text-sm font-medium ${
                    currentStep >= step ? "text-purple-600" : "text-gray-400"
                  }`}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
          {/* Step 1: Upload Method */}
          {currentStep === 1 && (
            <div className="space-y-8">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Choose Upload Method
                </h2>
                <p className="text-gray-600">
                  How would you like to provide your book content?
                </p>
              </div>

              {/* Payment Warning */}
              {paymentRequired && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center">
                    <CreditCard className="h-5 w-5 text-yellow-600 mr-2" />
                    <div>
                      <h3 className="text-sm font-medium text-yellow-800">
                        Payment Required
                      </h3>
                      <p className="text-sm text-yellow-700 mt-1">
                        This is your second or additional book upload. A payment of $5 is required to continue.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <button
                  onClick={() => setUploadMethod("file")}
                  className={`p-6 rounded-xl border-2 transition-all ${
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
                    Upload a PDF, DOCX, or TXT file
                  </p>
                </button>

                <button
                  onClick={() => setUploadMethod("text")}
                  className={`p-6 rounded-xl border-2 transition-all ${
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
                    Copy and paste your book content
                  </p>
                </button>
              </div>

              {uploadMethod === "file" && (
                <div className="mt-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select File
                  </label>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                  />
                  {file && (
                    <p className="mt-2 text-sm text-green-600">
                      Selected: {file.name}
                    </p>
                  )}
                </div>
              )}

              {uploadMethod === "text" && (
                <div className="mt-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Book Content
                  </label>
                  <textarea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Paste your book content here..."
                    className="w-full h-64 p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={nextStep}
                  disabled={
                    (uploadMethod === "file" && !file) ||
                    (uploadMethod === "text" && !textContent.trim())
                  }
                  className="flex items-center space-x-2 bg-purple-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <span>{paymentRequired ? "Proceed to Payment" : "Next"}</span>
                  <ArrowRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Content Mode */}
          {currentStep === 2 && (
            <div className="space-y-8">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Choose Content Mode
                </h2>
                <p className="text-gray-600">
                  How should your book be transformed?
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <button
                  onClick={() => setContentMode("learning")}
                  className={`p-6 rounded-xl border-2 transition-all ${
                    contentMode === "learning"
                      ? "border-green-500 bg-green-50"
                      : "border-gray-300 hover:border-green-300"
                  }`}
                >
                  <Brain className="h-12 w-12 text-green-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Learning Mode
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Interactive tutorials, quizzes, and educational content
                  </p>
                </button>

                <button
                  onClick={() => setContentMode("entertainment")}
                  className={`p-6 rounded-xl border-2 transition-all ${
                    contentMode === "entertainment"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <Sparkles className="h-12 w-12 text-purple-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Entertainment Mode
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Interactive stories, character voices, and immersive scenes
                  </p>
                </button>
              </div>

              <div className="flex justify-between">
                <button
                  onClick={prevStep}
                  className="flex items-center space-x-2 border border-gray-300 text-gray-700 px-6 py-3 rounded-xl font-medium hover:bg-gray-50 transition-all"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span>Back</span>
                </button>
                <button
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="flex items-center space-x-2 bg-purple-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isUploading ? (
                    <Loader className="h-5 w-5 animate-spin" />
                  ) : (
                    <Upload className="h-5 w-5" />
                  )}
                  <span>{isUploading ? "Uploading..." : "Upload Book"}</span>
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Processing */}
          {currentStep === 3 && (
            <div className="text-center space-y-6">
              <Loader className="h-16 w-16 text-purple-600 mx-auto animate-spin" />
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Processing Your Book
                </h2>
                <p className="text-gray-600">
                  Our AI is analyzing your content and generating interactive
                  elements...
                </p>
              </div>

              {uploadProgress > 0 && (
                <div className="max-w-md mx-auto">
                  <div className="bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">
                    {uploadProgress}% complete
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Review Chapters */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Review Generated Chapters
                </h2>
                <p className="text-gray-600">
                  Review and edit the AI-generated chapters before finalizing
                </p>
              </div>

              <div className="space-y-4 max-h-96 overflow-y-auto">
                {chapters.map((chapter, index) => (
                  <div
                    key={index}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Chapter {index + 1} Title
                      </label>
                      <input
                        type="text"
                        value={chapter.title}
                        onChange={(e) =>
                          handleChapterEdit(index, "title", e.target.value)
                        }
                        className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Content Preview
                      </label>
                      <textarea
                        value={chapter.content}
                        onChange={(e) =>
                          handleChapterEdit(index, "content", e.target.value)
                        }
                        className="w-full h-32 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex justify-between">
                <button
                  onClick={() => navigate("/dashboard")}
                  className="flex items-center space-x-2 border border-gray-300 text-gray-700 px-6 py-3 rounded-xl font-medium hover:bg-gray-50 transition-all"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span>Cancel</span>
                </button>
                <button
                  onClick={handleSaveChapters}
                  className="flex items-center space-x-2 bg-green-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-green-700 transition-all"
                >
                  <CheckCircle className="h-5 w-5" />
                  <span>Save & Finish</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}