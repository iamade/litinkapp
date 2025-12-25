import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { Mail, ArrowLeft, ArrowRight,  Sun, Moon } from "lucide-react";
import { toast } from "react-hot-toast";

interface PasswordResetProps {
  onBack: () => void;
}

export default function PasswordReset({ onBack }: PasswordResetProps) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const { requestPasswordReset } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await requestPasswordReset(email);
      toast.success("Password reset email sent! Check your inbox.");
      onBack();
    } catch (error) {
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to send password reset email.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-[#0F0F23] text-gray-900 dark:text-white overflow-hidden relative transition-colors duration-300">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
         <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/10 dark:bg-purple-600/20 blur-[120px] rounded-full"></div>
         <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/10 dark:bg-blue-600/10 blur-[120px] rounded-full"></div>
      </div>

      {/* Header / Nav */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2">
            <span className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">Litinkai</span>
        </div>
        
        <div className="flex items-center gap-4">
             <button
               onClick={toggleTheme}
               className="p-2 rounded-full text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
               aria-label="Toggle theme"
             >
               {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
             </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4 relative z-10">
        <div className="w-full max-w-md">
            {/* Glass Card */}
            <div className="bg-white/70 dark:bg-[#13132B]/80 backdrop-blur-xl border border-gray-200 dark:border-white/5 rounded-3xl p-8 shadow-2xl transition-all duration-300">
                
                <div className="text-center mb-10">
                    <h1 className="text-3xl font-bold mb-3 bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
                        Reset Password
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">
                        Enter your email address and we'll send you a link to reset your password.
                    </p>
                </div>

                <form className="space-y-6" onSubmit={handleRequestReset}>
                    <div>
                        <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Email</label>
                        <div className="relative">
                            <input
                                id="email"
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Enter your email"
                                className="w-full bg-white dark:bg-[#0A0A1B] border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder-gray-400 dark:placeholder-gray-600 pl-10"
                            />
                            <Mail className="w-4 h-4 text-gray-400 dark:text-gray-500 absolute left-3 top-3.5" />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-3.5 bg-[#635BFF] hover:bg-[#5B36F5] text-white rounded-xl font-bold tracking-wide shadow-lg shadow-purple-900/30 transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {loading ? "Sending..." : "Send Reset Link"}
                        {!loading && <ArrowRight className="w-4 h-4" />}
                    </button>
                    
                    <div className="text-center">
                        <button
                          type="button"
                          onClick={onBack}
                          className="flex items-center justify-center mx-auto text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors gap-2"
                        >
                          <ArrowLeft className="h-4 w-4" />
                          Back to Sign In
                        </button>
                    </div>
                </form>
            </div>
            
            <div className="text-center mt-8">
               <p className="text-xs text-gray-500">
                  <span className="opacity-75">Protected by reCAPTCHA and subject to the Google </span>
                  <a href="#" className="hover:text-gray-300">Privacy Policy</a>
                  <span className="opacity-75"> and </span> 
                  <a href="#" className="hover:text-gray-300">Terms of Service</a>.
               </p>
            </div>
        </div>
      </div>
    </div>
  );
}
