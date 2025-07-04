import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { userService } from "../services/userService";
import { toast } from "react-hot-toast";
import BookViewForLearning from "./BookViewForLearning";
import BookViewForEntertainment from "./BookViewForEntertainment";

interface Book {
  id: string;
  title: string;
  book_type: string;
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
      console.error("Error loading book:", error);
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
    return <BookViewForLearning />;
  } else {
    return <BookViewForEntertainment />;
  }
}
