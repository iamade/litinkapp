import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  role: 'author' | 'explorer';
  displayName?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, role: 'author' | 'explorer') => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate auth check
    const savedUser = localStorage.getItem('litink_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const signIn = async (email: string, password: string) => {
    // Simulate sign in - replace with actual Supabase auth
    // For demo purposes, make users authors if email contains "author"
    const isAuthor = email.toLowerCase().includes('author');
    const mockUser: User = {
      id: '1',
      email,
      role: isAuthor ? 'author' : 'explorer',
      displayName: email.split('@')[0]
    };
    setUser(mockUser);
    localStorage.setItem('litink_user', JSON.stringify(mockUser));
  };

  const signUp = async (email: string, password: string, role: 'author' | 'explorer') => {
    // Simulate sign up - replace with actual Supabase auth
    const mockUser: User = {
      id: '1',
      email,
      role,
      displayName: email.split('@')[0]
    };
    setUser(mockUser);
    localStorage.setItem('litink_user', JSON.stringify(mockUser));
  };

  const signOut = () => {
    setUser(null);
    localStorage.removeItem('litink_user');
  };

  const value = {
    user,
    loading,
    signIn,
    signUp,
    signOut
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}