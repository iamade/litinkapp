import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";
import BookViewForLearning from "./BookViewForLearning";
import BookViewForEntertainment from "./BookViewForEntertainment";
import { ErrorBoundary } from "../components/ErrorBoundary";

interface Chapter {
  id: string;
  title: string;
  content: string;
}

interface Book {
  id: string;
  title: string;
  author_name?: string;
  description?: string;
  cover_image_url?: string;
  book_type: string;
  difficulty?: string;
  tags?: string[]; // Replace 'any' with string[]
  language?: string;
  user_id: string;
  status: string;
  total_chapters?: number;
  estimated_duration?: number | string; // Replace 'any' with number or string
  created_at: string;
  updated_at: string;
  chapters?: Chapter[]; // Replace 'any[]' with Chapter[]
}

export default function BookView() {
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<Book | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load book data to determine type
  const loadBook = async (bookId: string) => {
    try {
      setIsLoading(true);
      const bookData = await userService.getBook(bookId);
      setBook(bookData);
    } catch (error) {
      toast.error("Failed to load book");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadBook(id);
    }
  }, [id]);

  if (isLoading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  if (!book) {
    return <div className="p-8 text-center text-red-500">Book not found.</div>;
  }

  // Route to appropriate component based on book type
  if (book.book_type === "learning") {
    return (
      <ErrorBoundary>
        <BookViewForLearning />
      </ErrorBoundary>
    );
  } else {
    return (
      <ErrorBoundary>
        <BookViewForEntertainment book={book} />
      </ErrorBoundary>
    );
  }
}
