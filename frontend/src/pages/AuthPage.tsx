import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Mail, Lock, User, Eye, EyeOff, Shield } from "lucide-react";
import { toast } from "react-hot-toast";
import PasswordReset from "../components/PasswordReset";
import { apiClient } from "../lib/api";

// Helper for Google Icon
const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
  </svg>
);

// Helper for Facebook Icon
const FacebookIcon = () => (
  <svg className="w-5 h-5 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
  </svg>
);

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const [isLogin, setIsLogin] = useState(searchParams.get('mode') !== 'register');
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

  // Sync mode with URL params
  useEffect(() => {
    setIsLogin(searchParams.get('mode') !== 'register');
  }, [searchParams]);

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
        setIsLogin(true);
        setPassword("");
        setConfirmPassword("");
        setLoading(false);
        return;
      }
      
      try {
        const user = await apiClient.get<any>("/users/me");
        const hasCreator = user.roles?.includes('creator');
        const hasExplorer = user.roles?.includes('explorer');
        
        if (hasCreator && !hasExplorer) {
            navigate('/creator');
        } else if (!hasCreator && hasExplorer) {
            navigate('/dashboard');
        } else {
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
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-[#0F0F23] text-gray-900 dark:text-white overflow-hidden relative transition-colors duration-300">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
         <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/10 dark:bg-purple-600/20 blur-[120px] rounded-full"></div>
         <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/10 dark:bg-blue-600/10 blur-[120px] rounded-full"></div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4 relative z-10 pt-24">
        <div className="w-full max-w-md">
            {/* Glass Card */}
            <div className="bg-white/70 dark:bg-[#13132B]/80 backdrop-blur-xl border border-gray-200 dark:border-white/5 rounded-3xl p-8 shadow-2xl transition-all duration-300">
                
                <div className="text-center mb-10">
                    <h1 className="text-3xl font-bold mb-3 bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
                        {isLogin ? "Welcome Back!" : "Start Creating AI Videos"}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">
                        {isLogin 
                          ? "Access your projects, track your video history, and continue where you left off." 
                          : "Turn your script or prompt into stunning videos instantly. Sign up for free today."}
                    </p>
                </div>

                <form className="space-y-5" onSubmit={handleSubmit}>
                    
                    {!isLogin && (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">First Name</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        required
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        placeholder="First name"
                                        className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                                    />
                                    <User className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Last Name</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        required
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                        placeholder="Last name"
                                        className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                                    />
                                    <User className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                                </div>
                            </div>
                        </div>
                    )}

                    {!isLogin && (
                         <div>
                            <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Username</label>
                            <div className="relative">
                                <input
                                    type="text"
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Enter username"
                                    className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                                />
                                <User className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                            </div>
                        </div>
                    )}

                    <div>
                        <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Email</label>
                        <div className="relative">
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Enter email"
                                className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                            />
                            <Mail className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                        </div>
                    </div>

                    <div>
                        <div className="flex justify-between items-center mb-1.5 ml-1">
                            <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400">Password</label>
                            {isLogin && (
                                <button type="button" onClick={() => setShowPasswordReset(true)} className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-500 dark:hover:text-purple-300 transition-colors">
                                    Forgot Password?
                                </button>
                            )}
                        </div>
                        <div className="relative">
                            <input
                                type={showPassword ? "text" : "password"}
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10 pr-10"
                            />
                            <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute right-3 top-3.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                    </div>

                    {!isLogin && (
                        <>
                             <div>
                                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Confirm Password</label>
                                <div className="relative">
                                    <input
                                        type={showConfirmPassword ? "text" : "password"}
                                        required
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="Retype password"
                                        className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10 pr-10"
                                    />
                                    <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                                     <button
                                      type="button"
                                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                      className="absolute right-3 top-3.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                                    >
                                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Security Question</label>
                                <div className="relative">
                                    <div className="grid grid-cols-1 gap-3">
                                        <div className="relative">
                                            <select
                                                required
                                                value={securityQuestion}
                                                onChange={(e) => setSecurityQuestion(e.target.value)}
                                                className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10 appearance-none"
                                            >
                                                <option value="" className="bg-white dark:bg-[#1A1A2E]">Select Question</option>
                                                <option value="mother_maiden_name" className="bg-white dark:bg-[#1A1A2E]">Mother's maiden name?</option>
                                                <option value="childhood_friend" className="bg-white dark:bg-[#1A1A2E]">Childhood friend's name?</option>
                                                <option value="favorite_color" className="bg-white dark:bg-[#1A1A2E]">Favorite color?</option>
                                                <option value="birth_city" className="bg-white dark:bg-[#1A1A2E]">Birth city?</option>
                                            </select>
                                            <Shield className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                                        </div>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                required
                                                value={securityAnswer}
                                                onChange={(e) => setSecurityAnswer(e.target.value)}
                                                placeholder="Answer"
                                                className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                                            />
                                            <Shield className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/5">
                                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">Profile Type</label>
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        onClick={() => toggleRole("explorer")}
                                        className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${
                                            selectedRoles.includes("explorer") 
                                            ? "bg-green-500/20 text-green-700 dark:text-green-400 border border-green-500/50" 
                                            : "bg-gray-100 dark:bg-black/20 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 border border-transparent"
                                        }`}
                                    >
                                        Explorer
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => toggleRole("author")}
                                        className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${
                                            selectedRoles.includes("author") 
                                            ? "bg-blue-500/20 text-blue-700 dark:text-blue-400 border border-blue-500/50" 
                                            : "bg-gray-100 dark:bg-black/20 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 border border-transparent"
                                        }`}
                                    >
                                        Creator
                                    </button>
                                </div>
                            </div>
                        </>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-3.5 bg-[#635BFF] hover:bg-[#5B36F5] text-white rounded-xl font-bold tracking-wide shadow-lg shadow-purple-900/30 transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed mt-4"
                    >
                        {loading ? "Processing..." : (isLogin ? "Login" : "Register")}
                    </button>

                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="px-2 bg-white dark:bg-[#13132B] text-gray-500 dark:text-gray-400">or {isLogin ? "Login" : "Register"} with:</span>
                        </div>
                    </div>

                    <div className="flex justify-center gap-4">
                        <button type="button" className="p-3 bg-gray-50 dark:bg-[#1A1A2E] border border-gray-200 dark:border-gray-700 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                            <GoogleIcon />
                        </button>
                         <button type="button" className="p-3 bg-gray-50 dark:bg-[#1A1A2E] border border-gray-200 dark:border-gray-700 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                            <FacebookIcon />
                        </button>
                    </div>

                    <div className="text-center mt-6">
                         <button
                            type="button"
                            onClick={() => {
                                setIsLogin(!isLogin);
                                setPassword("");
                                setConfirmPassword("");
                            }}
                            className="text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
                         >
                            {isLogin 
                             ? <span>Don't have an account? <span className="text-[#635BFF]">Register</span></span>
                             : <span>Already have an account? <span className="text-[#635BFF]">Login</span></span>}
                         </button>
                    </div>
                </form>
            </div>

            <div className="mt-8 text-center">
                 <button
                    onClick={handleResendVerification}
                    className="text-xs text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                  >
                    Didn't receive verification email?
                 </button>
            </div>
        </div>
      </div>
    </div>
  );
}
