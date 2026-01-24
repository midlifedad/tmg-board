/**
 * API Client for TMG Board Backend
 *
 * Handles all API requests with authentication headers.
 * Follows themany-forecasting pattern: X-User-Email header for user identification.
 */

// Use /api/proxy to go through Next.js proxy route (avoids CORS issues)
const API_BASE_URL = "/api/proxy";

interface RequestOptions extends RequestInit {
  userEmail?: string;
}

class ApiClient {
  private baseUrl: string;
  private userEmail: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setUserEmail(email: string | null) {
    this.userEmail = email;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { userEmail, ...fetchOptions } = options;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    // Add user email header if available
    const email = userEmail || this.userEmail;
    if (email) {
      (headers as Record<string, string>)["X-User-Email"] = email;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.message || `API error: ${response.statusText}`
      );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    return JSON.parse(text);
  }

  // GET request
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  // POST request
  async post<T>(
    endpoint: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T>(
    endpoint: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// Singleton instance
export const api = new ApiClient(API_BASE_URL);

// Set default user email for API authentication (dev/staging without real auth)
// Can be overridden by NEXT_PUBLIC_DEFAULT_USER_EMAIL env var
const defaultEmail = process.env.NEXT_PUBLIC_DEFAULT_USER_EMAIL ||
  (process.env.NODE_ENV === "development" ? "test@example.com" : null);

if (typeof window !== "undefined" && defaultEmail) {
  api.setUserEmail(defaultEmail);
}

// =============================================================================
// Auth API
// =============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: "member" | "chair" | "admin";
  google_id?: string;
  created_at: string;
}

export const authApi = {
  /**
   * Verify Google token with backend
   */
  verifyGoogleToken: async (token: string): Promise<{ user: User }> => {
    return api.post("/auth/google", { token });
  },

  /**
   * Get user details by email
   */
  getUserByEmail: async (email: string): Promise<User> => {
    return api.get(`/auth/user/${encodeURIComponent(email)}`);
  },

  /**
   * Get current authenticated user
   */
  getCurrentUser: async (): Promise<User> => {
    return api.get("/auth/me");
  },

  /**
   * Logout
   */
  logout: async (): Promise<void> => {
    return api.post("/auth/logout");
  },
};

// =============================================================================
// Paginated response helper
// =============================================================================

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// =============================================================================
// Documents API
// =============================================================================

export interface Document {
  id: number;
  title: string;
  type: "resolution" | "minutes" | "consent" | "financial" | "legal";
  file_path: string;
  uploaded_by_id: number;
  docusign_envelope_id?: string | null;
  signing_status?: "pending" | "sent" | "completed" | "declined" | null;
  created_at: string;
  updated_at: string;
}

export const documentsApi = {
  /**
   * List all documents with optional filters
   */
  list: async (params?: {
    type?: string;
    year?: number;
    status?: string;
  }): Promise<Document[]> => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set("type", params.type);
    if (params?.year) searchParams.set("year", params.year.toString());
    if (params?.status) searchParams.set("status", params.status);

    const query = searchParams.toString();
    const response = await api.get<PaginatedResponse<Document>>(`/documents/${query ? `?${query}` : ""}`);
    return response.items || [];
  },

  /**
   * Get document by ID
   */
  get: async (id: string): Promise<Document> => {
    return api.get(`/documents/${id}/`);
  },

  /**
   * Upload a new document
   */
  create: async (data: {
    title: string;
    type: Document["type"];
    file: File;
  }): Promise<Document> => {
    // TODO: Implement presigned URL upload flow
    return api.post("/documents", data);
  },

  /**
   * Send document for signature via DocuSign
   */
  sendForSignature: async (id: string): Promise<{ envelope_id: string }> => {
    return api.post(`/documents/${id}/sign`);
  },

  /**
   * Get signing status
   */
  getSigningStatus: async (
    id: string
  ): Promise<{
    status: string;
    signers: Array<{ email: string; name: string; signed_at?: string }>;
  }> => {
    return api.get(`/documents/${id}/status`);
  },
};

// =============================================================================
// Meetings API
// =============================================================================

export interface Meeting {
  id: number;
  title: string;
  scheduled_date: string;
  location: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  meeting_link?: string | null;
  description?: string | null;
  created_by_id: number;
  created_at: string;
}

export interface AgendaItem {
  id: string;
  meeting_id: string;
  title: string;
  description?: string;
  order: number;
  presenter_id?: string;
  decision_id?: string;
}

export const meetingsApi = {
  /**
   * List all meetings
   */
  list: async (): Promise<Meeting[]> => {
    const response = await api.get<PaginatedResponse<Meeting>>("/meetings/");
    return response.items || [];
  },

  /**
   * Get meeting by ID
   */
  get: async (id: string): Promise<Meeting> => {
    return api.get(`/meetings/${id}/`);
  },

  /**
   * Create a new meeting
   */
  create: async (data: {
    title: string;
    date: string;
    location: string;
  }): Promise<Meeting> => {
    return api.post("/meetings/", data);
  },

  /**
   * Get meeting agenda
   */
  getAgenda: async (meetingId: string): Promise<AgendaItem[]> => {
    const response = await api.get<PaginatedResponse<AgendaItem>>(`/meetings/${meetingId}/agenda/`);
    return response.items || [];
  },

  /**
   * Add agenda item
   */
  addAgendaItem: async (
    meetingId: string,
    data: { title: string; description?: string; presenter_id?: string }
  ): Promise<AgendaItem> => {
    return api.post(`/meetings/${meetingId}/agenda/`, data);
  },
};

// =============================================================================
// Decisions API
// =============================================================================

export interface Decision {
  id: number;
  title: string;
  description?: string | null;
  type: "vote" | "consent" | "resolution";
  status: "pending" | "open" | "closed";
  meeting_id?: number | null;
  deadline?: string | null;
  created_by_id: number;
  created_at: string;
}

export interface Vote {
  id: number;
  decision_id: number;
  member_id: number;
  vote: "yes" | "no" | "abstain";
  cast_at: string;
}

export interface DecisionDetail {
  decision: Decision;
  user_vote: string | null;
  results: {
    yes: number;
    no: number;
    abstain: number;
    pending: number;
  };
}

export const decisionsApi = {
  /**
   * List all decisions
   */
  list: async (params?: { status?: string }): Promise<Decision[]> => {
    const query = params?.status ? `?status=${params.status}` : "";
    const response = await api.get<PaginatedResponse<Decision>>(`/decisions/${query}`);
    return response.items || [];
  },

  /**
   * Get decision by ID (returns decision with votes and results)
   */
  get: async (id: string): Promise<DecisionDetail> => {
    return api.get(`/decisions/${id}/`);
  },

  /**
   * Cast a vote
   */
  castVote: async (
    decisionId: string,
    vote: "yes" | "no" | "abstain"
  ): Promise<Vote> => {
    return api.post(`/decisions/${decisionId}/vote/`, { vote });
  },

  /**
   * Get voting results
   */
  getResults: async (
    decisionId: string
  ): Promise<{
    yes: number;
    no: number;
    abstain: number;
    pending: number;
    votes: Vote[];
  }> => {
    return api.get(`/decisions/${decisionId}/results/`);
  },
};

// =============================================================================
// Ideas API
// =============================================================================

export interface Idea {
  id: number;
  title: string;
  description?: string | null;
  submitted_by_id: number;
  status: "new" | "under_review" | "approved" | "rejected" | "promoted";
  created_at: string;
}

export interface Comment {
  id: number;
  idea_id: number;
  user_id: number;
  user_name?: string;
  content: string;
  created_at: string;
}

export const ideasApi = {
  /**
   * List all ideas
   */
  list: async (params?: { status?: string }): Promise<Idea[]> => {
    const query = params?.status ? `?status=${params.status}` : "";
    const response = await api.get<PaginatedResponse<Idea>>(`/ideas/${query}`);
    return response.items || [];
  },

  /**
   * Get idea by ID
   */
  get: async (id: string): Promise<Idea> => {
    return api.get(`/ideas/${id}/`);
  },

  /**
   * Submit a new idea
   */
  create: async (data: {
    title: string;
    description?: string;
  }): Promise<Idea> => {
    return api.post("/ideas/", data);
  },

  /**
   * Add comment to idea
   */
  addComment: async (ideaId: string, content: string): Promise<Comment> => {
    return api.post(`/ideas/${ideaId}/comments/`, { content });
  },

  /**
   * Get comments for idea
   */
  getComments: async (ideaId: string): Promise<Comment[]> => {
    const response = await api.get<PaginatedResponse<Comment>>(`/ideas/${ideaId}/comments/`);
    return response.items || [];
  },

  /**
   * Promote idea to decision (chair/admin only)
   */
  promote: async (ideaId: string): Promise<Decision> => {
    return api.post(`/ideas/${ideaId}/promote/`);
  },
};
