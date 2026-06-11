import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { apiClient } from "../lib/api";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

const INVALID_TOKEN_MESSAGE =
  "This activation link is invalid or expired. Please register again or request a new link.";

// Build the login URL, pre-filling the email when the backend gave us one
// (AuthPage reads ?email= to populate the login form — same pattern used after registration).
const loginUrl = (email?: string) =>
  email ? `/auth?mode=login&email=${encodeURIComponent(email)}` : "/auth?mode=login";

export default function ActivationPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const activateAccount = async () => {
      if (!token) {
        setStatus("error");
        setMessage(INVALID_TOKEN_MESSAGE);
        return;
      }

      try {
        // 200 OK — token validated and account activated now.
        const response = await apiClient.get<{ message: string; email: string }>(
          `/auth/activate/${token}`
        );
        setStatus("success");
        setMessage("Your account is activated. Please login.");
        toast.success("Your account is activated. Please login.");

        setTimeout(() => {
          navigate(loginUrl(response.email));
        }, 1500);
      } catch (error) {
        // apiClient throws Error("[<status>] <message>"); parse both so we can
        // tell "already activated" (user is fine) apart from a truly bad token.
        const raw = error instanceof Error ? error.message : "";
        const statusCode = Number(raw.match(/^\[(\d+)\]/)?.[1] ?? 0);
        const detail = raw.replace(/^\[\d+\]\s*/, "").trim();

        const alreadyActivated =
          statusCode === 409 || /already activated/i.test(detail);

        if (alreadyActivated) {
          // 409 Conflict, or 400 with "already activated" — account is already
          // active, so this is informational, not an error.
          setStatus("success");
          setMessage("Account already activated. Please login.");
          toast("Account already activated. Please login.", { icon: "ℹ️" });

          setTimeout(() => {
            navigate(loginUrl());
          }, 1500);
          return;
        }

        // 400 (invalid) / 410 (expired) / 404 — keep the red error UI.
        setStatus("error");
        setMessage(INVALID_TOKEN_MESSAGE);
      }
    };

    activateAccount();
  }, [token, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0F0F23] p-4">
      <div className="w-full max-w-md bg-white dark:bg-[#13132B] rounded-3xl shadow-2xl p-8 border border-gray-200 dark:border-white/5">
        <div className="text-center">
          {status === "loading" && (
            <>
              <Loader2 className="w-16 h-16 mx-auto text-purple-600 animate-spin mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Activating Your Account
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we activate your account...
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="w-16 h-16 mx-auto text-green-500 mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Account Activated!
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Redirecting to login page...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="w-16 h-16 mx-auto text-red-500 mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Activation Failed
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
              <button
                onClick={() => navigate("/auth?mode=login")}
                className="px-6 py-2.5 bg-[#635BFF] hover:bg-[#5B36F5] text-white rounded-xl font-bold transition-all"
              >
                Go to Login
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
