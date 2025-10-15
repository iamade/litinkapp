import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { apiClient } from "../lib/api";
import { setOnTokenRefresh } from "../lib/api";

interface User {
  id: string;
  email: string;
  display_name: string;
  roles: ("author" | "explorer")[];
  role?: "author" | "explorer";
  preferred_mode?: "explorer" | "creator";
  onboarding_completed?: {
    explorer?: boolean;
    creator?: boolean;
  };
}

export const hasRole = (user: User | null, role: "author" | "explorer"): boolean => {
  if (!user) return false;
  return user.roles?.includes(role) ?? false;
};

export const hasAllRoles = (user: User | null, roles: ("author" | "explorer")[]): boolean => {
  if (!user) return false;
  return roles.every(role => user.roles?.includes(role));
};

export const hasAnyRole = (user: User | null, roles: ("author" | "explorer")[]): boolean => {
  if (!user) return false;
  return roles.some(role => user.roles?.includes(role));
};

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
    roles: ("author" | "explorer")[]
  ) => Promise<void>;
  logout: () => void;
  loading: boolean;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (
    email: string,
    token: string,
    newPassword: string
  ) => Promise<void>;
  resendVerificationEmail: (email: string) => Promise<void>;
  addRole: (role: "author" | "explorer") => Promise<void>;
  removeRole: (role: "author" | "explorer") => Promise<void>;
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
          localStorage.removeItem("authToken");
          localStorage.removeItem("refreshToken");
        }
      }
      setLoading(false);
    };
    checkUser();
    // Subscribe to token refreshes
    setOnTokenRefresh(async () => {
      try {
        const profile = await apiClient.get<User>("/users/me");
        setUser(profile);
      } catch {
        setUser(null);
        localStorage.removeItem("authToken");
        localStorage.removeItem("refreshToken");
      }
    });
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token, refresh_token } = await apiClient.post<{
      access_token: string;
      refresh_token: string;
    }>("/auth/login", { email, password });
    localStorage.setItem("authToken", access_token);
    localStorage.setItem("refreshToken", refresh_token);
    const profile = await apiClient.get<User>("/users/me");
    setUser(profile);
  };

  const register = async (
    username: string,
    email: string,
    password: string,
    roles: ("author" | "explorer")[]
  ) => {
    await apiClient.post("/auth/register", {
      display_name: username,
      email,
      password,
      roles,
    });
    await login(email, password);
  };

  const addRole = async (role: "author" | "explorer") => {
    await apiClient.post("/users/me/roles", { role });
    const profile = await apiClient.get<User>("/users/me");
    setUser(profile);
  };

  const removeRole = async (role: "author" | "explorer") => {
    await apiClient.delete(`/users/me/roles/${role}`);
    const profile = await apiClient.get<User>("/users/me");
    setUser(profile);
  };

  const requestPasswordReset = async (email: string) => {
    await apiClient.post("/auth/request-password-reset", { email });
  };

  const confirmPasswordReset = async (
    email: string,
    token: string,
    newPassword: string
  ) => {
    await apiClient.post("/auth/confirm-password-reset", {
      email,
      token,
      new_password: newPassword,
    });
  };

  const resendVerificationEmail = async (email: string) => {
    await apiClient.post("/auth/resend-verification", { email });
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("authToken");
    localStorage.removeItem("refreshToken");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        register,
        logout,
        loading,
        requestPasswordReset,
        confirmPasswordReset,
        resendVerificationEmail,
        addRole,
        removeRole,
      }}
    >
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
