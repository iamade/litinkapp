import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import AuthorPanel from './pages/AuthorPanel';
import LearningMode from './pages/LearningMode';
import EntertainmentMode from './pages/EntertainmentMode';
import Profile from './pages/Profile';
import BookUpload from './pages/BookUpload';
import BookView from './pages/BookView';

function App() {
  return (
    <AuthProvider>
      <Router>
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
    </AuthProvider>
  );
}

export default App;