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
  roles: ("author" | "explorer" | "creator" | "superadmin")[];
  role?: "author" | "explorer" | "creator" | "superadmin";
  preferred_mode?: "explorer" | "creator";
  onboarding_completed?: {
    explorer?: boolean;
    creator?: boolean;
  };
}

export const hasRole = (user: User | null, role: "author" | "explorer" | "creator" | "superadmin"): boolean => {
  if (!user) return false;
  return user.roles?.includes(role) ?? false;
};

export const hasAllRoles = (user: User | null, roles: ("author" | "explorer" | "creator" | "superadmin")[]): boolean => {
  if (!user) return false;
  return roles.every(role => user.roles?.includes(role));
};

export const hasAnyRole = (user: User | null, roles: ("author" | "explorer" | "creator" | "superadmin")[]): boolean => {
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
      try {
        // Just try to get the user. If cookies are valid, it will succeed.
        const profile = await apiClient.get<User>("/users/me");
        setUser(profile);
      } catch (error) {
        // If 401, we are not logged in. That's fine.
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkUser();
    
    // Subscribe to token refreshes (optional now, but good for state sync)
    setOnTokenRefresh(async () => {
      try {
        const profile = await apiClient.get<User>("/users/me");
        setUser(profile);
      } catch {
        setUser(null);
      }
    });
  }, []);

  const login = async (email: string, password: string) => {
    await apiClient.post("/auth/login", { email, password });
    // After login, cookies are set. Fetch user profile.
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
    // await login(email, password);
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

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout", {});
    } catch (e) {
      // Ignore error on logout
    }
    setUser(null);
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
