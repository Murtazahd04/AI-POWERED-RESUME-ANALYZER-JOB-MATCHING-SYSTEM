import { useEffect, useState } from "react";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const lakh = (n) => `₹${(n / 100000).toFixed(1)}L`;

function salaryText(job) {
  if (!job.salary_min && !job.salary_max) return null;
  const range =
    job.salary_min && job.salary_max && job.salary_min !== job.salary_max
      ? `${lakh(job.salary_min)} – ${lakh(job.salary_max)}`
      : lakh(job.salary_max || job.salary_min);
  return `${range} per year${job.salary_is_estimate ? " (estimate)" : ""}`;
}

const tone = (score) => (score >= 75 ? "jm-high" : score >= 55 ? "jm-mid" : "jm-low");

function Part({ label, value }) {
  if (value === null || value === undefined) return null;
  return (
    <span className="jm-part">
      {label} <strong>{value}%</strong>
    </span>
  );
}

export default function JobMatchPanel({ resumeId, refreshKey = 0 }) {
  const [data, setData] = useState(null);
  const [where, setWhere] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Resume was re-parsed, so any earlier matches are out of date.
  useEffect(() => {
    setData(null);
    setError("");
  }, [refreshKey, resumeId]);

  async function run(refresh = false) {
    setLoading(true);
    setError("");
    try {
      const result = await resumeApi.jobMatches(resumeId, {
        where: where.trim() || undefined,
        refresh: refresh || undefined,
      });
      setData(result);
    } catch (e) {
      setError(apiErrorMessage(e, "Could not load job matches."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="detail-card">
      <h2 className="section-title">Matching jobs</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Live job postings compared with your resume: skills, job title, seniority and how well your
        experience fits the role.
      </p>

      <div className="jm-controls">
        <input
          className="jm-input"
          value={where}
          onChange={(e) => setWhere(e.target.value)}
          placeholder="City (optional), e.g. Mumbai. Leave empty for all of India"
          maxLength={60}
          onKeyDown={(e) => e.key === "Enter" && !loading && run(false)}
        />
        <button className="btn-small btn-filled" onClick={() => run(false)} disabled={loading}>
          {loading ? "Finding jobs..." : data ? "Search again" : "Find matching jobs"}
        </button>
        {data && !loading && (
          <button className="btn-small" onClick={() => run(true)} title="Ignore saved results and fetch fresh postings">
            Refresh
          </button>
        )}
      </div>

      {loading && <p className="muted">This can take up to 30 seconds while we search and compare postings...</p>}
      {error && <div className="auth-error">{error}</div>}

      {data && (
        <>
          {data.cached && <p className="muted">Showing saved results from earlier. Press Refresh for new postings.</p>}
          {data.warnings?.map((w, i) => (
            <p key={i} className="jm-warning">{w}</p>
          ))}
          {data.jobs.length === 0 && !data.warnings?.length && <p className="muted">No matching jobs found.</p>}

          {data.jobs.map((job) => {
            const salary = salaryText(job);
            return (
              <div key={job.id} className="jm-card">
                <div className="jm-head">
                  <div>
                    <div className="jm-title">{job.title}</div>
                    <div className="muted">
                      {job.company} · {job.location}
                    </div>
                    {salary && <div className="muted">{salary}</div>}
                  </div>
                  <div className={`jm-score ${tone(job.match.score)}`}>
                    {job.match.score}%<span>match</span>
                  </div>
                </div>

                <div className="jm-parts">
                  <Part label="Skills" value={job.match.skills} />
                  <Part label="Title" value={job.match.title} />
                  <Part label="Seniority fit" value={job.match.level_fit} />
                  <Part label="Context" value={job.match.context} />
                </div>

                {job.why_it_fits && <p className="jm-why">{job.why_it_fits}</p>}

                {job.matched_skills.length > 0 && (
                  <div>
                    <div className="jm-label">Skills you have</div>
                    <div className="tag-row">
                      {job.matched_skills.map((s) => (
                        <span key={s} className="tag jm-have">{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {job.missing_skills.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div className="jm-label">Skills to add</div>
                    <div className="tag-row">
                      {job.missing_skills.map((s) => (
                        <span key={s} className="tag jm-miss">{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {job.improvements.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div className="jm-label">How to improve for this role</div>
                    <ul className="jm-list">
                      {job.improvements.map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {job.url && /^https?:\/\//.test(job.url) && (
                  <a className="btn-small" style={{ marginTop: 12 }} href={job.url} target="_blank" rel="noreferrer">
                    View job →
                  </a>
                )}
              </div>
            );
          })}

          <p className="muted" style={{ fontSize: "0.8rem" }}>
            Postings come from Adzuna and descriptions are often cut short, so scores are estimates.
            {data.ai_used ? " Context matching and advice were written by AI." : " Context matching by AI was not used."}
          </p>
        </>
      )}
    </div>
  );
}