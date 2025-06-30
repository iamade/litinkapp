import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Mail, Lock, ArrowLeft, CheckCircle } from "lucide-react";
import { toast } from "react-hot-toast";

interface PasswordResetProps {
  onBack: () => void;
}

export default function PasswordReset({ onBack }: PasswordResetProps) {
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { requestPasswordReset, confirmPasswordReset } = useAuth();

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await requestPasswordReset(email);
      toast.success("Password reset email sent! Check your inbox.");
      setStep("confirm");
    } catch (error) {
      console.error("Password reset request error:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to send password reset email.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    if (newPassword.length < 6) {
      toast.error("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);

    try {
      await confirmPasswordReset(email, token, newPassword);
      toast.success("Password reset successfully!");
      onBack(); // Go back to login
    } catch (error) {
      console.error("Password reset confirmation error:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to reset password.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="flex justify-center">
            <img
              src="/litink.png"
              alt="Litink Logo"
              className="h-20 w-20 object-contain"
            />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            {step === "request" ? "Reset Your Password" : "Enter Reset Code"}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {step === "request"
              ? "Enter your email to receive a reset link"
              : "Enter the code from your email and your new password"}
          </p>
        </div>

        <div className="bg-white p-8 rounded-2xl shadow-xl border border-purple-100">
          {step === "request" ? (
            <form className="space-y-6" onSubmit={handleRequestReset}>
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-700"
                >
                  Email address
                </label>
                <div className="mt-1 relative">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                    placeholder="Enter your email"
                  />
                  <Mail className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
              >
                {loading ? "Sending..." : "Send Reset Email"}
              </button>
            </form>
          ) : (
            <form className="space-y-6" onSubmit={handleConfirmReset}>
              <div>
                <label
                  htmlFor="token"
                  className="block text-sm font-medium text-gray-700"
                >
                  Reset Code
                </label>
                <div className="mt-1 relative">
                  <input
                    id="token"
                    name="token"
                    type="text"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                    placeholder="Enter the code from your email"
                  />
                  <CheckCircle className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                </div>
              </div>

              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-sm font-medium text-gray-700"
                >
                  New Password
                </label>
                <div className="mt-1 relative">
                  <input
                    id="newPassword"
                    name="newPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                    placeholder="Enter your new password"
                  />
                  <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                </div>
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium text-gray-700"
                >
                  Confirm New Password
                </label>
                <div className="mt-1 relative">
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                    placeholder="Confirm your new password"
                  />
                  <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
              >
                {loading ? "Resetting..." : "Reset Password"}
              </button>
            </form>
          )}

          <div className="mt-6 text-center">
            <button
              onClick={onBack}
              className="flex items-center justify-center mx-auto text-purple-600 hover:text-purple-500 text-sm font-medium"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to Sign In
            </button>
          </div>
        </div>

        <div className="text-center">
          <p className="text-xs text-gray-500">
            Need help? Contact our support team
          </p>
        </div>
      </div>
    </div>
  );
}
