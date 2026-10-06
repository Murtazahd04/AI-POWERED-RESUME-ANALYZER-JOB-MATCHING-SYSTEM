import { useEffect, useState } from "react";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const CATEGORY_LABELS = {
  skills: "Skills",
  experience: "Experience",
  education: "Education",
  projects: "Projects",
};

function tone(score) {
  if (score >= 85) return "rs-excellent";
  if (score >= 70) return "rs-good";
  if (score >= 50) return "rs-fair";
  return "rs-weak";
}

function FactorRow({ factor }) {
  const full = factor.points >= factor.max;
  return (
    <li className={`rs-factor ${full ? "rs-factor-full" : "rs-factor-short"}`}>
      <div className="rs-factor-head">
        <span>{factor.label}</span>
        <span className="rs-factor-points">
          {factor.points}/{factor.max}
        </span>
      </div>
      <p className="rs-factor-note">{factor.note}</p>
    </li>
  );
}

function CategoryCard({ name, data }) {
  return (
    <div className="rs-category">
      <div className="rs-category-head">
        <h3>{CATEGORY_LABELS[name] || name}</h3>
        <span className={`rs-pill ${tone(data.score)}`}>{data.score}/100</span>
      </div>
      <div className="rs-bar">
        <i style={{ width: `${data.score}%` }} />
      </div>
      <ul className="rs-factor-list">
        {data.factors.map((f, i) => (
          <FactorRow key={i} factor={f} />
        ))}
      </ul>
    </div>
  );
}

export default function ResumeScorePanel({ resumeId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    resumeApi
      .score(resumeId)
      .then(setData)
      .catch((e) => setError(apiErrorMessage(e, "Could not calculate the resume score.")))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId]);

  if (loading) return <p className="muted">Calculating score...</p>;
  if (error) return <div className="auth-error">{error}</div>;
  if (!data) return null;

  return (
    <div className="detail-card">
      <div className="rs-overall">
        <div className={`rs-ring ${tone(data.overall)}`}>
          <b>{data.overall}</b>
          <span>/100</span>
        </div>
        <div>
          <div className="rs-grade">{data.grade}</div>
          <p className="muted" style={{ margin: "4px 0 0" }}>{data.summary}</p>
        </div>
        <button className="btn-small" onClick={load} style={{ marginLeft: "auto" }}>
          Recalculate
        </button>
      </div>

      <div className="rs-categories">
        {Object.entries(data.components).map(([name, comp]) => (
          <CategoryCard key={name} name={name} data={comp} />
        ))}
      </div>

      <h2 className="section-title" style={{ marginTop: 24 }}>ATS compatibility - {data.ats.score}/100</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Whether an Applicant Tracking System can read this resume correctly.
      </p>
      <ul className="rs-ats-list">
        {data.ats.checks.map((c, i) => (
          <li key={i} className={c.points >= c.max ? "rs-ats-pass" : "rs-ats-fail"}>
            <span className="rs-ats-icon">{c.points >= c.max ? "check" : "x"}</span>
            <div>
              <div className="rs-ats-label">{c.label}</div>
              <div className="rs-factor-note">{c.note}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
