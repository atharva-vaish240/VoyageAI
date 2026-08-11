import { useAuth } from "../hooks/useAuth";

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="page-container">
      <h1>Profile</h1>
      <div style={{
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 24,
        maxWidth: 480,
        marginTop: 16,
      }}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 13, color: "var(--text)", display: "block" }}>Name</label>
          <p style={{ margin: "4px 0 0", fontSize: 16, color: "var(--text-h)" }}>{user?.name}</p>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 13, color: "var(--text)", display: "block" }}>Email</label>
          <p style={{ margin: "4px 0 0", fontSize: 16, color: "var(--text-h)" }}>{user?.email}</p>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 13, color: "var(--text)", display: "block" }}>Role</label>
          <p style={{ margin: "4px 0 0", fontSize: 16, color: "var(--text-h)" }}>{user?.role}</p>
        </div>
        <div>
          <label style={{ fontSize: 13, color: "var(--text)", display: "block" }}>Auth Provider</label>
          <p style={{ margin: "4px 0 0", fontSize: 16, color: "var(--text-h)" }}>{user?.auth_provider}</p>
        </div>
      </div>
    </div>
  );
}
