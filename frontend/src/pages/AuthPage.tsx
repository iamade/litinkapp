import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Mail, Lock, User, UserCheck, Eye, EyeOff, Shield } from "lucide-react";
import { toast } from "react-hot-toast";
import PasswordReset from "../components/PasswordReset";
import { apiClient } from "../lib/api";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<("author" | "explorer")[]>(["explorer"]);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const { login, register, resendVerificationEmail } = useAuth();
  const navigate = useNavigate();

  const toggleRole = (role: "author" | "explorer") => {
    setSelectedRoles(prev => {
      if (prev.includes(role)) {
        return prev.length > 1 ? prev.filter(r => r !== role) : prev;
      } else {
        return [...prev, role];
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Logged in successfully!");
      } else {
        if (password !== confirmPassword) {
          toast.error("Passwords do not match.");
          setLoading(false);
          return;
        }
        if (password.length < 6) {
          toast.error("Password must be at least 6 characters long.");
          setLoading(false);
          return;
        }
        if (selectedRoles.length === 0) {
          toast.error("Please select at least one profile type.");
          setLoading(false);
          return;
        }
        await register(username, email, password, confirmPassword, firstName, lastName, securityQuestion, securityAnswer, selectedRoles);
        toast.success(
          "Account created successfully! Please check your email for verification."
        );
        // Don't navigate - user needs to verify email first
        // Switch to login mode so they can log in after verification
        setIsLogin(true);
        setPassword("");
        setConfirmPassword("");
        setLoading(false);
        return;
      }
      
      // Only try to navigate after login (not registration)
      try {
        const user = await apiClient.get<any>("/users/me");
        const hasCreator = user.roles?.includes('creator');
        const hasExplorer = user.roles?.includes('explorer');
        
        if (hasCreator && !hasExplorer) {
            navigate('/creator');
        } else if (!hasCreator && hasExplorer) {
            navigate('/dashboard');
        } else {
            // Both or neither
            if (user.preferred_mode === 'creator') {
                navigate('/creator');
            } else {
                navigate('/dashboard');
            }
        }
      } catch (err) {
         console.error("Failed to fetch user profile for redirect", err);
         navigate("/dashboard");
      }
    } catch (error) {
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("An unknown error occurred.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!email) {
      toast.error("Please enter your email address first.");
      return;
    }

    try {
      await resendVerificationEmail(email);
      toast.success("Verification email sent! Check your inbox.");
    } catch (error) {
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to send verification email.");
      }
    }
  };

  if (showPasswordReset) {
    return <PasswordReset onBack={() => setShowPasswordReset(false)} />;
  }

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
            {isLogin ? "Welcome back to Litink" : "Join the Litink community"}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {isLogin
              ? "Sign in to continue your reading journey"
              : "Transform your reading experience with AI"}
          </p>
        </div>

        <div className="bg-white p-8 rounded-2xl shadow-xl border border-purple-100">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  I want to... (select one or both)
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => toggleRole("explorer")}
                    className={`flex items-center justify-center px-4 py-3 rounded-xl border-2 transition-all ${
                      selectedRoles.includes("explorer")
                        ? "border-green-500 bg-green-50 text-green-700"
                        : "border-gray-300 hover:border-green-300 text-gray-600"
                    }`}
                  >
                    <User className="h-5 w-5 mr-2" />
                    <span className="text-sm font-medium">Explore & Learn</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleRole("author")}
                    className={`flex items-center justify-center px-4 py-3 rounded-xl border-2 transition-all ${
                      selectedRoles.includes("author")
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-300 hover:border-blue-300 text-gray-600"
                    }`}
                  >
                    <UserCheck className="h-5 w-5 mr-2" />
                    <span className="text-sm font-medium">Create Content</span>
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  You can always add or remove profiles later from your dashboard
                </p>
              </div>
            )}

            {!isLogin && (
              <>
                {/* First Name and Last Name row */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="firstName"
                      className="block text-sm font-medium text-gray-700"
                    >
                      First Name
                    </label>
                    <div className="mt-1 relative">
                      <input
                        id="firstName"
                        name="firstName"
                        type="text"
                        required
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                        placeholder="First name"
                      />
                      <User className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                    </div>
                  </div>
                  <div>
                    <label
                      htmlFor="lastName"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Last Name
                    </label>
                    <div className="mt-1 relative">
                      <input
                        id="lastName"
                        name="lastName"
                        type="text"
                        required
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                        placeholder="Last name"
                      />
                      <User className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                    </div>
                  </div>
                </div>

                {/* Username */}
                <div>
                  <label
                    htmlFor="username"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Username
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="username"
                      name="username"
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                      placeholder="Choose a username"
                    />
                    <User className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                  </div>
                </div>
              </>
            )}

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

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <div className="mt-1 relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-3 pl-10 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                  placeholder="Enter your password"
                />
                <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {!isLogin && (
              <>
                {/* Confirm Password */}
                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Confirm Password
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete="new-password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="appearance-none relative block w-full px-3 py-3 pl-10 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                      placeholder="Confirm your password"
                    />
                    <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-5 w-5" />
                      ) : (
                        <Eye className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Security Question */}
                <div>
                  <label
                    htmlFor="securityQuestion"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Security Question
                  </label>
                  <div className="mt-1 relative">
                    <select
                      id="securityQuestion"
                      name="securityQuestion"
                      required
                      value={securityQuestion}
                      onChange={(e) => setSecurityQuestion(e.target.value)}
                      className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                    >
                      <option value="">Select a security question</option>
                      <option value="mother_maiden_name">What is your mother's maiden name?</option>
                      <option value="childhood_friend">What was your childhood friend's name?</option>
                      <option value="favorite_color">What is your favorite color?</option>
                      <option value="birth_city">What city were you born in?</option>
                    </select>
                    <Shield className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                  </div>
                </div>

                {/* Security Answer */}
                <div>
                  <label
                    htmlFor="securityAnswer"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Security Answer
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="securityAnswer"
                      name="securityAnswer"
                      type="text"
                      required
                      value={securityAnswer}
                      onChange={(e) => setSecurityAnswer(e.target.value)}
                      className="appearance-none relative block w-full px-3 py-3 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-xl focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10"
                      placeholder="Your answer"
                    />
                    <Shield className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
                  </div>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
            >
              {loading
                ? "Please wait..."
                : isLogin
                ? "Sign In"
                : "Create Account"}
            </button>
          </form>

          <div className="mt-6 space-y-4">
            {isLogin && (
              <div className="text-center">
                <button
                  onClick={() => setShowPasswordReset(true)}
                  className="text-purple-600 hover:text-purple-500 text-sm font-medium"
                >
                  Forgot your password?
                </button>
              </div>
            )}

            {/* Resend verification - show on both login and registration */}
            <div className="text-center">
              <button
                type="button"
                onClick={handleResendVerification}
                className="text-purple-600 hover:text-purple-500 text-sm font-medium"
              >
                Didn't receive verification email?
              </button>
            </div>

            <div className="text-center">
              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  setEmail("");
                  setPassword("");
                  setConfirmPassword("");
                  setUsername("");
                  setFirstName("");
                  setLastName("");
                  setSecurityQuestion("");
                  setSecurityAnswer("");
                  setShowPassword(false);
                  setShowConfirmPassword(false);
                }}
                className="text-purple-600 hover:text-purple-500 text-sm font-medium"
              >
                {isLogin
                  ? "Don't have an account? Sign up"
                  : "Already have an account? Sign in"}
              </button>
            </div>
          </div>
        </div>

        <div className="text-center">
          <p className="text-xs text-gray-500">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
