import { useAuth } from "../hooks/useAuth";

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="page-container profile-page">
      <div
        className="profile-container"
        style={{
          maxWidth: 540,
          margin: "20px auto 0",
          background: "var(--bg-card)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: "1px solid var(--border)",
          borderRadius: 24,
          padding: "40px 32px",
          boxShadow: "0 20px 40px -10px rgba(0, 0, 0, 0.6), 0 0 30px rgba(124, 58, 237, 0.15)",
          textAlign: "center",
        }}
      >
        {/* Avatar Circle */}
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: "50%",
            background: "var(--accent-gradient)",
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 32,
            fontWeight: 800,
            margin: "0 auto 16px",
            boxShadow: "0 0 25px rgba(124, 58, 237, 0.4)",
          }}
        >
          {user?.name?.charAt(0).toUpperCase() || "U"}
        </div>

        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#ffffff", margin: "0 0 4px" }}>
          {user?.name}
        </h2>

        <span
          style={{
            display: "inline-block",
            fontSize: 11,
            fontWeight: 700,
            padding: "4px 14px",
            borderRadius: 9999,
            background: "var(--accent-bg)",
            color: "var(--accent-light)",
            border: "1px solid var(--accent-border)",
            letterSpacing: 0.8,
            textTransform: "uppercase",
            marginBottom: 32,
          }}
        >
          {user?.role || "USER"}
        </span>

        {/* Info Rows */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            textAlign: "left",
            borderTop: "1px solid var(--border)",
            paddingTop: 24,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
              borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 8 }}>
              ✉️ Email
            </span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-h)" }}>
              {user?.email}
            </span>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
              borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 8 }}>
              👤 Role
            </span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-h)" }}>
              {user?.role}
            </span>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 8 }}>
              🔑 Auth Provider
            </span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-h)" }}>
              {user?.auth_provider}
            </span>
          </div>
        </div>

        {/* Quote */}
        <div
          style={{
            marginTop: 32,
            paddingTop: 20,
            borderTop: "1px solid var(--border)",
            fontSize: 14,
            fontStyle: "italic",
            color: "var(--accent-light)",
          }}
        >
          "The journey is the reward." ✈️
        </div>
      </div>
    </div>
  );
}
