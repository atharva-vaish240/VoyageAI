import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import gsap from "gsap";
import "./PillNav.css";

export interface PillNavItem {
  label: string;
  href: string;
  ariaLabel?: string;
}

export interface PillNavProps {
  items: PillNavItem[];
  activeHref: string;
  logo?: React.ReactNode;
  userControl?: React.ReactNode;
  baseColor?: string;
  pillColor?: string;
  pillTextColor?: string;
  hoveredPillTextColor?: string;
  ease?: string;
  initialLoadAnimation?: boolean;
  className?: string;
}

export default function PillNav({
  items,
  activeHref,
  logo,
  userControl,
  baseColor = "rgba(5, 8, 22, 0.45)",
  pillColor = "#8b5cf6",
  pillTextColor = "#94a3b8",
  hoveredPillTextColor = "#ffffff",
  ease = "power2.out",
  initialLoadAnimation = true,
  className = "",
}: PillNavProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const logoRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const circleRefs = useRef<(HTMLSpanElement | null)[]>([]);

  // Initial load animation
  useEffect(() => {
    if (initialLoadAnimation && navRef.current) {
      gsap.fromTo(
        navRef.current,
        { opacity: 0, y: -16 },
        { opacity: 1, y: 0, duration: 0.5, ease }
      );
    }
  }, [initialLoadAnimation, ease]);

  // Mobile menu open/close animation
  useEffect(() => {
    if (!mobileMenuRef.current) return;
    if (isMobileMenuOpen) {
      gsap.fromTo(
        mobileMenuRef.current,
        { opacity: 0, y: -10, display: "flex" },
        { opacity: 1, y: 0, duration: 0.3, ease }
      );
    } else {
      gsap.to(mobileMenuRef.current, {
        opacity: 0,
        y: -10,
        duration: 0.2,
        ease,
        onComplete: () => {
          if (mobileMenuRef.current) mobileMenuRef.current.style.display = "none";
        },
      });
    }
  }, [isMobileMenuOpen, ease]);

  const handleMouseEnter = (index: number) => {
    const circle = circleRefs.current[index];
    if (circle) {
      gsap.to(circle, { scale: 1, duration: 0.3, ease });
    }
  };

  const handleMouseLeave = (index: number) => {
    const circle = circleRefs.current[index];
    if (circle) {
      gsap.to(circle, { scale: 0, duration: 0.25, ease });
    }
  };

  const handleLogoMouseEnter = () => {
    if (logoRef.current) {
      gsap.to(logoRef.current, { scale: 1.04, duration: 0.2, ease: "power1.out" });
    }
  };

  const handleLogoMouseLeave = () => {
    if (logoRef.current) {
      gsap.to(logoRef.current, { scale: 1, duration: 0.2, ease: "power1.out" });
    }
  };

  const isItemActive = (href: string) => {
    if (href === "/app") {
      return (
        activeHref === "/app" &&
        !activeHref.startsWith("/app/trips") &&
        !activeHref.startsWith("/app/preferences") &&
        !activeHref.startsWith("/app/profile") &&
        !activeHref.startsWith("/app/admin")
      );
    }
    return activeHref === href || activeHref.startsWith(href + "/");
  };

  return (
    <header
      ref={navRef}
      className={`pill-nav-header ${className}`}
      style={{ backgroundColor: baseColor }}
    >
      <div className="pill-nav-container">
        {/* Brand Logo */}
        {logo && (
          <div
            ref={logoRef}
            className="pill-nav-logo"
            onMouseEnter={handleLogoMouseEnter}
            onMouseLeave={handleLogoMouseLeave}
          >
            {logo}
          </div>
        )}

        {/* Desktop Navigation Items */}
        <nav className="pill-nav-items" aria-label="Main Navigation">
          {items.map((item, index) => {
            const active = isItemActive(item.href);

            return (
              <Link
                key={index}
                to={item.href}
                aria-label={item.ariaLabel || item.label}
                className={`pill-nav-item ${active ? "is-active" : ""}`}
                onMouseEnter={() => handleMouseEnter(index)}
                onMouseLeave={() => handleMouseLeave(index)}
                style={{
                  color: active ? hoveredPillTextColor : pillTextColor,
                }}
              >
                {/* Hover circle indicator */}
                <span
                  ref={(el) => {
                    circleRefs.current[index] = el;
                  }}
                  className="pill-hover-circle"
                  style={{ backgroundColor: pillColor }}
                />

                <span className="pill-nav-text">{item.label}</span>

                {/* Active indicator bar */}
                {active && (
                  <span
                    className="pill-active-bg"
                    style={{ backgroundColor: "rgba(255, 255, 255, 0.08)" }}
                  />
                )}
              </Link>
            );
          })}
        </nav>

        {/* User / Profile Control */}
        {userControl && <div className="pill-nav-user-control">{userControl}</div>}

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          className={`pill-mobile-toggle ${isMobileMenuOpen ? "is-open" : ""}`}
          onClick={() => setIsMobileMenuOpen((prev) => !prev)}
          aria-label="Toggle Navigation Menu"
          aria-expanded={isMobileMenuOpen}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>
      </div>

      {/* Mobile Drawer */}
      <div ref={mobileMenuRef} className="pill-mobile-menu">
        {items.map((item, index) => {
          const active = isItemActive(item.href);
          return (
            <Link
              key={index}
              to={item.href}
              className={`pill-mobile-item ${active ? "is-active" : ""}`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
