export const API_BASE_URL = import.meta.env.PROD 
  ? "https://litinkapp.onrender.com/api/v1"
  : "http://localhost:8000/api/v1";

// Helper to notify listeners (still useful for UI updates, though token is in cookie)
let onTokenRefresh: ((token: string) => void) | null = null;
export function setOnTokenRefresh(cb: (token: string) => void) {
  onTokenRefresh = cb;
}

async function refreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Send cookies
    });

    if (!response.ok) {
      return false;
    }

    // Cookies are automatically updated by the response
    return true;
  } catch (error) {
    return false;
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

  async patch<T>(endpoint: string, body: unknown): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "PATCH", body));
  },

  async delete<T>(endpoint: string, body?: unknown): Promise<T> {
    return withLoading(() => this.request<T>(endpoint, "DELETE", body));
  },

  async postStream(endpoint: string, body: unknown): Promise<Response> {
    return withLoading(async () => {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      
      let response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        credentials: "include",
      });

      if (response.status === 401) {
        const refreshed = await refreshToken();
        if (refreshed) {
          response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers,
            body: JSON.stringify(body),
            credentials: "include",
          });
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = (errorData as { detail?: string | { message?: string } }).detail;
        let errorMessage = "An API error occurred";
        if (typeof detail === "string") {
          errorMessage = detail;
        } else if (detail && typeof detail === "object" && "message" in detail) {
          errorMessage = detail.message || errorMessage;
        }
        throw new Error(`[${response.status}] ${errorMessage}`);
      }
      
      return response;
    });
  },

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    return withLoading(async () => {
      let response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {}, // do not set Content-Type for FormData
        body: formData,
        credentials: "include",
      });

      if (response.status === 401) {
        // Try refresh
        const refreshed = await refreshToken();
        if (refreshed) {
          response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: {},
            body: formData,
            credentials: "include",
          });
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = (errorData as { detail?: string | { message?: string } }).detail;
        let errorMessage = "An API error occurred";
        if (typeof detail === "string") {
          errorMessage = detail;
        } else if (detail && typeof detail === "object" && "message" in detail) {
          errorMessage = detail.message || errorMessage;
        }
        throw new Error(`[${response.status}] ${errorMessage}`);
      }
      return response.json();
    });
  },


  async request<T>(
    endpoint: string,
    method: string,
    body?: unknown
  ): Promise<T> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    let response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
      credentials: "include",
    });


    // Skip token refresh retry for public endpoints (auth, activation)
    const isPublicEndpoint = endpoint.startsWith('/auth/');
    
    if (response.status === 401 && !isPublicEndpoint) {
      // Try refresh
      const refreshed = await refreshToken();
      if (refreshed) {
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method,
          headers,
          body: body ? JSON.stringify(body) : null,
          credentials: "include",
        });
      }
    }


    if (!response.ok) {
      let errorData: unknown = {};
      try {
        errorData = await response.json();
      } catch {
        // ignore
      }
      
      // Handle FastAPI 422 validation errors (array format)
      if (response.status === 422 && Array.isArray((errorData as any).detail)) {
        const validationErrors = (errorData as any).detail;
        const errorMessages = validationErrors.map((err: any) => {
          if (err.msg && err.loc) {
            const field = err.loc[err.loc.length - 1]; // Get the field name
            return `${field}: ${err.msg}`;
          }
          return err.msg || 'Validation error';
        });
        throw new Error(errorMessages.join(', '));
      }
      
      // Handle both string detail and object detail (with message property)
      const detail = (errorData as { detail?: string | { message?: string } }).detail;
      let errorMessage = "An API error occurred";
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (detail && typeof detail === "object" && "message" in detail) {
        errorMessage = detail.message || errorMessage;
      }
      // Include status code in error message for proper 404 detection
      throw new Error(`[${response.status}] ${errorMessage}`);
    }

    if (response.status === 204) {
      return true as T;
    }

    return response.json();
  },
};

export async function generateScriptAudio(chapterId: string | null, scriptId: string, sceneNumbers?: number[]) {
  return apiClient.post<{ 
    status: string; 
    video_generation_id: string; 
    task_id: string 
  }>("/ai/generate-audio-for-script", {
    chapter_id: chapterId,
    script_id: scriptId,
    scene_numbers: sceneNumbers
  });
}

export async function deleteAudio(chapterId: string, audioId: string) {
  return apiClient.delete<{ 
    success: boolean; 
    message: string;
    audio_id: string;
  }>(`/chapters/${chapterId}/audio/${audioId}`);
}