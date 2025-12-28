import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "../lib/api";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function ActivationPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const activateAccount = async () => {
      if (!token) {
        setStatus("error");
        setMessage("Invalid activation link");
        return;
      }

      try {
        const response = await apiClient.get<{ message: string; email: string }>(
          `/auth/activate/${token}`
        );
        setStatus("success");
        setMessage(response.message || "Account activated successfully!");
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate("/auth?mode=login");
        }, 3000);
      } catch (error) {
        setStatus("error");
        if (error instanceof Error) {
          setMessage(error.message.replace(/^\[\d+\]\s*/, ""));
        } else {
          setMessage("Failed to activate account. The link may be invalid or expired.");
        }
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
