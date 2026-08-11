import { useAuth } from "../hooks/useAuth";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="page-container">
      <h1>Welcome, {user?.name}!</h1>
      <p>Your AI travel planner is coming soon.</p>
      <p style={{ color: "var(--text)", marginTop: 8, fontSize: 14 }}>
        Plan Trip functionality will be available in a later phase.
      </p>
    </div>
  );
}
