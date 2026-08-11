import api from "./client";
import type {
  SignupRequest,
  LoginRequest,
  TokenResponse,
  User,
  MessageResponse,
} from "../types/auth";

export const authApi = {
  signup: (data: SignupRequest) =>
    api.post<User>("/auth/signup", data),

  login: (data: LoginRequest) =>
    api.post<TokenResponse>("/auth/login", data),

  refresh: (refresh_token: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token }),

  logout: (refresh_token: string) =>
    api.post<MessageResponse>("/auth/logout", { refresh_token }),

  me: () =>
    api.get<User>("/auth/me"),
};
