import React, { createContext, useContext, useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { Toaster } from "react-hot-toast";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import AuthorPanel from "./pages/AuthorPanel";
import LearningMode from "./pages/LearningMode";
import EntertainmentMode from "./pages/EntertainmentMode";
import Profile from "./pages/Profile";
import BookUpload from "./pages/BookUpload";
import BookView from "./pages/BookView";

// Global Loading Context
const LoadingContext = createContext({
  setLoading: (v: boolean) => {},
  loading: false,
});
export const useLoading = () => useContext(LoadingContext);

function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(false);
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

function App() {
  return (
    <AuthProvider>
      <LoadingProvider>
        <Router>
          <Toaster position="top-center" reverseOrder={false} />
          <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50">
            <Navbar />
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/auth" element={<AuthPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/author" element={<AuthorPanel />} />
              <Route path="/learn" element={<LearningMode />} />
              <Route path="/explore" element={<EntertainmentMode />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/upload" element={<BookUpload />} />
              <Route path="/book/:id" element={<BookView />} />
            </Routes>
          </div>
        </Router>
      </LoadingProvider>
    </AuthProvider>
  );
}

export default App;
