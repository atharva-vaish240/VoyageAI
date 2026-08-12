import { useState, useRef, useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import PillNav from "../ui/PillNav";
import type { PillNavItem } from "../ui/PillNav";
import SpecularButton from "../ui/SpecularButton";
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

  const navItems: PillNavItem[] = [
    { label: "Home", href: "/app" },
    { label: "My Trips", href: "/app/trips" },
    { label: "Preferences", href: "/app/preferences" },
  ];

  if (user?.role === "ADMIN") {
    navItems.push({ label: "Admin", href: "/app/admin" });
  }

  const logoElement = (
    <Link to="/app" className="app-logo">
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="logo-svg"
      >
        <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="url(#logo-grad-pill)" />
        <defs>
          <linearGradient
            id="logo-grad-pill"
            x1="2"
            y1="3"
            x2="23"
            y2="21"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#a78bfa" />
            <stop offset="1" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
      </svg>
      <span className="logo-text">VoyageAI</span>
    </Link>
  );

  const userControlElement = (
    <div className="profile-menu" ref={menuRef}>
      <SpecularButton
        size="custom"
        radius={9999}
        tint="#8b5cf6"
        tintOpacity={0.15}
        blur={4}
        textColor="#ffffff"
        lineColor="#c084fc"
        baseColor="#1e1b4b"
        intensity={1.2}
        shineSize={18}
        shineFade={36}
        thickness={1.5}
        speed={0.35}
        followMouse={true}
        proximity={250}
        autoAnimate={false}
        onClick={() => setMenuOpen((prev) => !prev)}
        ariaExpanded={menuOpen}
        ariaHasPopup="true"
        className="profile-trigger"
      >
        <span className="profile-avatar">
          {user?.name?.charAt(0).toUpperCase() || "U"}
        </span>
        <span className="profile-name">{user?.name}</span>
        <span className="profile-caret">▾</span>
      </SpecularButton>

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
  );

  return (
    <div className="app-layout">
      <PillNav
        items={navItems}
        activeHref={location.pathname}
        logo={logoElement}
        userControl={userControlElement}
      />

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
