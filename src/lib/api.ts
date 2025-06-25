const API_BASE_URL = "http://localhost:8000/api/v1";

const getAuthToken = (): string | null => {
  return localStorage.getItem("authToken");
};

const getRefreshToken = (): string | null => {
  return localStorage.getItem("refreshToken");
};

// Helper to update token in localStorage and notify listeners
let onTokenRefresh: ((token: string) => void) | null = null;
export function setOnTokenRefresh(cb: (token: string) => void) {
  onTokenRefresh = cb;
}

async function refreshToken(): Promise<string | null> {
  const storedRefreshToken = getRefreshToken();
  if (!storedRefreshToken) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: storedRefreshToken }),
    });

    if (!response.ok) {
      // If refresh fails, log the user out by clearing tokens
      localStorage.removeItem("authToken");
      localStorage.removeItem("refreshToken");
      return null;
    }

    const data = await response.json();
    if (data.access_token && data.refresh_token) {
      localStorage.setItem("authToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);
      if (onTokenRefresh) onTokenRefresh(data.access_token);
      return data.access_token;
    }
    return null;
  } catch (error) {
    console.error("Error refreshing token:", error);
    return null;
  }
}

let setLoading: ((v: boolean) => void) | null = null;
export function setLoadingContextSetter(setter: (v: boolean) => void) {
  setLoading = setter;
}

async function withLoading<T>(fn: () => Promise<T>): Promise<T> {
  if (setLoading) setLoading(true);
  try {
    return await fn();
  } finally {
    if (setLoading) setLoading(false);
  }
}

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "GET"));
  },

  async post<T>(endpoint: string, body: unknown): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "POST", body));
  },

  async put<T>(endpoint: string, body: unknown): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "PUT", body));
  },

  async delete<T>(endpoint: string): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "DELETE"));
  },

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    return withLoading(async () => {
      const token = getAuthToken();
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      let response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers, // do not set Content-Type for FormData
        body: formData,
      });
      if (response.status === 401) {
        // Try refresh
        const newToken = await refreshToken();
        if (newToken) {
          headers["Authorization"] = `Bearer ${newToken}`;
          response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers,
            body: formData,
          });
        }
      }
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "An API error occurred");
      }
      return response.json();
    });
  },

  async request<T>(
    endpoint: string,
    method: string,
    body?: unknown
  ): Promise<T> {
    const token = getAuthToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    let response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    if (response.status === 401) {
      // Try refresh
      const newToken = await refreshToken();
      if (newToken) {
        const retryHeaders: HeadersInit = {
          "Content-Type": "application/json",
          Authorization: `Bearer ${newToken}`,
        };
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method,
          headers: retryHeaders,
          body: body ? JSON.stringify(body) : null,
        });
      }
    }

    if (!response.ok) {
      // Try to parse error JSON, but if 204, just throw a generic error
      let errorData: unknown = {};
      try {
        errorData = await response.json();
      } catch {
        // ignore
      }
      throw new Error(
        (errorData as { detail?: string }).detail || "An API error occurred"
      );
    }

    // If 204 No Content, return true (or empty object)
    if (response.status === 204) {
      return true as T;
    }

    return response.json();
  },
};
