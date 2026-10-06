import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { resumeApi } from "../api/endpoints";

export default function DashboardPage() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState(null);

  useEffect(() => {
    resumeApi.list().then(setResumes).catch(() => setResumes([]));
  }, []);

  const latest = resumes?.find((r) => r.score) || resumes?.[0] || null;
  const skillCount = latest?.parsed
    ? latest.parsed.skills.technical.length + latest.parsed.skills.soft.length
    : null;

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">AI-powered resume analysis &amp; career matching</p>

      <div className="hero-banner">
        <div>
          <h2 style={{ color: "#fff", fontSize: "1.6rem", margin: "0 0 10px" }}>Build your career with AI.</h2>
          <p style={{ color: "rgba(255,255,255,0.9)", maxWidth: 480, margin: "0 0 20px" }}>
            Upload your resume, see your score, and find out exactly what to improve.
          </p>
          <button className="btn-hero" onClick={() => navigate("/resumes")}>
            Analyze My Resume →
          </button>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Resume Score</div>
          <div className="stat-value">{latest?.score ? `${latest.score.overall}/100` : "—"}</div>
          <div className="stat-sub">{latest?.score ? latest.score.grade : "Upload & score a resume"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Skills Detected</div>
          <div className="stat-value">{skillCount ?? "—"}</div>
          <div className="stat-sub">{latest ? `From "${latest.filename}"` : "No resume yet"}</div>
        </div>
        <div className="stat-card stat-card-soon">
          <div className="stat-label">Skill Gaps</div>
          <div className="stat-value">—</div>
          <div className="stat-sub">Coming soon</div>
        </div>
      </div>

      <h2 className="section-title">Your resumes</h2>
      {resumes === null && <p className="muted">Loading...</p>}
      {resumes?.length === 0 && (
        <div className="empty-state">No resumes yet. Click "Analyze My Resume" above to upload one.</div>
      )}
      <div className="feature-grid">
        {resumes?.slice(0, 3).map((r) => (
          <div key={r.id} className="feature-card" style={{ cursor: "pointer" }} onClick={() => navigate(`/resumes/${r.id}`)}>
            <div className="feature-card-top">
              <h3>{r.filename}</h3>
              {r.score && <span className="badge badge-live">{r.score.overall}/100</span>}
            </div>
            <p className="muted">
              {r.score ? r.score.grade : "Not scored yet"} · uploaded {new Date(r.uploaded_at).toLocaleDateString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}