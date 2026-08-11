import axios from "axios";
import type { TokenResponse } from "../types/auth";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

// ── Token storage ───────────────────────────────────────────────
// localStorage is used because:
// 1. Tokens must survive page refreshes (otherwise every reload = re-login)
// 2. httpOnly cookies would require backend changes (Set-Cookie headers)
// 3. For this project scope, localStorage + short-lived access tokens
//    + server-side refresh token revocation is an acceptable tradeoff.
// The access token expires in 15 minutes, limiting exposure.

const TOKEN_KEYS = {
  access: "voyageai_access_token",
  refresh: "voyageai_refresh_token",
} as const;

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEYS.access);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(TOKEN_KEYS.refresh);
}

export function saveTokens(tokens: TokenResponse): void {
  localStorage.setItem(TOKEN_KEYS.access, tokens.access_token);
  localStorage.setItem(TOKEN_KEYS.refresh, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEYS.access);
  localStorage.removeItem(TOKEN_KEYS.refresh);
}

// ── Axios instance ──────────────────────────────────────────────

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Automatic token refresh on 401 ─────────────────────────────

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function onRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Don't retry if:
    // - Not a 401
    // - Already retried
    // - The failing request IS the refresh endpoint (avoid infinite loop)
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until refresh completes
      return new Promise((resolve) => {
        addRefreshSubscriber((newToken: string) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          originalRequest._retry = true;
          resolve(api(originalRequest));
        });
      });
    }

    isRefreshing = true;
    originalRequest._retry = true;

    try {
      const { data } = await axios.post<TokenResponse>(
        `${API_BASE}/auth/refresh`,
        { refresh_token: refreshToken },
      );
      saveTokens(data);
      onRefreshed(data.access_token);

      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return api(originalRequest);
    } catch {
      clearTokens();
      // Redirect to login — handled by AuthContext checking tokens
      window.location.href = "/login";
      return Promise.reject(error);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
