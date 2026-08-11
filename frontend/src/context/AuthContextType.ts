import { createContext } from "react";
import type { User } from "../types/auth";

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  handleOAuthTokens: (accessToken: string, refreshToken: string) => Promise<void>;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);
