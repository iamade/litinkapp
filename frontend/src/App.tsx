import React, { createContext, useContext, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { Toaster } from "react-hot-toast";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import ProjectView from "./pages/ProjectView";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import AuthorPanel from "./pages/AuthorPanel";
import LearningMode from "./pages/LearningMode";
import EntertainmentMode from "./pages/EntertainmentMode";
import CreatorMode from "./pages/CreatorMode";
import Profile from "./pages/Profile";
import BookUpload from "./pages/BookUpload";
import BookView from "./pages/BookView";
import SubscriptionPage from "./pages/SubscriptionPage";
import AdminDashboard from "./pages/AdminDashboard";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import OnboardingPage from "./pages/OnboardingPage";
import ActivationPage from "./pages/ActivationPage";
import { setLoadingContextSetter } from "./lib/api";
import { VideoGenerationProvider } from "./contexts/VideoGenerationContext";
import { ScriptSelectionProvider } from "./contexts/ScriptSelectionContext";
import { StoryboardProvider } from "./contexts/StoryboardContext";
import { INSUFFICIENT_CREDITS_EVENT, InsufficientCreditsEventDetail } from "./lib/credits";

// Global Loading Context
export const LoadingContext = createContext({
  setLoading: (v: boolean) => {},
  loading: false,
});
export const useLoading = () => useContext(LoadingContext);

export function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(false);
  // Register the setter once
  React.useEffect(() => {
    setLoadingContextSetter(setLoading);
  }, []);
  return (
    <LoadingContext.Provider value={{ loading, setLoading }}>
      {children}
      {loading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-purple-600"></div>
        </div>
      )}
    </LoadingContext.Provider>
  );
}

function InsufficientCreditsModalHandler() {
  const navigate = useNavigate();
  const [insufficientCredits, setInsufficientCredits] = useState<InsufficientCreditsEventDetail | null>(null);

  React.useEffect(() => {
    const onInsufficientCredits = (event: Event) => {
      const customEvent = event as CustomEvent<InsufficientCreditsEventDetail>;
      if (!customEvent.detail) return;
      setInsufficientCredits(customEvent.detail);
    };

    window.addEventListener(INSUFFICIENT_CREDITS_EVENT, onInsufficientCredits);
    return () => {
      window.removeEventListener(INSUFFICIENT_CREDITS_EVENT, onInsufficientCredits);
    };
  }, []);

  if (!insufficientCredits) return null;

  const missingCredits = Math.max(0, insufficientCredits.required - insufficientCredits.balance);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900">Insufficient Credits</h3>
        <p className="mt-2 text-sm text-gray-700">
          You need {missingCredits} more credits. Current balance: {insufficientCredits.balance}
        </p>
        <div className="mt-5 flex items-center justify-end gap-3">
          <button
            onClick={() => setInsufficientCredits(null)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
          <button
            onClick={() => {
              setInsufficientCredits(null);
              navigate("/subscription");
            }}
            className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
          >
            Upgrade
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ScriptSelectionProvider>
          <VideoGenerationProvider>
            <StoryboardProvider>
              <LoadingProvider>
                <Router>
                  <Toaster position="top-center" reverseOrder={false} />
                  <InsufficientCreditsModalHandler />
                  <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50 dark:from-gray-900 dark:to-gray-800 transition-colors">
                    <Navbar />
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/auth" element={<AuthPage />} />
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/author" element={<AuthorPanel />} />
                      <Route path="/learn" element={<LearningMode />} />
                      <Route path="/explore" element={<EntertainmentMode />} />
                      <Route path="/creator" element={<CreatorMode />} />
                      <Route path="/project/:id" element={<ProjectView />} />
                      <Route path="/profile" element={<Profile />} />
                      <Route path="/upload" element={<BookUpload />} />
                      <Route path="/book/:id" element={<BookView />} />
                      <Route path="/subscription" element={<SubscriptionPage />} />
                      <Route path="/admin" element={<AdminDashboard />} />
                      <Route path="/reset-password" element={<ResetPasswordPage />} />
                      <Route path="/onboarding" element={<OnboardingPage />} />
                      <Route path="/auth/activate/:token" element={<ActivationPage />} />
                    </Routes>
                  </div>
                </Router>
              </LoadingProvider>
            </StoryboardProvider>
          </VideoGenerationProvider>
        </ScriptSelectionProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
