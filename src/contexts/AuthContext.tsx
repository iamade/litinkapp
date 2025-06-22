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
    // Check for existing session
    const savedUser = localStorage.getItem('litink_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      // Call FastAPI backend for authentication
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error('Authentication failed');
      }

      const data = await response.json();
      
      // Get user info
      const userResponse = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.access_token}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error('Failed to get user info');
      }

      const userData = await userResponse.json();
      
      const mockUser: User = {
        id: userData.id,
        email: userData.email,
        role: userData.role,
        displayName: userData.display_name || userData.email.split('@')[0]
      };

      setUser(mockUser);
      localStorage.setItem('litink_user', JSON.stringify(mockUser));
      localStorage.setItem('litink_token', data.access_token);
    } catch (error) {
      // Fallback to demo mode for development
      console.warn('Backend auth failed, using demo mode:', error);
      const isAuthor = email.toLowerCase().includes('author');
      const mockUser: User = {
        id: '1',
        email,
        role: isAuthor ? 'author' : 'explorer',
        displayName: email.split('@')[0]
      };
      setUser(mockUser);
      localStorage.setItem('litink_user', JSON.stringify(mockUser));
    }
  };

  const signUp = async (email: string, password: string, role: 'author' | 'explorer') => {
    try {
      // Call FastAPI backend for registration
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, role }),
      });

      if (!response.ok) {
        throw new Error('Registration failed');
      }

      const userData = await response.json();
      
      const mockUser: User = {
        id: userData.id,
        email: userData.email,
        role: userData.role,
        displayName: userData.display_name || userData.email.split('@')[0]
      };

      setUser(mockUser);
      localStorage.setItem('litink_user', JSON.stringify(mockUser));
    } catch (error) {
      // Fallback to demo mode for development
      console.warn('Backend registration failed, using demo mode:', error);
      const mockUser: User = {
        id: '1',
        email,
        role,
        displayName: email.split('@')[0]
      };
      setUser(mockUser);
      localStorage.setItem('litink_user', JSON.stringify(mockUser));
    }
  };

  const signOut = () => {
    setUser(null);
    localStorage.removeItem('litink_user');
    localStorage.removeItem('litink_token');
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