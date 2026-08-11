import { useState, useRef, useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import "./AppLayout.css";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Close menu on route change
  useEffect(() => {
    const timer = setTimeout(() => {
      setMenuOpen(false);
    }, 0);
    return () => clearTimeout(timer);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
  };

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <div className="app-layout">
      <header className="app-header">
        <Link to="/app" className="app-logo">
          VoyageAI
        </Link>

        <nav className="app-nav">
          <Link
            to="/app"
            className={`nav-link ${isActive("/app") && !isActive("/app/trips") && !isActive("/app/preferences") && !isActive("/app/profile") && !isActive("/app/admin") ? "active" : ""}`}
          >
            Home
          </Link>
          <Link
            to="/app/trips"
            className={`nav-link ${isActive("/app/trips") ? "active" : ""}`}
          >
            My Trips
          </Link>
          <Link
            to="/app/preferences"
            className={`nav-link ${isActive("/app/preferences") ? "active" : ""}`}
          >
            Preferences
          </Link>
          {user?.role === "ADMIN" && (
            <Link
              to="/app/admin"
              className={`nav-link ${isActive("/app/admin") ? "active" : ""}`}
            >
              Admin
            </Link>
          )}
        </nav>

        <div className="profile-menu" ref={menuRef}>
          <button
            className="profile-trigger"
            onClick={() => setMenuOpen((prev) => !prev)}
            aria-expanded={menuOpen}
            aria-haspopup="true"
          >
            <span className="profile-avatar">
              {user?.name?.charAt(0).toUpperCase() || "U"}
            </span>
            <span className="profile-name">{user?.name}</span>
            <span className="profile-caret">▾</span>
          </button>

          {menuOpen && (
            <div className="profile-dropdown">
              <div className="dropdown-user-info">
                <p className="dropdown-name">{user?.name}</p>
                <p className="dropdown-email">{user?.email}</p>
                <span className="dropdown-role">{user?.role}</span>
              </div>
              <hr className="dropdown-divider" />
              <Link to="/app/profile" className="dropdown-item">
                Profile
              </Link>
              <button className="dropdown-item logout" onClick={handleLogout}>
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
