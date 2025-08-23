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
  CreditCard,
  AlertCircle,
} from "lucide-react";
import { apiClient } from "../lib/api";
import { stripeService } from "../services/stripeService";
// import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

// Add interface for chapter structure
// interface Chapter {
//   title: string;
//   content: string;
// }

interface BookSection {
  id: string;
  book_id: string;
  section_number: string; // "1", "I", "III", etc.
  section_type: string; // "part", "tablet", "book", "section"
  title: string;
  description?: string;
  order_index: number;
  chapters: Chapter[];
}

interface Chapter {
  id: string;
  book_id: string;
  section_id?: string;
  chapter_number: number;
  title: string;
  content: string;
  summary?: string;
  order_index: number;
}

interface BookStructure {
  id: string;
  title: string;
  has_sections: boolean;
  structure_type: "flat" | "hierarchical";
  sections: BookSection[];
  chapters: Chapter[]; // For flat structure books
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
  payment_required?: boolean;
  message?: string;
  has_sections?: boolean;
  structure_type?: "flat" | "hierarchical";
  structure_data?: BookStructure; 
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
  // const [chapterError, setChapterError] = useState("");
  const [processingStatus, setProcessingStatus] = useState("");
  const [processingFailed, setProcessingFailed] = useState(false);

  // Payment-related state
  const [paymentRequired, setPaymentRequired] = useState(false);
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [userBookCount, setUserBookCount] = useState(0);
  // Add this state variable near the other useState declarations
  const [bookStructure, setBookStructure] = useState<BookStructure | null>(
    null
  );
  const [isUploading, setIsUploading] = useState(false);

