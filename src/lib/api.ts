const API_BASE_URL = "http://localhost:8000/api/v1";

const getAuthToken = (): string | null => {
  return localStorage.getItem("authToken");
};

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, "GET");
  },

  async post<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, "POST", body);
  },

  async put<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, "PUT", body);
  },

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, "DELETE");
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

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "An API error occurred");
    }

    return response.json();
  },
};
