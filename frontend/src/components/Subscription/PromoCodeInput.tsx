import React, { useState } from "react";
import { ChevronDown, Loader2, Ticket } from "lucide-react";
import { apiClient } from "../../lib/api";
import { dispatchCreditsRefresh } from "../../lib/credits";

interface PromoRedeemResponse {
  credits_granted?: number;
  grant?: {
    credits_granted?: number;
  };
  message?: string;
}

interface PromoCodeInputProps {
  title?: string;
  defaultExpanded?: boolean;
  onRedeemed?: (creditsGranted: number) => void;
}

export default function PromoCodeInput({
  title = "Have a promo code?",
  defaultExpanded = false,
  onRedeemed,
}: PromoCodeInputProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [code, setCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleRedeem = async () => {
    const normalizedCode = code.trim();
    if (!normalizedCode) {
      setError("Please enter a promo code.");
      setSuccess(null);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiClient.post<PromoRedeemResponse>("/promo/redeem", {
        code: normalizedCode,
      });

      const creditsGranted =
        response.credits_granted ?? response.grant?.credits_granted ?? 0;

      setSuccess(
        creditsGranted > 0
          ? `Promo applied. ${creditsGranted.toLocaleString()} credits added.`
          : response.message || "Promo code redeemed successfully."
      );
      setCode("");
      dispatchCreditsRefresh();
      if (onRedeemed) {
        onRedeemed(creditsGranted);
      }
    } catch (err) {
      const fallbackMessage = "Invalid, expired, or already redeemed promo code.";
      setError(err instanceof Error ? err.message.replace(/^\[\d+\]\s*/, "") : fallbackMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 sm:p-5">
      <button
        type="button"
        onClick={() => setIsExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-left"
      >
        <span className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-gray-500 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Ticket className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="Enter promo code"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                disabled={isSubmitting}
              />
            </div>
            <button
              type="button"
              onClick={handleRedeem}
              disabled={isSubmitting}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Redeem
            </button>
          </div>

          {success && (
            <p className="text-sm text-green-600 dark:text-green-400">{success}</p>
          )}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}
