import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import type { User } from "../types/auth";
import { authApi } from "../api/auth";
import {
  getAccessToken,
  getRefreshToken,
  saveTokens,
  clearTokens,
} from "../api/client";
import { AuthContext } from "./AuthContextType";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current user from /auth/me
  const fetchUser = useCallback(async () => {
    try {
      const { data } = await authApi.me();
      setUser(data);
    } catch {
      setUser(null);
      clearTokens();
    }
  }, []);

  // On mount: check if we have a token and fetch user
  useEffect(() => {
    let isMounted = true;
    const initAuth = async () => {
      const token = getAccessToken();
      if (token) {
        await fetchUser();
      }
      if (isMounted) {
        setIsLoading(false);
      }
    };

    initAuth();

    return () => {
      isMounted = false;
    };
  }, [fetchUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await authApi.login({ email, password });
      saveTokens(data);
      await fetchUser();
    },
    [fetchUser],
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      await authApi.signup({ name, email, password });
      // After signup, don't auto-login — redirect to login page
    },
    [],
  );

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // Server-side revocation may fail — clear local state regardless
      }
    }
    clearTokens();
    setUser(null);
  }, []);

  const handleOAuthTokens = useCallback(
    async (accessToken: string, refreshToken: string) => {
      saveTokens({
        access_token: accessToken,
        refresh_token: refreshToken,
        token_type: "bearer",
      });
      await fetchUser();
    },
    [fetchUser],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        handleOAuthTokens,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
