import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div style={{ maxWidth: 600, margin: "80px auto", fontFamily: "sans-serif", textAlign: "center" }}>
      <h1>Welcome, {user?.name}! 🎉</h1>
      <p>You're logged in as {user?.email}.</p>
      <button onClick={logout} style={{ padding: "10px 20px", marginTop: 20 }}>
        Log out
      </button>
    </div>
  );
}