  const getSectionIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "tablet":
        return "📜";
      case "part":
        return "📖";
      case "book":
        return "📚";
      case "section":
        return "📄";
      case "chapter":
        return "📝";
      case "act":
        return "🎭";
      case "scene":
        return "🎬";
      case "unit":
        return "🎯";
      case "lesson":
        return "🎓";
      default:
        return "📄";
    }
  };

  const getSectionLabel = (type: string) => {
    switch (type.toLowerCase()) {
      case "tablet":
        return "Tablet";
      case "part":
        return "Part";
      case "book":
        return "Book";
      case "section":
        return "Section";
      case "chapter":
        return "Chapter";
      case "act":
        return "Act";
      case "scene":
        return "Scene";
      case "unit":
        return "Unit";
      case "lesson":
        return "Lesson";
      default:
        return "Section";
    }
  };

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
        book_type: bookToResume.book_type || bookMode,
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

    // Check payment success/cancel from URL params
    const urlParams = new URLSearchParams(location.search);
    const paymentStatus = urlParams.get("payment");
    const bookId = urlParams.get("book_id");

    if (paymentStatus === "success" && bookId) {
      toast.success("Payment successful! Please continue your upload.");
      setStep(2);
    } else if (paymentStatus === "cancelled" && bookId) {
      toast.error("Payment was cancelled. You can try again.");
    }

    // Load user book count
    loadUserBookCount();
  }, [location.state, location.search, navigate]);

  const loadUserBookCount = async () => {
    try {
      const bookCountData = await stripeService.getUserBookCount();
      setUserBookCount(bookCountData.book_count);
    } catch (error) {
      console.error("Error loading user book count:", error);
    }
  };

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

  // Step 3: AI Processing with Payment Logic
  const handleProcessAI = async () => {
    console.log("🚀 handleProcessAI called with bookMode:", bookMode);
    console.log("🚀 Upload method:", uploadMethod);
    console.log("🚀 File:", file?.name);
    if (isUploading) return;
    setIsUploading(true);
    setIsProcessing(true);
    setProcessingFailed(false);
    setAiBook(null);
    setEditableChapters([]);
    setProcessingStatus("Initializing...");
    setPaymentRequired(false);

    try {
      const formData = new FormData();
      formData.append("book_type", bookMode);
      console.log("📤 Sending upload with book_type:", bookMode);
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

      try {
        const book = (await apiClient.upload(
          "/books/upload",
          formData
        )) as Book;
        setAiBook(book);

        // Check if payment is required
        if (book.payment_required) {
          setPaymentRequired(true);
          setIsProcessing(false);
          setProcessingStatus("");
          toast.success("Payment required for additional book uploads");
          return;
        }

        setProcessingStatus("Uploading book...");

        // Poll for status changes (existing logic for free books)
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

              // Set book structure data if available
              if (updatedBook.structure_data) {
                setBookStructure(updatedBook.structure_data);
              } else if (updatedBook.chapters) {
                // Fallback: create basic structure from chapters
                setBookStructure({
                  id: updatedBook.id,
                  title: updatedBook.title || "",
                  has_sections: updatedBook.has_sections || false,
                  structure_type: updatedBook.structure_type || "flat",
                  sections: [],
                  chapters: updatedBook.chapters || [],
                });
              }
              
              setDetails({
                title: updatedBook.title || "",
                author_name: updatedBook.author_name || "",
                description: updatedBook.description || "",
                cover_image_url: updatedBook.cover_image_url || "",
                book_type: updatedBook.book_type || bookMode,
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
            toast.error(
              "Could not get book status. Please check the dashboard."
            );
          }
        }, 7000); // Poll every 7 seconds

        // Cleanup polling on component unmount
        return () => clearInterval(pollInterval);
      } catch (uploadError: any) {
        console.log("Upload error:", uploadError);
        setIsProcessing(false);
        setProcessingStatus("");

        //Show the actual error message
        const errorMessage =
          uploadError?.response?.data?.details ||
          uploadError?.message ||
          "Upload failed";
        toast.error(`Upload failed: ${errorMessage}`);
        return;
      }
    } catch (e: unknown) {
      const error = e as Error;
      toast.error(error.message || "AI processing failed.");
      setIsProcessing(false);
      setProcessingStatus("");
    } finally {
      setIsUploading(false);
    }
  };

  // Handle payment for book upload
  const handlePayment = async () => {
    if (!aiBook) return;

    setPaymentProcessing(true);
    try {
      const checkoutSession =
        await stripeService.createBookUploadCheckoutSession(aiBook.id);

      console.log("Stripe checkout session response:", checkoutSession);
      if (
        checkoutSession &&
        typeof checkoutSession === "object" &&
        "checkout_url" in checkoutSession
      ) {
        const url = (checkoutSession as { checkout_url: string }).checkout_url;
        if (url) {
          stripeService.redirectToCheckout(url);
          return;
        } else {
          toast.error("Stripe did not return a checkout URL.");
          console.error("No checkout_url in Stripe response:", checkoutSession);
        }
      } else {
        toast.error("Failed to create Stripe checkout session.");
        console.error("Unexpected Stripe session response:", checkoutSession);
      }
    } catch (e) {
      const error = e as Error;
      toast.error(error.message || "Error creating Stripe checkout session.");
      console.error("Stripe checkout session error:", error);
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
              book_type: bookStatus.book_type || bookMode,
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
  // const handleSaveChapters = async () => {
  //   if (!aiBook) return;
  //   setSavingChapters(true);
  //   setChapterError("");
  //   // Validate chapters
  //   if (
  //     !editableChapters.length ||
  //     editableChapters.some((ch) => !ch.title.trim())
  //   ) {
  //     setChapterError("Each chapter must have a title.");
  //     setSavingChapters(false);
  //     return;
  //   }
  //   try {
  //     await apiClient.post(
  //       `/books/${aiBook.id}/save-chapters`,
  //       editableChapters
  //     );
  //     setStep(5); // Proceed to Book Details
  //     toast.success("Chapters saved! Now complete book details.");
  //   } catch (e: unknown) {
  //     const error = e as Error;
  //     toast.error(error.message || "Failed to save chapters.");
  //     setChapterError(error.message || "Failed to save chapters.");
  //   } finally {
  //     setSavingChapters(false);
  //   }
  // };

  // ADD THE handleSaveStructure FUNCTION HERE (after line 535)
  const handleSaveStructure = async () => {
    if (!aiBook || !bookStructure) {
      toast.error("No book structure to save");
      return;
    }

    setSavingChapters(true);

    try {
      // Convert bookStructure to the format expected by the backend
      const structureData = {
        book_id: aiBook.id,
        has_sections: bookStructure.has_sections,
        structure_type: bookStructure.structure_type,
        sections: bookStructure.sections,
        chapters: bookStructure.chapters,
      };

      console.log("Saving structure:", structureData);

      // Save the hierarchical structure
      await apiClient.post(`/books/${aiBook.id}/save-structure`, structureData);

      toast.success("Book structure saved successfully!");
      setStep(5); // Move to next step
    } catch (error) {
      console.error("Error saving book structure:", error);
      toast.error("Failed to save book structure. Please try again.");
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

  const handleUploadBookClick = async () => {
    console.log("🚀 handleUploadBookClick called with bookMode:", bookMode);

    if (!user) return;
    setStep(2);

    // try {
    //   const formData = new FormData();
    //   formData.append("book_type", bookMode);
    //   if (uploadMethod === "file" && file) {
    //     formData.append("file", file);
    //   } else if (uploadMethod === "text" && textContent) {
    //     formData.append("text_content", textContent);
    //   } else {
    //     toast.error("Please provide a file or text content.");
    //     return;
    //   }

    //   const book = await apiClient.upload("/books/upload", formData);

    //   // Always proceed to step 2, ignoring payment requirements
    //   setAiBook(book as Book);
    //   setStep(2);
    // } catch (e) {
    //   const error = e as Error;
    //   toast.error(error.message || "Failed to upload book. Please try again.");
    // }
  };

  // const handleUploadBookClick = async () => {
  //   if (!user) return;
  //   if (
  //     (user.role && user.role.toLowerCase() === "superadmin") ||
  //     userBookCount < 1
  //   ) {
  //     try {
  //       const formData = new FormData();
  //       formData.append("book_type", bookMode);
  //       if (uploadMethod === "file" && file) {
  //         formData.append("file", file);
  //       } else if (uploadMethod === "text" && textContent) {
  //         formData.append("text_content", textContent);
  //       } else {
  //         toast.error("Please provide a file or text content.");
  //         return;
  //       }
  //       const book = await apiClient.upload("/books/upload", formData);
  //       if (
  //         typeof book === "object" &&
  //         book !== null &&
  //         "id" in book &&
  //         "status" in book
  //       ) {
  //         if (
  //           (book as { status?: string }).status === "PENDING_PAYMENT" &&
  //           (book as { id?: string }).id
  //         ) {
  //           // Immediately redirect to Stripe
  //           const checkoutSession =
  //             await stripeService.createBookUploadCheckoutSession(
  //               (book as { id: string }).id
  //             );
  //           stripeService.redirectToCheckout(
  //             (checkoutSession as { checkout_url: string }).checkout_url
  //           );
  //           return;
  //         } else {
  //           setAiBook(book as Book);
  //           setStep(2); // Proceed to next step
  //         }
  //       }
  //     } catch (e) {
  //       const error = e as Error;
  //       toast.error(
  //         error.message || "Failed to upload book. Please try again."
  //       );
  //     }
  //     return;
  //   }
  //   try {
  //     const formData = new FormData();
  //     formData.append("book_type", bookMode);
  //     if (uploadMethod === "file" && file) {
  //       formData.append("file", file);
  //     } else if (uploadMethod === "text" && textContent) {
  //       formData.append("text_content", textContent);
  //     } else {
  //       toast.error("Please provide a file or text content.");
  //       return;
  //     }
  //     const book = await apiClient.upload("/books/upload", formData);
  //     if (
  //       typeof book === "object" &&
  //       book !== null &&
  //       "payment_required" in book &&
  //       "id" in book
  //     ) {
  //       if (
  //         (book as { payment_required?: boolean }).payment_required &&
  //         (book as { id?: string }).id
  //       ) {
  //         // Immediately redirect to Stripe
  //         const checkoutSession =
  //           await stripeService.createBookUploadCheckoutSession(
  //             (book as { id: string }).id
  //           );
  //         stripeService.redirectToCheckout(
  //           (checkoutSession as { checkout_url: string }).checkout_url
  //         );
  //         return;
  //       } else {
  //         setAiBook(book as Book);
  //         setStep(2); // Proceed to next step
  //       }
  //     }
  //   } catch (e) {
  //     const error = e as Error;
  //     toast.error(
  //       error.message ||
  //         "Failed to upload book or initiate payment. Please try again."
  //     );
  //   }
  // };

  return (
    <div className="min-h-screen py-4 sm:py-8">
      <div className="max-w-4xl mx-auto px-2 sm:px-4 md:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2 sm:mb-4">
            Upload Your Book
          </h1>
          <p className="text-gray-600 text-sm sm:text-base">
            Transform your content into an interactive AI-powered experience
          </p>
          {userBookCount >= 1 && (
            <div className="mt-3 sm:mt-4 p-2 sm:p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-center space-x-2">
                <CreditCard className="h-5 w-5 text-blue-600" />
                <span className="text-blue-800 text-xs sm:text-sm font-medium">
                  You have uploaded {userBookCount} book
                  {userBookCount !== 1 ? "s" : ""}. Additional uploads require
                  payment.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Progress Steps */}
        <div className="mb-8 sm:mb-12">
          <div className="flex items-center justify-between overflow-x-auto scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent py-2">
            {steps.map((stepItem, index) => (
              <div
                key={stepItem.number}
                className="flex items-center min-w-[160px] sm:min-w-0"
              >
                <div
                  className={`flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 text-sm sm:text-base ${
                    step >= stepItem.number
                      ? "bg-purple-600 border-purple-600 text-white"
                      : "border-gray-300 text-gray-500"
                  }`}
                >
                  {step > stepItem.number ? (
                    <CheckCircle className="h-5 w-5 sm:h-6 sm:w-6" />
                  ) : (
                    <span className="font-medium">{stepItem.number}</span>
                  )}
                </div>
                <div className="ml-2 sm:ml-3 min-w-0">
                  <p
                    className={`text-xs sm:text-sm font-medium ${
                      step >= stepItem.number
                        ? "text-purple-600"
                        : "text-gray-500"
                    }`}
                  >
                    {stepItem.title}
                  </p>
                  <p className="text-[10px] sm:text-xs text-gray-500">
                    {stepItem.description}
                  </p>
                </div>
                {index < steps.length - 1 && (
                  <ArrowRight className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400 mx-2 sm:mx-4" />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl sm:rounded-2xl shadow-lg border border-gray-100 p-4 sm:p-8">
          {/* Step 1: Upload Method */}
          {step === 1 && (
            <div className="space-y-4 sm:space-y-6">
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6">
                How would you like to add your content?
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                <button
                  onClick={() => setUploadMethod("file")}
                  className={`w-full p-4 sm:p-8 rounded-2xl border-2 transition-all hover:scale-105 text-left ${
                    uploadMethod === "file"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <Upload className="h-10 w-10 sm:h-12 sm:w-12 text-purple-600 mx-auto mb-2 sm:mb-4" />
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1 sm:mb-2">
                    Upload File
                  </h3>
                  <p className="text-gray-600 text-xs sm:text-sm">
                    Upload a PDF, DOCX, TXT, or EPUB file of your book
                  </p>
                </button>

                <button
                  onClick={() => setUploadMethod("text")}
                  className={`w-full p-4 sm:p-8 rounded-2xl border-2 transition-all hover:scale-105 text-left ${
                    uploadMethod === "text"
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-300 hover:border-purple-300"
                  }`}
                >
                  <FileText className="h-10 w-10 sm:h-12 sm:w-12 text-purple-600 mx-auto mb-2 sm:mb-4" />
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1 sm:mb-2">
                    Paste Text
                  </h3>
                  <p className="text-gray-600 text-xs sm:text-sm">
                    Copy and paste your book content directly
                  </p>
                </button>
              </div>

              {uploadMethod === "file" && (
                <div className="mt-4 sm:mt-6">
                  <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1 sm:mb-2">
                    Select your book file
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-xl p-4 sm:p-8 text-center hover:border-purple-400 transition-colors">
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.epub"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <label htmlFor="file-upload" className="cursor-pointer">
                      <Book className="h-10 w-10 sm:h-12 sm:w-12 text-gray-400 mx-auto mb-2 sm:mb-4" />
                      <p className="text-gray-600 text-xs sm:text-sm">
                        {file ? file.name : "Click to upload or drag and drop"}
                      </p>
                      <p className="text-[10px] sm:text-xs text-gray-500 mt-1 sm:mt-2">
                        PDF, DOCX, TXT, or EPUB up to 10MB
                      </p>
                    </label>
                  </div>
                </div>
              )}

              {uploadMethod === "text" && (
                <div className="mt-4 sm:mt-6">
                  <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1 sm:mb-2">
                    Paste your book content
                  </label>
                  <textarea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    rows={8}
                    className="w-full border border-gray-300 rounded-xl p-3 sm:p-4 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-xs sm:text-base"
                    placeholder="Paste your book content here..."
                  />
                </div>
              )}

              <div className="flex flex-col sm:flex-row justify-end gap-3 sm:gap-0 mt-6 sm:mt-8">
                <button
                  onClick={handleUploadBookClick}
                  className="w-full sm:w-auto px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-all"
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

          {/* Step 3: AI Processing with Payment */}
          {step === 3 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                AI Processing
              </h2>
              <p className="text-gray-600 mb-4">
                Let AI analyze your book and auto-populate the details for you.
              </p>

              {/* Payment Required Section */}
              {paymentRequired && aiBook && (
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-xl p-6 mb-6">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <CreditCard className="h-8 w-8 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-blue-900 mb-2">
                        Payment Required
                      </h3>
                      <p className="text-blue-800 mb-4">
                        This is your {userBookCount + 1}
                        {userBookCount === 0
                          ? "st"
                          : userBookCount === 1
                          ? "nd"
                          : userBookCount === 2
                          ? "rd"
                          : "th"}{" "}
                        book upload. Additional uploads require a one-time
                        payment to continue processing.
                      </p>
                      <div className="bg-white/50 rounded-lg p-4 mb-4">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-blue-900">
                            Book Processing Fee
                          </span>
                          <span className="text-xl font-bold text-blue-900">
                            $9.99
                          </span>
                        </div>
                        <p className="text-sm text-blue-700 mt-1">
                          One-time payment per additional book
                        </p>
                      </div>
                      <button
                        onClick={handlePayment}
                        disabled={paymentProcessing}
                        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                      >
                        {paymentProcessing ? (
                          <>
                            <Settings className="h-5 w-5 animate-spin" />
                            <span>Processing...</span>
                          </>
                        ) : (
                          <>
                            <CreditCard className="h-5 w-5" />
                            <span>Pay & Continue Processing</span>
                          </>
                        )}
                      </button>
                      <p className="text-xs text-blue-600 mt-2 text-center">
                        Secure payment powered by Stripe
                      </p>
                    </div>
                  </div>
                </div>
              )}

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
                ) : paymentRequired ? (
                  <div className="flex flex-col items-center">
                    <AlertCircle className="h-12 w-12 text-blue-600 mb-4" />
                    <p className="text-gray-600 text-center">
                      Complete payment above to continue with AI processing
                    </p>
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

          {/* Step 4: Chapter Review
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
          )} */}

          {/* Step 4: Dynamic Chapter Review */}
          {step === 4 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Review & Edit{" "}
                {bookStructure?.structure_type === "flat"
                  ? "Chapters"
                  : bookStructure?.has_sections
                  ? `${getSectionLabel(bookStructure.structure_type)}s`
                  : "Chapters"}
              </h2>
              <p className="text-gray-600 mb-4">
                Review, edit, reorder, or add{" "}
                {bookStructure?.has_sections
                  ? "sections and chapters"
                  : "chapters"}
                . Only confirmed content will be saved.
              </p>

              {bookStructure?.has_sections ? (
                <HierarchicalStructureReview
                  structure={bookStructure}
                  onStructureChange={setBookStructure}
                />
              ) : (
                <div className="space-y-4">
                  {editableChapters.map((ch, idx) => (
                    <div
                      key={idx}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex justify-between items-center mb-2">
                        <h3 className="text-lg font-semibold">
                          Chapter {idx + 1}
                        </h3>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleMoveChapter(idx, "up")}
                            disabled={idx === 0}
                            className="text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                          >
                            ↑
                          </button>
                          <button
                            onClick={() => handleMoveChapter(idx, "down")}
                            disabled={idx === editableChapters.length - 1}
                            className="text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                          >
                            ↓
                          </button>
                          <button
                            onClick={() => handleRemoveChapter(idx)}
                            className="text-red-600 hover:text-red-800"
                          >
                            Remove
                          </button>
                        </div>
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
              )}

              <div className="flex justify-between mt-8">
                <button
                  onClick={handleBack}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-all"
                  disabled={savingChapters}
                >
                  Back
                </button>
                <button
                  onClick={handleSaveStructure}
                  disabled={savingChapters}
                  className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-blue-700 transition-all text-lg disabled:opacity-50"
                >
                  {savingChapters ? "Saving..." : "Confirm Structure"}
                </button>
              </div>
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

const HierarchicalStructureReview: React.FC<{
  structure: BookStructure;
  onStructureChange: (structure: BookStructure) => void;
}> = ({ structure, onStructureChange }) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set()
  );

  const moveChapter = (
    sectionIndex: number,
    chapterIndex: number,
    direction: "up" | "down"
  ) => {
    const newStructure = { ...structure };
    const section = newStructure.sections[sectionIndex];
    const chapters = [...section.chapters];

    const targetIndex =
      direction === "up" ? chapterIndex - 1 : chapterIndex + 1;

    if (targetIndex >= 0 && targetIndex < chapters.length) {
      [chapters[chapterIndex], chapters[targetIndex]] = [
        chapters[targetIndex],
        chapters[chapterIndex],
      ];
      newStructure.sections[sectionIndex] = { ...section, chapters };
      onStructureChange(newStructure);
    }
  };

  const removeChapter = (sectionIndex: number, chapterIndex: number) => {
    const newStructure = { ...structure };
    const section = newStructure.sections[sectionIndex];
    const chapters = section.chapters.filter((_, idx) => idx !== chapterIndex);
    newStructure.sections[sectionIndex] = { ...section, chapters };
    onStructureChange(newStructure);
  };

  const addChapter = (sectionIndex: number) => {
    const newStructure = { ...structure };
    const section = newStructure.sections[sectionIndex];
    const newChapter: Chapter = {
      id: `temp-${Date.now()}`,
      book_id: structure.id,
      section_id: section.id,
      chapter_number: section.chapters.length + 1,
      title: `New Chapter ${section.chapters.length + 1}`,
      content: "",
      summary: "",
      order_index: section.chapters.length,
    };

    newStructure.sections[sectionIndex] = {
      ...section,
      chapters: [...section.chapters, newChapter],
    };
    onStructureChange(newStructure);
  };

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getSectionIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "tablet":
        return "📜";
      case "part":
        return "📖";
      case "book":
        return "📚";
      case "section":
        return "📄";
      case "chapter":
        return "📝";
      case "act":
        return "🎭";
      case "scene":
        return "🎬";
      case "unit":
        return "🎯";
      case "lesson":
        return "🎓";
      default:
        return "📄";
    }
  };

  const getSectionLabel = (type: string) => {
    switch (type.toLowerCase()) {
      case "tablet":
        return "Tablet";
      case "part":
        return "Part";
      case "book":
        return "Book";
      case "section":
        return "Section";
      case "chapter":
        return "Chapter";
      case "act":
        return "Act";
      case "scene":
        return "Scene";
      case "unit":
        return "Unit";
      case "lesson":
        return "Lesson";
      default:
        return "Section";
    }
  };

  return (
    <div className="space-y-4">
      {structure.sections.map((section, sectionIndex) => (
        <div
          key={section.id}
          className="border border-gray-200 rounded-lg overflow-hidden"
        >
          {/* Section Header */}
          <div
            className="bg-gray-50 p-4 cursor-pointer hover:bg-gray-100 transition-colors"
            onClick={() => toggleSection(section.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">
                  {getSectionIcon(section.section_type)}
                </span>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {getSectionLabel(section.section_type)}{" "}
                    {section.section_number}: {section.title}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {section.chapters.length} chapter
                    {section.chapters.length !== 1 ? "s" : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Add chapter to this section
                  }}
                  className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm"
                >
                  + Chapter
                </button>
                {expandedSections.has(section.id) ? (
                  <span className="text-gray-500">▲</span>
                ) : (
                  <span className="text-gray-500">▲</span>
                )}
                {/* {expandedSections.has(section.id) ? 
                  <ChevronUpIcon className="h-5 w-5 text-gray-500" /> : 
                  <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                } */}
              </div>
            </div>
          </div>

          {/* Section Content */}
          {expandedSections.has(section.id) && (
            <div className="p-4 space-y-4">
              {section.chapters.map((chapter, chapterIndex) => (
                <div
                  key={chapter.id}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900">
                      Chapter {chapterIndex + 1}
                    </h4>
                    <div className="flex space-x-2">
                      <button
                        onClick={() =>
                          moveChapter(sectionIndex, chapterIndex, "up")
                        }
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        ↑
                      </button>
                      <button
                        onClick={() =>
                          moveChapter(sectionIndex, chapterIndex, "down")
                        }
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        ↓
                      </button>
                      <button
                        onClick={() =>
                          removeChapter(sectionIndex, chapterIndex)
                        }
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-2"
                    placeholder="Chapter Title"
                    value={chapter.title}
                    onChange={(e) => {
                      // Update chapter title
                    }}
                  />

                  <textarea
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="Chapter Content"
                    rows={4}
                    value={chapter.content}
                    onChange={(e) => {
                      // Update chapter content
                    }}
                  />
                </div>
              ))}

              {section.chapters.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>
                    No chapters in this{" "}
                    {getSectionLabel(section.section_type).toLowerCase()}
                  </p>
                  <button className="mt-2 px-4 py-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                    Add First Chapter
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      <button className="w-full p-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400 hover:text-gray-800 transition-colors">
        {/* + Add New {getSectionLabel(structure.structure_type)} */}+ Add New{" "}
        {getSectionLabel(structure?.structure_type || "section")}
      </button>
    </div>
  );
};
