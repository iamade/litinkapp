import { apiClient } from "../lib/api";

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

export interface PaymentStatusResponse {
  book_id: string;
  status: string;
  payment_status: string;
  requires_payment: boolean;
}

export interface UserBookCountResponse {
  user_id: string;
  book_count: number;
  next_book_requires_payment: boolean;
}

export const stripeService = {
  /**
   * Create a Stripe checkout session for book upload payment
   */
  createBookUploadCheckoutSession: async (
    bookId: string
  ): Promise<CheckoutSessionResponse> => {
    try {
      const response = await apiClient.post<CheckoutSessionResponse>(
        "/payments/create-book-upload-checkout-session",
        { book_id: bookId }
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Check the payment status of a book
   */
  checkPaymentStatus: async (bookId: string): Promise<PaymentStatusResponse> => {
    try {
      const response = await apiClient.get<PaymentStatusResponse>(
        `/payments/check-payment-status/${bookId}`
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get the user's book count and payment requirements
   */
  getUserBookCount: async (): Promise<UserBookCountResponse> => {
    try {
      const response = await apiClient.get<UserBookCountResponse>(
        "/payments/user-book-count"
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Redirect to Stripe Checkout
   */
  redirectToCheckout: (checkoutUrl: string): void => {
    window.location.href = checkoutUrl;
  },
};