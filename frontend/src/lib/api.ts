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

  // PATCH request
  async patch<T>(
    endpoint: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
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

// User email is set per-page from the session via api.setUserEmail(session.user.email)
// No default — auth is handled by Google OAuth + backend verification

// =============================================================================
// Branding API (public, no auth required)
// =============================================================================

export interface BrandingSettings {
  app_name: string;
  organization_name: string;
  organization_logo_url?: string | null;
}

export const brandingApi = {
  getBranding: async (): Promise<BrandingSettings> => {
    return api.get("/admin/branding");
  },
};

// =============================================================================
// Auth API
// =============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "chair" | "board" | "shareholder";
  google_id?: string;
  timezone?: string | null;
  effective_timezone?: string;
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
   * Update current user's timezone
   */
  updateTimezone: async (timezone: string): Promise<void> => {
    return api.patch("/auth/me/timezone", { timezone });
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
  type: "resolution" | "minutes" | "consent" | "financial" | "legal" | "whitepaper" | "strategy" | "audit";
  file_path: string;
  uploaded_by_id: number;
  docusign_envelope_id?: string | null;
  signing_status?: "pending" | "sent" | "completed" | "declined" | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: number;
  document_id: number;
  version_number: number;
  file_path: string;
  uploaded_by_id: number;
  uploaded_by_name?: string;
  upload_reason?: string | null;
  created_at: string;
}

export const documentsApi = {
  /**
   * List all documents with optional filters
   */
  list: async (params?: {
    type?: string;
    year?: number;
    status?: string;
    archived?: boolean;
  }): Promise<Document[]> => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set("type", params.type);
    if (params?.year) searchParams.set("year", params.year.toString());
    if (params?.status) searchParams.set("status", params.status);
    if (params?.archived !== undefined) searchParams.set("archived", String(params.archived));

    const query = searchParams.toString();
    const response = await api.get<PaginatedResponse<Document>>(`/documents/${query ? `?${query}` : ""}`);
    return response.items || [];
  },

  /**
   * Get document by ID
   */
  get: async (id: string): Promise<Document> => {
    return api.get(`/documents/${id}`);
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
   * Update document metadata
   */
  update: async (id: string, data: {
    title?: string;
    type?: string;
    description?: string;
    category?: string;
    tags?: string[];
  }): Promise<Document> => {
    return api.patch(`/documents/${id}`, data);
  },

  /**
   * Send document for signature via DocuSign
   */
  sendForSignature: async (id: string): Promise<{ envelope_id: string }> => {
    return api.post(`/documents/${id}/send-for-signature`);
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
    return api.get(`/documents/${id}/signing-status`);
  },

  /**
   * Get document version history
   */
  getVersions: async (id: string): Promise<DocumentVersion[]> => {
    const response = await api.get<DocumentVersion[] | PaginatedResponse<DocumentVersion>>(`/documents/${id}/versions`);
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Upload a new version
   */
  uploadVersion: async (id: string, file: File, reason?: string): Promise<DocumentVersion> => {
    const formData = new FormData();
    formData.append("file", file);
    if (reason) formData.append("reason", reason);

    const response = await fetch(`/api/proxy/documents/${id}/versions`, {
      method: "POST",
      headers: {
        "X-User-Email": api["userEmail"] || "",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.message || "Failed to upload version");
    }

    return response.json();
  },

  /**
   * Fetch the HTML content of a document for inline rendering.
   * Returns a blob URL that can be used as an iframe src.
   */
  fetchHtmlContent: async (id: string): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}/render`, {
      headers: {
        "X-User-Email": api["userEmail"] || "",
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, "Failed to load HTML document");
    }

    const html = await response.text();
    const blob = new Blob([html], { type: "text/html" });
    return URL.createObjectURL(blob);
  },

  /**
   * Check if a document is an HTML file based on its file_path
   */
  isHtmlDocument: (doc: Document): boolean => {
    return doc.file_path?.endsWith('.html') || false;
  },

  /**
   * Archive document
   */
  archive: async (id: string): Promise<void> => {
    return api.post(`/documents/${id}/archive`);
  },

  /**
   * Unarchive document
   */
  unarchive: async (id: string): Promise<void> => {
    return api.post(`/documents/${id}/unarchive`);
  },

  /**
   * Get document activity log
   */
  getActivity: async (id: string): Promise<Array<{
    id: number;
    action: string;
    user_name: string;
    created_at: string;
    details?: string;
  }>> => {
    const response = await api.get<PaginatedResponse<{
      id: number;
      action: string;
      user_name: string;
      created_at: string;
      details?: string;
    }>>(`/documents/${id}/activity`);
    return response.items || [];
  },
};

// =============================================================================
// Meetings API
// =============================================================================

export interface Meeting {
  id: number;
  title: string;
  scheduled_date: string;
  duration_minutes?: number | null;
  location: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  meeting_link?: string | null;
  description?: string | null;
  created_by_id: number;
  created_at: string;
  agenda_items_count?: number;
  has_minutes?: boolean;
  decisions_count?: number;
}

export interface Transcript {
  id: number;
  meeting_id: number;
  content: string;
  source: "paste" | "upload";
  original_filename?: string | null;
  char_count: number;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface AgendaItem {
  id: number;
  meeting_id: number;
  title: string;
  description?: string | null;
  item_type?: "information" | "discussion" | "decision_required" | "consent_agenda";
  duration_minutes: number;
  order_index: number;
  presenter_id?: number | null;
  presenter?: string | null;
  status: "pending" | "in_progress" | "completed" | "skipped";
  decision_id?: number | null;
  created_at?: string | null;
}

export interface MemberOption {
  id: number;
  name: string;
}

export const meetingsApi = {
  /**
   * List active board members (for presenter dropdowns)
   */
  listMembers: async (): Promise<MemberOption[]> => {
    return api.get<MemberOption[]>("/meetings/members");
  },

  /**
   * List all meetings
   */
  list: async (): Promise<Meeting[]> => {
    const response = await api.get<PaginatedResponse<Meeting>>("/meetings");
    return response.items || [];
  },

  /**
   * Get meeting by ID
   */
  get: async (id: string): Promise<Meeting> => {
    return api.get(`/meetings/${id}`);
  },

  /**
   * Create a new meeting
   */
  create: async (data: {
    title: string;
    scheduled_date: string;
    duration_minutes?: number;
    location: string;
    description?: string;
    meeting_link?: string;
  }): Promise<Meeting> => {
    return api.post("/meetings", data);
  },

  /**
   * Get meeting agenda
   */
  getAgenda: async (meetingId: string): Promise<AgendaItem[]> => {
    return api.get<AgendaItem[]>(`/meetings/${meetingId}/agenda`);
  },

  /**
   * Update meeting
   */
  update: async (id: string, data: {
    title?: string;
    scheduled_date?: string;
    duration_minutes?: number;
    location?: string;
    description?: string;
    meeting_link?: string;
  }): Promise<Meeting> => {
    return api.patch(`/meetings/${id}`, data);
  },

  /**
   * Cancel meeting (backend uses DELETE to set status to cancelled)
   */
  cancel: async (id: string): Promise<void> => {
    return api.delete(`/meetings/${id}`);
  },

  /**
   * Start meeting
   */
  start: async (id: string): Promise<Meeting> => {
    return api.post(`/meetings/${id}/start`);
  },

  /**
   * End meeting
   */
  end: async (id: string): Promise<Meeting> => {
    return api.post(`/meetings/${id}/end`);
  },

  /**
   * Add agenda item
   */
  addAgendaItem: async (
    meetingId: string,
    data: {
      title: string;
      description?: string;
      item_type?: "information" | "discussion" | "decision_required" | "consent_agenda";
      duration_minutes?: number;
      presenter_id?: number;
    }
  ): Promise<AgendaItem> => {
    return api.post(`/meetings/${meetingId}/agenda`, data);
  },

  /**
   * Update agenda item
   */
  updateAgendaItem: async (
    meetingId: string,
    itemId: number,
    data: {
      title?: string;
      description?: string;
      item_type?: "information" | "discussion" | "decision_required" | "consent_agenda";
      duration_minutes?: number;
      presenter_id?: number;
    }
  ): Promise<AgendaItem> => {
    return api.patch(`/meetings/${meetingId}/agenda/${itemId}`, data);
  },

  /**
   * Delete agenda item
   */
  deleteAgendaItem: async (meetingId: string, itemId: number): Promise<void> => {
    return api.delete(`/meetings/${meetingId}/agenda/${itemId}`);
  },

  /**
   * Reorder agenda items
   */
  reorderAgendaItems: async (
    meetingId: string,
    items: Array<{ id: number; order_index: number }>
  ): Promise<void> => {
    return api.patch(`/meetings/${meetingId}/agenda/reorder`, { item_ids: items.map(i => i.id) });
  },

  /**
   * Get attendance
   */
  getAttendance: async (meetingId: string): Promise<Array<{
    meeting_id: number;
    member_id: number;
    member_name: string;
    status: "present" | "absent" | "excused";
    joined_at?: string;
    left_at?: string;
  }>> => {
    const response = await api.get<
      Array<{ meeting_id: number; member_id: number; member_name: string; status: "present" | "absent" | "excused"; joined_at?: string; left_at?: string }>
      | PaginatedResponse<{ meeting_id: number; member_id: number; member_name: string; status: "present" | "absent" | "excused"; joined_at?: string; left_at?: string }>
    >(`/meetings/${meetingId}/attendance`);
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Update attendance
   */
  updateAttendance: async (
    meetingId: string,
    userId: number,
    status: "present" | "absent" | "excused"
  ): Promise<void> => {
    return api.patch(`/meetings/${meetingId}/attendance/${userId}`, { status });
  },

  /**
   * Get transcript for a meeting
   */
  getTranscript: async (meetingId: string): Promise<Transcript | null> => {
    try {
      return await api.get<Transcript>(`/meetings/${meetingId}/transcript`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },

  /**
   * Add transcript via paste
   */
  addTranscript: async (meetingId: string, content: string): Promise<Transcript> => {
    return api.post(`/meetings/${meetingId}/transcript`, { content });
  },

  /**
   * Upload a .txt transcript file
   */
  uploadTranscript: async (meetingId: string, file: File): Promise<Transcript> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`/api/proxy/meetings/${meetingId}/transcript/upload`, {
      method: "POST",
      headers: {
        "X-User-Email": api["userEmail"] || "",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.detail || "Failed to upload transcript");
    }

    return response.json();
  },

  /**
   * Replace existing transcript
   */
  replaceTranscript: async (meetingId: string, content: string): Promise<Transcript> => {
    return api.put(`/meetings/${meetingId}/transcript`, { content });
  },

  /**
   * Delete transcript
   */
  deleteTranscript: async (meetingId: string): Promise<void> => {
    return api.delete(`/meetings/${meetingId}/transcript`);
  },

  /**
   * Get minutes for a meeting (returns null if none exist)
   */
  getMinutes: async (meetingId: string): Promise<{ document_id: number; html_content: string; title: string; created_at: string | null; updated_at: string | null } | null> => {
    try {
      return await api.get(`/meetings/${meetingId}/minutes`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },

  /**
   * Create meeting with agenda items in one call
   */
  createWithAgenda: async (data: {
    title: string;
    date: string;
    duration_minutes?: number;
    location?: string;
    meeting_link?: string;
    description?: string;
    template_id?: number;
    agenda_items?: Array<{
      title: string;
      description?: string;
      item_type?: string;
      duration_minutes?: number;
    }>;
  }): Promise<Meeting> => {
    return api.post("/meetings/with-agenda", data);
  },
};

// =============================================================================
// Templates API
// =============================================================================

export interface MeetingTemplate {
  id: number;
  name: string;
  description?: string | null;
  default_duration_minutes?: number | null;
  default_location?: string | null;
  items_count: number;
  has_regulatory_items: boolean;
  created_at: string;
}

export interface TemplateDetail extends MeetingTemplate {
  items: TemplateItem[];
}

export interface TemplateItem {
  id: number;
  title: string;
  description?: string | null;
  item_type: string;
  duration_minutes?: number | null;
  order_index: number;
  is_regulatory: boolean;
}

export const templatesApi = {
  list: async (): Promise<MeetingTemplate[]> => {
    return api.get<MeetingTemplate[]>("/templates");
  },
  get: async (id: number): Promise<TemplateDetail> => {
    return api.get<TemplateDetail>(`/templates/${id}`);
  },
  create: async (data: {
    name: string;
    description?: string;
    default_duration_minutes?: number;
    default_location?: string;
    items: Array<{
      title: string;
      description?: string;
      item_type?: string;
      duration_minutes?: number;
      order_index: number;
      is_regulatory?: boolean;
    }>;
  }): Promise<TemplateDetail> => {
    return api.post("/templates", data);
  },
  update: async (
    id: number,
    data: {
      name?: string;
      description?: string;
      default_duration_minutes?: number;
      default_location?: string;
      items?: Array<{
        title: string;
        description?: string;
        item_type?: string;
        duration_minutes?: number;
        order_index: number;
        is_regulatory?: boolean;
      }>;
    }
  ): Promise<TemplateDetail> => {
    return api.patch(`/templates/${id}`, data);
  },
  delete: async (id: number): Promise<void> => {
    return api.delete(`/templates/${id}`);
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
    return api.get(`/decisions/${id}`);
  },

  /**
   * Cast a vote
   */
  castVote: async (
    decisionId: string,
    vote: "yes" | "no" | "abstain"
  ): Promise<Vote> => {
    return api.post(`/decisions/${decisionId}/vote`, { vote });
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
    return api.get(`/decisions/${decisionId}/results`);
  },

  /**
   * Create a new decision
   */
  create: async (data: {
    title: string;
    description?: string | null;
    type: "vote" | "consent" | "resolution";
    deadline?: string | null;
    meeting_id?: number | null;
    visibility?: "standard" | "anonymous" | "transparent";
  }): Promise<Decision> => {
    return api.post("/decisions", data);
  },

  /**
   * Extend deadline
   */
  extendDeadline: async (id: string, newDeadline: string): Promise<Decision> => {
    return api.post(`/decisions/${id}/extend`, { new_deadline: newDeadline });
  },

  /**
   * Send reminders to pending voters
   */
  sendReminders: async (id: string): Promise<{ sent_count: number }> => {
    return api.post(`/decisions/${id}/remind`);
  },

  /**
   * Update a decision
   */
  update: async (id: string, data: {
    title?: string;
    description?: string | null;
    type?: "vote" | "consent" | "resolution";
    deadline?: string | null;
  }): Promise<Decision> => {
    return api.patch(`/decisions/${id}`, data);
  },

  /**
   * Open voting on a decision
   */
  open: async (id: string): Promise<Decision> => {
    return api.post(`/decisions/${id}/open`);
  },

  /**
   * Close voting on a decision
   */
  close: async (id: string): Promise<Decision> => {
    return api.post(`/decisions/${id}/close`);
  },

  /**
   * Reopen voting on a decision
   */
  reopen: async (id: string): Promise<Decision> => {
    return api.post(`/decisions/${id}/reopen`);
  },

  /**
   * Archive a decision
   */
  archive: async (id: string, reason?: string): Promise<void> => {
    return api.post(`/decisions/${id}/archive`, { reason: reason || null });
  },
};

// =============================================================================
// Resolutions API
// =============================================================================

export interface ResolutionSignature {
  member_id: number;
  member_name: string;
  signed_at: string | null;
  ip_address: string | null;
}

export interface SignatureStatus {
  resolution_id: number;
  signatures: ResolutionSignature[];
  signed_count: number;
  total_members: number;
}

export interface ResolutionListItem extends Decision {
  signature_count: number;
  total_signers: number;
  resolution_number: string | null;
}

export const resolutionsApi = {
  list: async (params?: { status?: string }): Promise<ResolutionListItem[]> => {
    const query = params?.status ? `?status=${params.status}` : "";
    const response = await api.get<PaginatedResponse<ResolutionListItem>>(`/resolutions${query}`);
    return response.items || [];
  },
  get: async (id: string): Promise<DecisionDetail> => {
    return api.get(`/resolutions/${id}`);
  },
  getSignatures: async (id: string): Promise<SignatureStatus> => {
    return api.get(`/resolutions/${id}/signatures`);
  },
  sign: async (id: string): Promise<{ status: string; signature_id: number; signed_at: string }> => {
    return api.post(`/resolutions/${id}/sign`);
  },
};

// =============================================================================
// Ideas API
// =============================================================================

export interface IdeaCategory {
  id: number;
  name: string;
  color: string;
  description?: string | null;
}

export interface Idea {
  id: number;
  title: string;
  description?: string | null;
  submitted_by_id: number;
  status: "new" | "under_review" | "approved" | "rejected" | "promoted";
  category_id?: number | null;
  category?: IdeaCategory | null;
  created_at: string;
  updated_at?: string;
}

export interface IdeaHistory {
  id: number;
  idea_id: number;
  field_changed: string;
  old_value?: string | null;
  new_value?: string | null;
  changed_by_id: number;
  changed_by_name?: string;
  reason?: string | null;
  created_at: string;
}

export type ReactionType = "thumbs_up" | "lightbulb" | "heart" | "warning";

export interface CommentReaction {
  id: number;
  comment_id: number;
  user_id: number;
  reaction_type: ReactionType;
}

export interface Comment {
  id: number;
  idea_id: number;
  author_id: number;
  user_id?: number; // alias for author_id (legacy)
  user_name?: string;
  content: string;
  parent_id?: number | null;
  is_pinned?: boolean;
  edited_at?: string | null;
  reactions?: Record<ReactionType, number>;
  user_reaction?: ReactionType | null;
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
    return api.get(`/ideas/${id}`);
  },

  /**
   * Submit a new idea
   */
  create: async (data: {
    title: string;
    description?: string;
  }): Promise<Idea> => {
    return api.post("/ideas", data);
  },

  /**
   * Add comment to idea
   */
  addComment: async (ideaId: string, content: string): Promise<Comment> => {
    return api.post(`/ideas/${ideaId}/comments`, { content });
  },

  /**
   * Get comments for idea
   */
  getComments: async (ideaId: string): Promise<Comment[]> => {
    const response = await api.get<PaginatedResponse<Comment>>(`/ideas/${ideaId}/comments`);
    return response.items || [];
  },

  /**
   * Update an idea
   */
  update: async (id: string, data: {
    title?: string;
    description?: string | null;
  }): Promise<Idea> => {
    return api.patch(`/ideas/${id}`, data);
  },

  /**
   * Update idea status (moderate)
   */
  updateStatus: async (id: string, status: Idea["status"]): Promise<Idea> => {
    return api.post(`/ideas/${id}/status`, { status });
  },

  /**
   * Delete an idea
   */
  delete: async (id: string): Promise<void> => {
    return api.delete(`/ideas/${id}`);
  },

  /**
   * Update idea status with reason
   */
  updateStatusWithReason: async (id: string, status: Idea["status"], reason?: string): Promise<Idea> => {
    return api.post(`/ideas/${id}/status`, { status, reason });
  },

  /**
   * Get idea history
   */
  getHistory: async (id: string): Promise<IdeaHistory[]> => {
    const response = await api.get<PaginatedResponse<IdeaHistory>>(`/ideas/${id}/history`);
    return response.items || [];
  },

  /**
   * Promote idea to decision (chair/admin only)
   */
  promote: async (ideaId: string): Promise<Decision> => {
    return api.post(`/ideas/${ideaId}/promote`);
  },

  /**
   * Toggle reaction on a comment
   */
  toggleReaction: async (ideaId: string, commentId: number, reactionType: ReactionType): Promise<void> => {
    return api.post(`/ideas/${ideaId}/comments/${commentId}/react`, { reaction_type: reactionType });
  },

  /**
   * Pin/unpin a comment
   */
  togglePinComment: async (ideaId: string, commentId: number): Promise<Comment> => {
    return api.post(`/ideas/${ideaId}/comments/${commentId}/pin`);
  },

  /**
   * Edit a comment
   */
  editComment: async (ideaId: string, commentId: number, content: string): Promise<Comment> => {
    return api.patch(`/ideas/${ideaId}/comments/${commentId}`, { content });
  },
};

// =============================================================================
// Idea Categories API (Admin only)
// =============================================================================

export const categoriesApi = {
  /**
   * List all categories
   */
  list: async (): Promise<IdeaCategory[]> => {
    const response = await api.get<IdeaCategory[] | PaginatedResponse<IdeaCategory>>("/ideas/categories");
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Create a category
   */
  create: async (data: { name: string; color: string; description?: string }): Promise<IdeaCategory> => {
    return api.post("/ideas/categories", data);
  },

  /**
   * Update a category
   */
  update: async (id: number, data: { name?: string; color?: string; description?: string }): Promise<IdeaCategory> => {
    return api.patch(`/ideas/categories/${id}`, data);
  },

  /**
   * Delete a category
   */
  delete: async (id: number): Promise<void> => {
    return api.delete(`/ideas/categories/${id}`);
  },
};

// =============================================================================
// Admin API (requires admin/chair role)
// =============================================================================

export interface BoardMember {
  id: number;
  name: string;
  email: string;
  role: "admin" | "chair" | "board" | "shareholder";
  status?: "active" | "inactive";
  created_at: string;
  last_login_at?: string | null;
}

export interface Invitation {
  id: number;
  email: string;
  name: string;
  role: "admin" | "chair" | "board" | "shareholder";
  invited_by_id: number;
  message?: string | null;
  expires_at: string;
  created_at: string;
  accepted_at?: string | null;
}

export interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  entity_name?: string;
  action: string;
  changed_by_id?: number;
  changed_by_name?: string;
  changed_at: string;
  changes?: Record<string, unknown> | null;
  ip_address?: string | null;
}

// =============================================================================
// Agent Admin Types
// =============================================================================

export interface AdminAgentConfig {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  system_prompt: string;
  model: string;
  max_iterations: number;
  temperature: number;
  allowed_tool_names: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
  parameter_count: number;
}

export interface AgentUsageStats {
  agent_id: number;
  agent_name: string;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  avg_duration_ms: number;
}

export interface SystemSettings {
  app_name: string;
  organization_name: string;
  organization_logo_url?: string | null;
  default_meeting_duration: number;
  default_timezone: string;
  voting_reminder_days: number;
  signature_reminder_days: number;
  [key: string]: string | number | boolean | null | undefined;
}

export const adminApi = {
  // -------------------------------------------------------------------------
  // User Management
  // -------------------------------------------------------------------------

  /**
   * List all users (admin only)
   */
  listUsers: async (): Promise<BoardMember[]> => {
    const response = await api.get<BoardMember[] | PaginatedResponse<BoardMember>>("/admin/users");
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Get user by ID
   */
  getUser: async (id: string): Promise<BoardMember> => {
    return api.get(`/admin/users/${id}`);
  },

  /**
   * Update user (role, status)
   */
  updateUser: async (
    id: string,
    data: { name?: string; role?: string }
  ): Promise<BoardMember> => {
    return api.patch(`/admin/users/${id}`, data);
  },

  /**
   * Deactivate user (soft delete)
   */
  deactivateUser: async (id: string): Promise<void> => {
    return api.delete(`/admin/users/${id}`);
  },

  /**
   * Reactivate user
   */
  reactivateUser: async (id: string): Promise<BoardMember> => {
    return api.post(`/admin/users/${id}/restore`);
  },

  // -------------------------------------------------------------------------
  // Invitations
  // -------------------------------------------------------------------------

  /**
   * List pending invitations
   */
  listInvitations: async (): Promise<Invitation[]> => {
    const response = await api.get<Invitation[] | PaginatedResponse<Invitation>>("/admin/invites");
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Send invitation
   */
  sendInvitation: async (data: {
    email: string;
    name: string;
    role: string;
    message?: string;
  }): Promise<Invitation> => {
    return api.post("/admin/users/invite", data);
  },

  /**
   * Resend invitation
   */
  resendInvitation: async (id: string): Promise<void> => {
    return api.post(`/admin/invites/${id}/resend`);
  },

  /**
   * Cancel invitation
   */
  cancelInvitation: async (id: string): Promise<void> => {
    return api.delete(`/admin/invites/${id}`);
  },

  // -------------------------------------------------------------------------
  // Audit Log
  // -------------------------------------------------------------------------

  /**
   * List audit log entries
   */
  listAuditLog: async (params?: {
    user_id?: string;
    action?: string;
    entity_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditLogEntry[]> => {
    const searchParams = new URLSearchParams();
    if (params?.user_id) searchParams.set("user_id", params.user_id);
    if (params?.action) searchParams.set("action", params.action);
    if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());

    const query = searchParams.toString();
    const response = await api.get<AuditLogEntry[] | { items: AuditLogEntry[] }>(`/admin/audit/${query ? `?${query}` : ""}`);
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Export audit log as CSV
   */
  exportAuditLog: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> => {
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);

    const query = searchParams.toString();
    const response = await fetch(`/api/proxy/admin/audit/export/${query ? `?${query}` : ""}`, {
      headers: {
        "X-User-Email": api["userEmail"] || "",
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, "Failed to export audit log");
    }

    return response.blob();
  },

  // -------------------------------------------------------------------------
  // Settings
  // -------------------------------------------------------------------------

  /**
   * Get all settings
   */
  getSettings: async (): Promise<SystemSettings> => {
    return api.get("/admin/settings");
  },

  /**
   * Update settings
   */
  updateSettings: async (settings: Partial<SystemSettings>): Promise<void> => {
    // Convert to the {settings: {key: value}} format the backend expects
    const payload: Record<string, string> = {};
    for (const [key, value] of Object.entries(settings)) {
      if (value !== undefined) {
        payload[key] = String(value);
      }
    }
    return api.patch("/admin/settings", { settings: payload });
  },

  /**
   * Upload organization logo
   */
  uploadLogo: async (file: File): Promise<{ url: string }> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/proxy/admin/settings/logo", {
      method: "POST",
      headers: {
        "X-User-Email": api["userEmail"] || "",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.message || "Failed to upload logo");
    }

    return response.json();
  },

  /**
   * Remove organization logo
   */
  removeLogo: async (): Promise<void> => {
    return api.delete("/admin/settings/logo");
  },

  // -------------------------------------------------------------------------
  // Roles & Permissions (placeholder - will be enhanced once backend ready)
  // -------------------------------------------------------------------------

  /**
   * Get permission matrix for all roles
   */
  getPermissionMatrix: async (): Promise<Record<string, string[]>> => {
    return api.get("/admin/permissions");
  },

  /**
   * Update permissions for a role
   */
  updateRolePermissions: async (
    role: string,
    permissions: string[]
  ): Promise<void> => {
    return api.put(`/admin/roles/${role}`, { permissions });
  },

  // -------------------------------------------------------------------------
  // Agent Management
  // -------------------------------------------------------------------------

  /**
   * List all agent configurations
   */
  listAgents: async (includeInactive = false): Promise<AdminAgentConfig[]> => {
    const query = includeInactive ? "?include_inactive=true" : "";
    const response = await api.get<AdminAgentConfig[] | PaginatedResponse<AdminAgentConfig>>(`/admin/agents${query}`);
    return Array.isArray(response) ? response : response.items || [];
  },

  /**
   * Create a new agent configuration
   */
  createAgent: async (data: {
    name: string;
    description?: string;
    system_prompt: string;
    model: string;
    max_iterations?: number;
    temperature?: number;
    allowed_tool_names?: string[];
  }): Promise<AdminAgentConfig> => {
    return api.post("/admin/agents", data);
  },

  /**
   * Update an agent configuration
   */
  updateAgent: async (id: number, data: Partial<AdminAgentConfig>): Promise<{ status: string; id: number }> => {
    return api.patch(`/admin/agents/${id}`, data);
  },

  /**
   * Deactivate an agent (soft delete)
   */
  deleteAgent: async (id: number): Promise<{ status: string; id: number }> => {
    return api.delete(`/admin/agents/${id}`);
  },

  /**
   * List all available tools from the tool registry
   */
  listAvailableTools: async (): Promise<ToolInfo[]> => {
    return api.get("/admin/agents/tools");
  },

  /**
   * Get aggregated usage statistics per agent
   */
  getAgentUsageStats: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<AgentUsageStats[]> => {
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);
    const query = searchParams.toString();
    return api.get(`/admin/agents/usage${query ? `?${query}` : ""}`);
  },

  // -------------------------------------------------------------------------
  // Agent API Keys
  // -------------------------------------------------------------------------

  /** Get API key status for all providers (admin only) */
  getApiKeys: async (): Promise<Record<string, { configured: boolean; source: string; masked_value: string }>> => {
    return api.get("/agents/api-keys");
  },

  /** Update API keys for providers (admin only) */
  updateApiKey: async (data: { anthropic_api_key?: string; groq_api_key?: string }): Promise<{ status: string; keys: string[] }> => {
    return api.put("/agents/api-keys", data);
  },

  /** Get available models (filtered by configured providers) */
  getAvailableModels: async (): Promise<{ models: Array<{ value: string; label: string; provider: string }> }> => {
    return api.get("/agents/available-models");
  },
};
