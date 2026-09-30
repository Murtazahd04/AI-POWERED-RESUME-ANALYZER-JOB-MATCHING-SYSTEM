import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

export default function ResumeDetailPage() {
  const { id } = useParams();
  const [resume, setResume] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    resumeApi.get(id).then(setResume).catch((e) => setError(apiErrorMessage(e)));
  }, [id]);

  async function reparse() {
    setBusy(true);
    setError("");
    try {
      const data = await resumeApi.reparse(id);
      setResume((r) => ({ ...r, parsed: data.parsed }));
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (!resume && error) {
    return (
      <div className="app-page">
        <Link to="/resumes" className="back-link">← Back to resumes</Link>
        <div className="auth-error" style={{ marginTop: 20 }}>{error}</div>
      </div>
    );
  }
  if (!resume) return <div className="app-page"><p className="muted">Loading...</p></div>;

  const p = resume.parsed;

  if (!p) {
    return (
      <div className="app-page">
        <Link to="/resumes" className="back-link">← Back to resumes</Link>
        <p style={{ marginTop: 20 }}>This resume hasn't been parsed yet.</p>
        {error && <div className="auth-error">{error}</div>}
        <button onClick={reparse} disabled={busy}>
          {busy ? "Parsing..." : "Parse now"}
        </button>
      </div>
    );
  }

  const technical = p.skills?.technical ?? [];
  const soft = p.skills?.soft ?? [];
  const experience = p.experience ?? [];
  const education = p.education ?? [];
  const projects = p.projects ?? [];
  const certifications = p.certifications ?? [];

  return (
    <div className="app-page">
      <Link to="/resumes" className="back-link">← Back to resumes</Link>
      <h1 className="page-title">{p.name || resume.filename}</h1>
      <p className="page-subtitle">
        {resume.filename} · {p.total_experience_years ?? 0} years of experience detected
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <a href={resume.file_url} target="_blank" rel="noreferrer">View original</a>
        <button onClick={reparse} disabled={busy}>
          {busy ? "Parsing..." : "Re-parse"}
        </button>
      </div>
      {error && <div className="auth-error">{error}</div>}

      <div className="detail-card">
        <h2 className="section-title">Contact</h2>
        <p>Email: {p.contact?.email || "—"}</p>
        <p>Phone: {p.contact?.phone || "—"}</p>
        <p>LinkedIn: {p.contact?.linkedin || "—"}</p>
        <p>GitHub: {p.contact?.github || "—"}</p>
      </div>

      <div className="detail-card">
        <h2 className="section-title">Skills</h2>
        <div className="tag-row">
          {[...technical, ...soft].map((s) => (
            <span key={s} className="tag">{s}</span>
          ))}
          {technical.length + soft.length === 0 && (
            <span className="muted">No skills detected.</span>
          )}
        </div>
      </div>

      <div className="detail-card">
        <h2 className="section-title">Experience</h2>
        {experience.length === 0 && <p className="muted">No experience detected.</p>}
        {experience.map((e, i) => (
          <div key={i} className="detail-block">
            <strong>{e.title || "Role"}</strong> <span className="muted">({e.date_range})</span>
            <ul>{(e.highlights ?? []).map((h, j) => <li key={j}>{h}</li>)}</ul>
          </div>
        ))}
      </div>

      <div className="detail-card">
        <h2 className="section-title">Education</h2>
        {education.length === 0 && <p className="muted">No education detected.</p>}
        {education.map((e, i) => (
          <div key={i} className="detail-block">
            <strong>{e.degree}</strong>
            <div className="muted">{[e.institution, e.year].filter(Boolean).join(" · ")}</div>
          </div>
        ))}
      </div>

      <div className="detail-card">
        <h2 className="section-title">Projects</h2>
        {projects.length === 0 && <p className="muted">No projects detected.</p>}
        {projects.map((proj, i) => (
          <div key={i} className="detail-block">
            <strong>{proj.name}</strong>
            {(proj.description ?? []).map((d, j) => <p key={j} style={{ margin: "4px 0" }}>{d}</p>)}
            <div className="tag-row">
              {(proj.technologies ?? []).map((t) => <span key={t} className="tag">{t}</span>)}
            </div>
          </div>
        ))}
      </div>

      <div className="detail-card">
        <h2 className="section-title">Certifications</h2>
        {certifications.length === 0 && <p className="muted">None detected.</p>}
        <ul>{certifications.map((c, i) => <li key={i}>{c}</li>)}</ul>
      </div>
    </div>
  );
}