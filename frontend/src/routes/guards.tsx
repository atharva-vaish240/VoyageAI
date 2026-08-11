import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/** Requires authentication — redirects to /login if not authenticated. */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="page-loading">Loading...</div>;
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

/** Redirects authenticated users away from login/signup to /app. */
export function GuestRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="page-loading">Loading...</div>;
  }

  return isAuthenticated ? <Navigate to="/app" replace /> : <Outlet />;
}

/** Requires ADMIN role — returns 403-style message for non-admins. */
export function AdminRoute() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="page-loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== "ADMIN") {
    return (
      <div className="page-container">
        <h1>Access Denied</h1>
        <p>You do not have permission to access this page.</p>
      </div>
    );
  }

  return <Outlet />;
}
