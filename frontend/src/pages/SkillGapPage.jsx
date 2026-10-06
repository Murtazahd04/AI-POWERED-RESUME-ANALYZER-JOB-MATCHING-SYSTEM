import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { resumeApi, skillGapApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const PRIORITY_STYLE = {
  high: { background: "#fee2e2", color: "#b91c1c" },
  medium: { background: "#fef3c7", color: "#b45309" },
  low: { background: "#e0e7ff", color: "#4338ca" },
};
const COLOR_MATCHED = "#16a34a";
const COLOR_GAP = "#ef4444";

function compatibilityLabel(value) {
  if (value >= 80) return "Strong fit";
  if (value >= 60) return "Good fit, a few gaps";
  if (value >= 40) return "Partial fit";
  return "Big gaps to close";
}

function PriorityBadge({ level }) {
  return (
    <span
      style={{
        ...PRIORITY_STYLE[level],
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: "0.78rem",
        fontWeight: 600,
      }}
    >
      {level} priority
    </span>
  );
}

function RequirementChart({ requirements }) {
  const data = requirements.map((r) => ({
    skill: r.skill,
    score: Math.round(r.score * 100),
    status: r.status,
  }));
  return (
    <div style={{ width: "100%", height: Math.max(180, data.length * 38) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="skill" width={110} />
          <Tooltip formatter={(v) => [`${v}% match`, "Resume evidence"]} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((d) => (
              <Cell key={d.skill} fill={d.status === "gap" ? COLOR_GAP : COLOR_MATCHED} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function SkillGapPage() {
  const [resumes, setResumes] = useState(null);
  const [roleSuggestions, setRoleSuggestions] = useState([]);
  const [resumeId, setResumeId] = useState("");
  const [role, setRole] = useState("");
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    resumeApi
      .list()
      .then((list) => {
        setResumes(list);
        const firstParsed = list.find((r) => r.parsed);
        if (firstParsed) setResumeId((cur) => cur || firstParsed.id);
      })
      .catch((e) => {
        setResumes([]);
        setError(`Couldn't load your resumes: ${apiErrorMessage(e)}`);
      });

    skillGapApi.roles().then(setRoleSuggestions).catch(() => {});

    skillGapApi
      .latest()
      .then((latest) => {
        if (latest) {
          setResult(latest);
          setResumeId(latest.resume_id);
          setRole(latest.role || latest.job_title || "");
        }
      })
      .catch(() => {});
  }, []);

  const run = async (e) => {
    e.preventDefault();
    setRunning(true);
    setError("");
    try {
      setResult(await skillGapApi.analyze(resumeId, role.trim()));
    } catch (err) {
      setError(apiErrorMessage(err, "Couldn't run the skill gap analysis."));
    } finally {
      setRunning(false);
    }
  };

  const loading = resumes === null;
  const parsedResumes = resumes?.filter((r) => r.parsed) ?? [];
  const matched = result?.requirements.filter((r) => r.status === "matched") ?? [];

  return (
    <div className="app-page">
      <h1 className="page-title">Skill Gap</h1>
      <p className="page-subtitle">
        Type the role you want. We compare it with your resume, show what's missing, and suggest what to learn next.
      </p>

      {error && <div className="auth-error">{error}</div>}
      {loading && !error && <p className="muted">Loading...</p>}

      {!loading && parsedResumes.length === 0 && (
        <div className="empty-state">
          You need a parsed resume first.{" "}
          <Link to="/resumes" className="back-link">Upload and parse one</Link>.
        </div>
      )}

      {!loading && parsedResumes.length > 0 && (
        <form className="detail-card" onSubmit={run}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
            <label className="parser-choice">
              <span>Resume</span>
              <select value={resumeId} onChange={(e) => setResumeId(e.target.value)} disabled={running}>
                {parsedResumes.map((r) => (
                  <option key={r.id} value={r.id}>{r.filename}</option>
                ))}
              </select>
            </label>
            <label className="parser-choice" style={{ flex: "1 1 260px" }}>
              <span>Target role</span>
              <input
                type="text"
                list="role-suggestions"
                value={role}
                maxLength={80}
                placeholder="e.g. Python Developer"
                onChange={(e) => setRole(e.target.value)}
                disabled={running}
              />
              <datalist id="role-suggestions">
                {roleSuggestions.map((r) => <option key={r} value={r} />)}
              </datalist>
            </label>
            <button className="btn-small btn-filled" type="submit" disabled={running || !resumeId || role.trim().length < 2}>
              {running ? "Analyzing..." : "Find my skill gaps"}
            </button>
          </div>
        </form>
      )}

      {result && (
        <>
          <div className="detail-card">
            <h2 className="section-title">{result.role || result.job_title}</h2>
            <div className="score-ring-row">
              <div className="score-ring">
                <span className="score-number">{result.compatibility}</span>
                <span className="score-max">%</span>
              </div>
              <div>
                <div className="score-grade">{compatibilityLabel(result.compatibility)}</div>
                <div className="muted">
                  {result.matched_count} of {result.total_requirements} skills covered ·{" "}
                  {result.gap_count} {result.gap_count === 1 ? "gap" : "gaps"} found
                </div>
              </div>
            </div>
            {result.role_source === "ai" && (
              <p className="muted" style={{ marginTop: 12 }}>
                The skills for this role were generated by AI. Treat them as a guide, not a rulebook.
              </p>
            )}
            {result.role_source === "built-in" && result.role_matched && (
              <p className="muted" style={{ marginTop: 12 }}>
                Compared against the typical skills for “{result.role_matched}”.
              </p>
            )}
          </div>

          <div className="detail-card">
            <h2 className="section-title">How your resume covers each skill</h2>
            <p className="muted">Green means your resume shows evidence. Red means it's missing or weak.</p>
            <RequirementChart requirements={result.requirements} />
          </div>

          {result.gaps.length === 0 ? (
            <div className="detail-card">
              <h2 className="section-title">No gaps found</h2>
              <p className="muted">Your resume covers every skill we checked for this role.</p>
            </div>
          ) : (
            <div className="detail-card">
              <h2 className="section-title">What to work on</h2>
              {result.gaps.map((gap) => (
                <div key={gap.skill} className="detail-block" style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <strong>{gap.skill}</strong>
                    <PriorityBadge level={gap.priority} />
                    {gap.kind === "preferred" && <span className="muted">nice to have</span>}
                  </div>
                  <p style={{ margin: "8px 0" }}>{gap.explanation}</p>
                  {gap.recommendations.length > 0 ? (
                    <ul>
                      {gap.recommendations.map((rec) => (
                        <li key={rec.id}>
                          <a href={rec.url} target="_blank" rel="noreferrer" className="back-link">
                            {rec.title}
                          </a>{" "}
                          <span className="muted">
                            {rec.provider} · {rec.type} · {rec.level}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">No matching course in the catalog yet.</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {matched.length > 0 && (
            <div className="detail-card">
              <h2 className="section-title">Already covered</h2>
              <div className="tag-row">
                {matched.map((r) => (
                  <span key={r.skill} className="tag" title={r.evidence || ""}>{r.skill}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}