import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute, GuestRoute, AdminRoute } from "./routes/guards";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import HomePage from "./pages/HomePage";
import TripsPage from "./pages/TripsPage";
import PreferencesPage from "./pages/PreferencesPage";
import ProfilePage from "./pages/ProfilePage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public / guest routes */}
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
          </Route>

          {/* OAuth callback — accessible regardless of auth state */}
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

          {/* Protected app routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/app" element={<HomePage />} />
              <Route path="/app/trips" element={<TripsPage />} />
              <Route path="/app/preferences" element={<PreferencesPage />} />
              <Route path="/app/profile" element={<ProfilePage />} />

              {/* Admin-only routes */}
              <Route element={<AdminRoute />}>
                <Route path="/app/admin" element={<AdminPage />} />
              </Route>
            </Route>
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
