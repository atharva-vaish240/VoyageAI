// ── User ────────────────────────────────────────────────────────

export interface User {
  id: number;
  name: string;
  email: string;
  role: "USER" | "ADMIN";
  is_active: boolean;
  auth_provider: string;
  created_at: string;
  updated_at: string;
}

// ── Auth requests ───────────────────────────────────────────────

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

// ── Auth responses ──────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MessageResponse {
  message: string;
}

// ── API error ───────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}
