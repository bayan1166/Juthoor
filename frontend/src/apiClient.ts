const API_BASE = import.meta.env.VITE_API_BASE_URL as string;

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, body: string) {
    super(body);
    this.status = status;
  }
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface QuestionOut {
  question: string;
  correct_answer: string;
  distractors: { text: string; misconception: string }[];
  hint: string;
  explanation: string;
  skill: string;
  difficulty: number;
  pattern: string;
  source: string;
  banner: string;
  guided: boolean;
}

export interface DecisionOut {
  action: string;
  next_skill: string;
  next_difficulty: number;
  reason: string;
  breadcrumb: string;
  gap_skill: string | null;
  round_over: boolean;
  coins_awarded: number;
  gems_awarded: number;
}

export interface WalletOut {
  student_id: string;
  coins: number;
  gems: number;
  lifetime_coins_earned: number;
  lifetime_gems_earned: number;
}

export interface ChatMessageResponse {
  reply: string;
  gap_detected: boolean;
  gap_skill: string | null;
  drill_down_triggered: boolean;
  next_skill: string | null;
  next_difficulty: number | null;
  breadcrumb: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload: Record<string, unknown>) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
};

export const adaptiveApi = {
  getQuestion: (studentId: string) =>
    request<QuestionOut>(`/students/${studentId}/adaptive/question`),
  submitAnswer: (studentId: string, payload: Record<string, unknown>) =>
    request<DecisionOut>(`/students/${studentId}/adaptive/answer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const economyApi = {
  getWallet: (studentId: string) => request<WalletOut>(`/students/${studentId}/economy/wallet`),
  getShop: (studentId: string, category?: string) =>
    request(`/students/${studentId}/economy/shop${category ? `?category=${category}` : ""}`),
  purchase: (studentId: string, itemId: string, currency: "coins" | "gems") =>
    request(`/students/${studentId}/economy/purchase`, {
      method: "POST",
      body: JSON.stringify({ item_id: itemId, currency }),
    }),
};

export const chatApi = {
  start: (studentId: string, skillContext: string) =>
    request<{ session_id: string; opening_message: string }>(`/students/${studentId}/chat/start`, {
      method: "POST",
      body: JSON.stringify({ skill_context: skillContext }),
    }),
  send: (studentId: string, sessionId: string, message: string) =>
    request<ChatMessageResponse>(`/students/${studentId}/chat/message`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
};

export const insightsApi = {
  getStudentInsights: (studentId: string) => request(`/students/${studentId}/insights`),
  getCohortInsights: (organizationId: string) => request(`/organizations/${organizationId}/insights`),
};
