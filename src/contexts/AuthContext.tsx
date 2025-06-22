import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { apiClient } from "../lib/api";

interface User {
  id: string;
  email: string;
  username: string;
  // Add other user properties from your backend's User schema
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
    role: "author" | "explorer"
  ) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkUser = async () => {
      const token = localStorage.getItem("authToken");
      if (token) {
        try {
          const profile = await apiClient.get<User>("/users/me");
          setUser(profile);
        } catch (error) {
          console.error("Failed to fetch user profile", error);
          localStorage.removeItem("authToken");
        }
      }
      setLoading(false);
    };
    checkUser();
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await apiClient.post<{ access_token: string }>(
      "/auth/login",
      { email, password }
    );
    localStorage.setItem("authToken", access_token);
    const profile = await apiClient.get<User>("/users/me");
    setUser(profile);
  };

  const register = async (
    username: string,
    email: string,
    password: string,
    role: "author" | "explorer"
  ) => {
    await apiClient.post("/auth/register", {
      display_name: username,
      email,
      password,
      role,
    });
    // After successful registration, log the user in
    await login(email, password);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("authToken");
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
