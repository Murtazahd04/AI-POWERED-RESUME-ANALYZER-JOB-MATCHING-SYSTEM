import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: "▦" },
  { to: "/resumes", label: "Resume Analyzer", icon: "↑" },
  { to: "/resume-score", label: "Resume Score", icon: "◉" },
  { to: "/job-matching", label: "Job Matching", icon: "○" },
  { to: "/skill-gap", label: "Skill Gap", icon: "◇", soon: true },
  { to: "/profile", label: "Profile", icon: "◎", soon: true },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = (user?.name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand" onClick={() => navigate("/dashboard")}>
          Resume<span style={{ color: "var(--primary)" }}>AI</span>
        </div>
        <nav>
          {LINKS.map((l) =>
            l.soon ? (
              // Not a link yet, so it can never look "active".
              <div key={l.to} className="sidebar-link sidebar-link-soon">
                <span className="sidebar-icon">{l.icon}</span> {l.label}
                <span className="sidebar-soon-tag">soon</span>
              </div>
            ) : (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}
              >
                <span className="sidebar-icon">{l.icon}</span> {l.label}
              </NavLink>
            )
          )}
        </nav>
        <div className="sidebar-footer">
          <button className="btn-small" onClick={logout} style={{ width: "100%" }}>
            Log out
          </button>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topbar">
          <span />
          <div className="avatar">{initials}</div>
        </header>
        <main className="shell-content">{children}</main>
      </div>
    </div>
  );
}