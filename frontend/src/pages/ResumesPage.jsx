import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const MAX_MB = 5;

function formatSize(bytes) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const load = () =>
    resumeApi.list().then(setResumes).catch((e) => setError(apiErrorMessage(e)));

  useEffect(() => {
    load();
  }, []);

  const upload = async (file) => {
    setError("");
    setSuccess("");
    if (!file) return;

    const name = file.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setError("Only PDF and DOCX files are supported.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File is too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }

    setUploading(true);
    setProgress(0);
    try {
      await resumeApi.upload(file, setProgress);
      setSuccess(`"${file.name}" uploaded successfully.`);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "Upload failed. Please try again."));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    upload(e.dataTransfer.files[0]);
  };

  const remove = async (resume) => {
    if (!window.confirm(`Delete "${resume.filename}"? This can't be undone.`)) return;
    setError("");
    setSuccess("");
    try {
      await resumeApi.remove(resume.id);
      setSuccess("Resume deleted.");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "Couldn't delete this resume."));
    }
  };

  return (
    <div className="app-page">
      <Link to="/dashboard" className="back-link">← Back to dashboard</Link>
      <h1 className="page-title">My resumes</h1>
      <p className="page-subtitle">Upload a PDF or DOCX resume (max {MAX_MB} MB).</p>

      {error && <div className="auth-error">{error}</div>}
      {success && <div className="auth-success">{success}</div>}

      <div
        className={`dropzone ${dragging ? "dropzone-active" : ""}`}
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          hidden
          onChange={(e) => upload(e.target.files[0])}
        />
        {uploading ? (
          <>
            <div className="dropzone-title">Uploading... {progress}%</div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </>
        ) : (
          <>
            <div className="dropzone-title">
              {dragging ? "Drop it here" : "Drag a resume here, or click to browse"}
            </div>
            <div className="dropzone-hint">PDF or DOCX, up to {MAX_MB} MB</div>
          </>
        )}
      </div>

      <h2 className="section-title">Upload history</h2>
      {resumes === null && <p className="muted">Loading...</p>}
      {resumes?.length === 0 && (
        <div className="empty-state">No resumes yet. Upload your first one above.</div>
      )}

      {resumes?.map((r) => (
        <div key={r.id} className="resume-row">
          <div className="resume-info">
            <div className="resume-name">{r.filename}</div>
            <div className="resume-meta">
              {r.file_type.toUpperCase()} · {formatSize(r.size_bytes)} · uploaded{" "}
              {new Date(r.uploaded_at).toLocaleDateString()}
            </div>
          </div>
          <a className="btn-small" href={r.file_url} target="_blank" rel="noreferrer">
            View
          </a>
          <button className="btn-small btn-danger" onClick={() => remove(r)}>
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}