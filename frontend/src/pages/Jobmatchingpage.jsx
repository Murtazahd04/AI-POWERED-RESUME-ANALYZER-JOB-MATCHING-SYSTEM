import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import JobMatchPanel from "../components/JobMatchPanel";

export default function JobMatchingPage() {
  const [resumes, setResumes] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    resumeApi
      .list()
      .then((list) => {
        setResumes(list);
        // Start with the newest resume that has been parsed (the list is newest first).
        const firstParsed = list.find((r) => r.parsed);
        if (firstParsed) setSelectedId(firstParsed.id);
      })
      .catch((e) => setError(apiErrorMessage(e)));
  }, []);

  const selected = resumes?.find((r) => r.id === selectedId);

  return (
    <div className="app-page">
      <h1 className="page-title">Job Matching</h1>
      <p className="page-subtitle">
        Pick a resume and we'll find the 5 best-matching jobs, with advice on how to improve for each role.
      </p>

      {error && <div className="auth-error">{error}</div>}
      {resumes === null && !error && <p className="muted">Loading...</p>}

      {resumes?.length === 0 && (
        <div className="empty-state">
          No resumes yet. <Link to="/resumes" className="back-link">Upload your first one</Link> to find matching jobs.
        </div>
      )}

      {resumes?.length > 0 && (
        <>
          <label className="parser-choice">
            <span>Resume</span>
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.filename}
                  {r.parsed ? "" : " (not parsed)"}
                </option>
              ))}
            </select>
          </label>

          {selected && !selected.parsed && (
            <div className="detail-card" style={{ marginTop: 16 }}>
              This resume hasn't been parsed yet, so there is nothing to match.{" "}
              <Link to={`/resumes/${selected.id}`} className="back-link">Open it and parse it first</Link>.
            </div>
          )}

          {selected?.parsed && (
            <div style={{ marginTop: 16 }}>
              <JobMatchPanel key={selected.id} resumeId={selected.id} />
            </div>
          )}
        </>
      )}
    </div>
  );
}