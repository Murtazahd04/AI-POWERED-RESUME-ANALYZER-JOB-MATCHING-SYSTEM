import { useEffect, useId, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { resumeApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const emptyParsed = () => ({
  name: "",
  contact: { email: "", phone: "", linkedin: "", github: "" },
  summary: "",
  education: [],
  experience: [],
  total_experience_years: 0,
  projects: [],
  certifications: [],
  skills: { technical: [], soft: [] },
});

function makeDraft(parsed) {
  const empty = emptyParsed();
  return {
    ...empty,
    ...parsed,
    contact: { ...empty.contact, ...parsed.contact },
    education: (parsed.education ?? []).map((item) => ({
      degree: "",
      institution: "",
      year: "",
      ...item,
    })),
    experience: (parsed.experience ?? []).map((item) => ({
      title: "",
      date_range: "",
      highlights: [],
      technologies: [],
      ...item,
    })),
    projects: (parsed.projects ?? []).map((item) => ({
      name: "",
      description: [],
      technologies: [],
      ...item,
    })),
    certifications: parsed.certifications ?? [],
    skills: { ...empty.skills, ...parsed.skills },
  };
}

function textToLines(value) {
  return value.split("\n");
}

function cleanLines(lines) {
  return lines
    .map((line) => line.trim().replace(/^[•●▪■◦○‣∙·*-]\s*/, ""))
    .filter(Boolean);
}

const analysisSections = [
  { key: "summary", title: "AI resume summary", suggestionSection: "Summary" },
  { key: "strengths", title: "Resume strengths", suggestionSection: "Strengths" },
  { key: "weaknesses", title: "Resume weaknesses", suggestionSection: "Weaknesses" },
  { key: "formatting", title: "Formatting & clarity", suggestionSection: "Formatting & clarity" },
  { key: "general", title: "General improvements", suggestionSection: "General" },
];

const resumeSectionAnalysis = {
  skills: { title: "Skills", suggestionSection: "Skills" },
  experience: { title: "Experience", suggestionSection: "Experience" },
  education: { title: "Education", suggestionSection: "Education" },
  certifications: { title: "Certifications", suggestionSection: "Certifications" },
  projects: { title: "Projects", suggestionSection: "Projects" },
};

function AnalysisResult({ section, result }) {
  if (section === "summary") return <p>{result}</p>;
  if (section === "skills") {
    return (
      <>
        <h4>Identified skills</h4>
        {result.identified_skills?.length
          ? <div className="tag-row">{result.identified_skills.map((skill, index) => <span key={`${skill}-${index}`} className="tag">{skill}</span>)}</div>
          : <p className="muted">No skills could be identified from the resume.</p>}
        <h4>Strengths</h4>
        {result.strengths?.length ? <ul>{result.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No supported skill strengths were identified.</p>}
        <h4>Gaps / missing evidence</h4>
        {result.gaps?.length ? <ul>{result.gaps.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No missing skill evidence was identified.</p>}
      </>
    );
  }
  if (section === "experience") {
    return (
      <>
        <p>{result.assessment}</p>
        <h4>Relevant strengths</h4>
        {result.relevant_strengths?.length ? <ul>{result.relevant_strengths.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No supported experience strengths were identified.</p>}
        <h4>Gaps / missing evidence</h4>
        {result.gaps?.length ? <ul>{result.gaps.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No missing experience evidence was identified.</p>}
      </>
    );
  }
  if (section === "education") {
    return (
      <>
        <p>{result.assessment}</p>
        <h4>Relevant details</h4>
        {result.relevant_details?.length ? <ul>{result.relevant_details.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No additional education details were identified.</p>}
      </>
    );
  }
  if (section === "certifications") {
    return (
      <>
        <p>{result.assessment}</p>
        <h4>Relevant details</h4>
        {result.relevant_details?.length ? <ul>{result.relevant_details.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No certification details were identified.</p>}
      </>
    );
  }
  if (section === "projects") {
    return (
      <>
        <p>{result.assessment}</p>
        <h4>Project and technology highlights</h4>
        {result.project_highlights?.length ? <ul>{result.project_highlights.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No project highlights could be supported by the resume details.</p>}
      </>
    );
  }
  if (section === "strengths" || section === "weaknesses") {
    const items = result ?? [];
    return items.length
      ? <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul>
      : <p className="muted">No specific {section} could be supported by the resume details.</p>;
  }
  return null;
}

function SectionAnalysisToggles({
  section,
  suggestionSection,
  result,
  suggestions,
  openAnalysis,
  setOpenAnalysis,
  openImprovements,
  setOpenImprovements,
  showEmptyAnalysis = false,
}) {
  const sectionSuggestions = suggestions.filter((item) => item.section === suggestionSection);
  const analysisId = `analysis-${section}`;
  const improvementsId = `improvements-${section}`;
  const hasAnalysis = result !== undefined && result !== null;

  return (
    <>
      <div className="analysis-toggle-row">
        {(hasAnalysis || showEmptyAnalysis) && (
          <button
            type="button"
            className="btn-small"
            aria-expanded={Boolean(openAnalysis[section])}
            aria-controls={analysisId}
            onClick={() => setOpenAnalysis((current) => ({
              ...current,
              [section]: !current[section],
            }))}
          >
            {openAnalysis[section] ? "Hide AI analysis" : "Show AI analysis"}
          </button>
        )}
        {suggestionSection && (
          <button
            type="button"
            className="btn-small"
            aria-expanded={Boolean(openImprovements[section])}
            aria-controls={improvementsId}
            onClick={() => setOpenImprovements((current) => ({
              ...current,
              [section]: !current[section],
            }))}
          >
            {openImprovements[section] ? "Hide improvements" : "Show improvements"}
          </button>
        )}
      </div>
      {(hasAnalysis || showEmptyAnalysis) && (
        <div id={analysisId} hidden={!openAnalysis[section]}>
          {hasAnalysis
            ? <AnalysisResult section={section} result={result} />
            : <p className="muted">Run "Analyze my resume" to generate this section's AI analysis.</p>}
        </div>
      )}
      {suggestionSection && (
        <div id={improvementsId} hidden={!openImprovements[section]}>
          {sectionSuggestions.length ? (
            <ul className="suggestion-list">
              {sectionSuggestions.map((item, index) => (
                <li key={`${section}-${index}`}>
                  <strong>{item.priority.toUpperCase()}:</strong> {item.suggestion}
                  <div className="muted">{item.reason}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No specific improvements were identified for this section.</p>
          )}
        </div>
      )}
    </>
  );
}

function Field({ label, value, onChange, type = "text", ...props }) {
  return (
    <label className="editor-field">
      <span>{label}</span>
      <input
        type={type}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function TextAreaField({ label, value, onChange, rows = 3, addBullet = false }) {
  const id = useId();
  const textareaRef = useRef(null);

  function insertBullet() {
    const textarea = textareaRef.current;
    const start = textarea?.selectionStart ?? value.length;
    const end = textarea?.selectionEnd ?? value.length;
    const before = value.slice(0, start);
    const after = value.slice(end);
    const prefix = before && !before.endsWith("\n") ? "\n" : "";
    const insertion = `${prefix}• `;
    const nextValue = `${before}${insertion}${after}`;
    const cursor = before.length + insertion.length;
    onChange(nextValue);
    requestAnimationFrame(() => {
      textarea?.focus();
      textarea?.setSelectionRange(cursor, cursor);
    });
  }

  return (
    <div className="editor-field">
      <div className="editor-field-heading">
        <label htmlFor={id}>{label}</label>
        {addBullet && (
          <button className="btn-small" type="button" onClick={insertBullet}>
            Add bullet
          </button>
        )}
      </div>
      <textarea
        id={id}
        ref={textareaRef}
        rows={rows}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

export default function ResumeDetailPage() {
  const { id } = useParams();
  const [resume, setResume] = useState(null);
  const [draft, setDraft] = useState(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [parserChoice, setParserChoice] = useState("");
  const [analyzingResume, setAnalyzingResume] = useState(false);
  const [resumeAnalysis, setResumeAnalysis] = useState(null);
  const [openAnalysis, setOpenAnalysis] = useState({});
  const [openImprovements, setOpenImprovements] = useState({});
   
  // --- NEW: which tab is showing ---
const [tab, setTab] = useState("details");

  useEffect(() => {
    resumeApi.get(id).then((data) => {
      setResume(data);
      if (data.parser_used) {
        setParserChoice(data.parser_used);
      }
      const saved = data.ai_results ?? {};
      const legacyResult = {
        skills_analysis: saved.skills?.result,
        experience_analysis: saved.experience?.result,
        education_analysis: saved.education?.result,
        project_analysis: saved.projects?.result,
        strengths: saved.strengths?.result?.strengths,
        weaknesses: saved.weaknesses?.result?.weaknesses,
        summary: saved.summary?.result?.summary,
        improvement_suggestions: saved.improvement_suggestions?.result?.suggestions ?? [],
      };
      const hasLegacyAnalysis = [
        "skills",
        "experience",
        "education",
        "projects",
        "strengths",
        "weaknesses",
        "summary",
        "improvement_suggestions",
      ].some((key) => saved[key]);
      setResumeAnalysis(saved.full_resume?.result ?? (
        hasLegacyAnalysis ? legacyResult : null
      ));
    }).catch((e) => setError(apiErrorMessage(e)));
  }, [id]);

  
  function beginEdit() {
    setDraft(makeDraft(resume.parsed));
    setEditing(true);
    setError("");
    setNotice("");
  }

  function cancelEdit() {
    setDraft(null);
    setEditing(false);
    setError("");
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function updateNestedDraft(section, field, value) {
    setDraft((current) => ({
      ...current,
      [section]: { ...current[section], [field]: value },
    }));
  }

  function updateItem(section, index, field, value) {
    setDraft((current) => ({
      ...current,
      [section]: current[section].map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item
      ),
    }));
  }

  function addItem(section, item) {
    setDraft((current) => ({ ...current, [section]: [...current[section], item] }));
  }

  function removeItem(section, index) {
    setDraft((current) => ({
      ...current,
      [section]: current[section].filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  async function saveEdit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const payload = {
      ...draft,
      name: String(draft.name ?? "").trim() || null,
      contact: Object.fromEntries(
        Object.entries(draft.contact).map(([key, value]) => [
          key,
          String(value ?? "").trim() || null,
        ])
      ),
      summary: String(draft.summary ?? "").trim() || null,
      skills: {
        technical: cleanLines(draft.skills.technical),
        soft: cleanLines(draft.skills.soft),
      },
      education: draft.education.map((item) => ({
        degree: String(item.degree ?? "").trim() || null,
        institution: String(item.institution ?? "").trim() || null,
        year: String(item.year ?? "").trim() || null,
      })),
      experience: draft.experience.map((item) => ({
        ...item,
        title: String(item.title ?? "").trim() || null,
        date_range: String(item.date_range ?? "").trim(),
        highlights: cleanLines(item.highlights),
        technologies: cleanLines(item.technologies),
      })),
      projects: draft.projects.map((item) => ({
        ...item,
        name: String(item.name ?? "").trim(),
        description: cleanLines(item.description),
        technologies: cleanLines(item.technologies),
      })),
      certifications: cleanLines(draft.certifications),
    };

    try {
      const result = await resumeApi.saveParsed(id, payload);
      setResume((current) => ({ ...current, parsed: result.parsed, ai_results: {} }));
      setResumeAnalysis(null);
      setOpenAnalysis({});
      setOpenImprovements({});
      setDraft(null);
      setEditing(false);
      setNotice("Resume details saved.");
    } catch (e) {
      setError(apiErrorMessage(e, "Couldn't save the resume details."));
    } finally {
      setBusy(false);
    }
  }

  async function reparse() {
    if (!parserChoice) {
      setError("Choose AI parsing or spaCy parsing before reparsing.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await resumeApi.reparse(id, parserChoice);
      setResume((current) => ({
        ...current,
        parsed: data.parsed,
        parser_used: data.parser_used,
        parsed_at: data.parsed_at,
        ai_results: {},
      }));
      setResumeAnalysis(null);
      setOpenAnalysis({});
      setOpenImprovements({});
      setNotice(`Resume successfully re-parsed using ${data.parser_used === "ai" ? "AI" : "spaCy"}. Stale AI analysis results have been cleared.`);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function analyzeResume() {
    setAnalyzingResume(true);
    setError("");
    setNotice("");
    try {
      const data = await resumeApi.analyzeResume(id);
      setResumeAnalysis(data.analysis.result);
      setResume((current) => ({
        ...current,
        ai_results: {
          ...current.ai_results,
          full_resume: {
            result: data.analysis.result,
            generated_at: data.analysis.generated_at,
          },
        },
      }));
      setOpenAnalysis({});
      setOpenImprovements({});
      setTab("ai");
    } catch (e) {
      setError(apiErrorMessage(e, "Couldn't analyze the resume."));
    } finally {
      setAnalyzingResume(false);
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
        <ParserChoice value={parserChoice} onChange={setParserChoice} disabled={busy} />
        <button onClick={reparse} disabled={busy || !parserChoice}>
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
        {resume.parser_used && (
          <> · Parsed with {resume.parser_used === "ai" ? "AI" : "spaCy"}{resume.parsed_at ? ` on ${new Date(resume.parsed_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })}` : ""}</>
        )}
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <a href={resume.file_url} target="_blank" rel="noreferrer" className="btn-small">View original</a>
        {!editing && (
          <>
            <button className="btn-small" onClick={beginEdit} disabled={busy}>Edit details</button>
            <button className="btn-small btn-filled" onClick={analyzeResume} disabled={analyzingResume || busy}>
              {analyzingResume ? "Analyzing your resume..." : "Analyze my resume"}
            </button>
            <ParserChoice value={parserChoice} onChange={setParserChoice} disabled={busy} compact />
            <button className="btn-small" onClick={reparse} disabled={busy || !parserChoice}>
              {busy ? "Parsing..." : "Re-parse"}
            </button>
          </>
        )}
      </div>
      {error && <div className="auth-error">{error}</div>}
      {notice && <div className="auth-success">{notice}</div>}

      {editing ? (
        <form onSubmit={saveEdit}>
          <div className="detail-card">
            <h2 className="section-title">Edit resume details</h2>
            <div className="editor-grid">
              <Field label="Name" value={draft.name} onChange={(value) => updateDraft("name", value)} />
              <Field
                label="Years of experience"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={draft.total_experience_years}
                onChange={(value) => updateDraft("total_experience_years", Number(value))}
              />
              <Field label="Email" type="email" value={draft.contact.email}
                onChange={(value) => updateNestedDraft("contact", "email", value)} />
              <Field label="Phone" value={draft.contact.phone}
                onChange={(value) => updateNestedDraft("contact", "phone", value)} />
              <Field label="LinkedIn URL" value={draft.contact.linkedin}
                onChange={(value) => updateNestedDraft("contact", "linkedin", value)} />
              <Field label="GitHub URL" value={draft.contact.github}
                onChange={(value) => updateNestedDraft("contact", "github", value)} />
            </div>
            <TextAreaField label="Summary" value={draft.summary}
              onChange={(value) => updateDraft("summary", value)} />
          </div>

          <div className="detail-card">
            <h2 className="section-title">Skills</h2>
            <div className="editor-grid">
              <TextAreaField label="Technical skills (one per line)" rows={5}
                value={draft.skills.technical.join("\n")}
                onChange={(value) => updateNestedDraft("skills", "technical", textToLines(value))} />
              <TextAreaField label="Soft skills (one per line)" rows={5}
                value={draft.skills.soft.join("\n")}
                onChange={(value) => updateNestedDraft("skills", "soft", textToLines(value))} />
            </div>
          </div>

          <div className="detail-card">
            <h2 className="section-title">Experience</h2>
            {draft.experience.map((item, index) => (
              <div className="editor-item" key={index}>
                <div className="editor-grid">
                  <Field label="Role / title" value={item.title}
                    onChange={(value) => updateItem("experience", index, "title", value)} />
                  <Field label="Date range" value={item.date_range}
                    onChange={(value) => updateItem("experience", index, "date_range", value)} />
                </div>
                <TextAreaField label="Highlights (one per line)" rows={4} addBullet
                  value={item.highlights.join("\n")}
                  onChange={(value) => updateItem("experience", index, "highlights", textToLines(value))} />
                <TextAreaField label="Technologies (one per line)"
                  value={item.technologies.join("\n")}
                  onChange={(value) => updateItem("experience", index, "technologies", textToLines(value))} />
                <button className="btn-small btn-danger" type="button"
                  onClick={() => removeItem("experience", index)}>Remove experience</button>
              </div>
            ))}
            <button className="btn-small" type="button" onClick={() => addItem("experience", {
              title: "", date_range: "", highlights: [], technologies: [],
            })}>Add experience</button>
          </div>

          <div className="detail-card">
            <h2 className="section-title">Education</h2>
            {draft.education.map((item, index) => (
              <div className="editor-item" key={index}>
                <div className="editor-grid">
                  <Field label="Degree" value={item.degree}
                    onChange={(value) => updateItem("education", index, "degree", value)} />
                  <Field label="Institution" value={item.institution}
                    onChange={(value) => updateItem("education", index, "institution", value)} />
                  <Field label="Year" value={item.year}
                    onChange={(value) => updateItem("education", index, "year", value)} />
                </div>
                <button className="btn-small btn-danger" type="button"
                  onClick={() => removeItem("education", index)}>Remove education</button>
              </div>
            ))}
            <button className="btn-small" type="button"
              onClick={() => addItem("education", { degree: "", institution: "", year: "" })}>
              Add education
            </button>
          </div>

          <div className="detail-card">
            <h2 className="section-title">Projects</h2>
            {draft.projects.map((item, index) => (
              <div className="editor-item" key={index}>
                <Field label="Project name" required value={item.name}
                  onChange={(value) => updateItem("projects", index, "name", value)} />
                <TextAreaField label="Description (one per line)" rows={4} addBullet
                  value={item.description.join("\n")}
                  onChange={(value) => updateItem("projects", index, "description", textToLines(value))} />
                <TextAreaField label="Technologies (one per line)"
                  value={item.technologies.join("\n")}
                  onChange={(value) => updateItem("projects", index, "technologies", textToLines(value))} />
                <button className="btn-small btn-danger" type="button"
                  onClick={() => removeItem("projects", index)}>Remove project</button>
              </div>
            ))}
            <button className="btn-small" type="button"
              onClick={() => addItem("projects", { name: "", description: [], technologies: [] })}>
              Add project
            </button>
          </div>

          <div className="detail-card">
            <h2 className="section-title">Certifications</h2>
            <TextAreaField label="Certifications (one per line)" rows={5} addBullet
              value={draft.certifications.join("\n")}
              onChange={(value) => updateDraft("certifications", textToLines(value))} />
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
            <button className="btn-small btn-filled" type="submit" disabled={busy}>
              {busy ? "Saving..." : "Save changes"}
            </button>
            <button className="btn-small" type="button" onClick={cancelEdit} disabled={busy}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          {/* ---------- TAB BAR ---------- */}
          <div className="tab-bar">
            <button className={`tab-btn ${tab === "details" ? "tab-btn-active" : ""}`} onClick={() => setTab("details")}>
              Resume details
            </button>

            <button className={`tab-btn ${tab === "ai" ? "tab-btn-active" : ""}`} onClick={() => setTab("ai")}>
              AI analysis {resumeAnalysis && <span className="tab-dot" />}
            </button>
          </div>

          {/* ---------- TAB: Resume details ---------- */}
          {tab === "details" && (
            <>
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
                  {[...technical, ...soft].map((skill, index) => (
                    <span key={`${skill}-${index}`} className="tag">{skill}</span>
                  ))}
                  {technical.length + soft.length === 0 && <span className="muted">No skills detected.</span>}
                </div>
              </div>

              <div className="detail-card">
                <h2 className="section-title">Experience</h2>
                {experience.length === 0 && <p className="muted">No experience detected.</p>}
                {experience.map((item, index) => (
                  <div key={index} className="detail-block">
                    <strong>{item.title || "Role"}</strong> <span className="muted">({item.date_range})</span>
                    <ul>{(item.highlights ?? []).map((highlight, i) => <li key={i}>{highlight}</li>)}</ul>
                  </div>
                ))}
              </div>

              <div className="detail-card">
                <h2 className="section-title">Education</h2>
                {education.length === 0 && <p className="muted">No education detected.</p>}
                {education.map((item, index) => (
                  <div key={index} className="detail-block">
                    <strong>{item.degree}</strong>
                    <div className="muted">{[item.institution, item.year].filter(Boolean).join(" · ")}</div>
                  </div>
                ))}
              </div>

              <div className="detail-card">
                <h2 className="section-title">Projects</h2>
                {projects.length === 0 && <p className="muted">No projects detected.</p>}
                {projects.map((project, index) => (
                  <div key={index} className="detail-block">
                    <strong>{project.name}</strong>
                    {(project.description ?? []).map((description, i) => (
                      <p key={i} style={{ margin: "4px 0" }}>{description}</p>
                    ))}
                    <div className="tag-row">
                      {(project.technologies ?? []).map((technology, i) => (
                        <span key={`${technology}-${i}`} className="tag">{technology}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="detail-card">
                <h2 className="section-title">Certifications</h2>
                {certifications.length === 0 && <p className="muted">None detected.</p>}
                <ul>{certifications.map((certification, index) => <li key={index}>{certification}</li>)}</ul>
              </div>
            </>
          )}

           
          {tab === "score" && (
            <div className="detail-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2 className="section-title" style={{ margin: 0 }}>Resume score</h2>
                <button className="btn-small btn-filled" onClick={runScore} disabled={scoring}>
                  {scoring ? "Scoring..." : resume.score ? "Recompute" : "Compute score"}
                </button>
              </div>
              {scoreError && <div className="auth-error" style={{ marginTop: 12 }}>{scoreError}</div>}

              {resume.score ? (
                <>
                  <div className="score-ring-row">
                    <div className="score-ring">
                      <span className="score-number">{resume.score.overall}</span>
                      <span className="score-max">/100</span>
                    </div>
                    <div>
                      <div className="score-grade">{resume.score.grade}</div>
                      <div className="muted">{resume.score.summary}</div>
                    </div>
                  </div>

                  <div className="score-bars">
                    {Object.entries(resume.score.components).map(([key, c]) => (
                      <div key={key} className="score-bar-row">
                        <div className="score-bar-label">
                          <span style={{ textTransform: "capitalize" }}>{key}</span>
                          <span>{c.score}/100</span>
                        </div>
                        <div className="progress-track">
                          <div className="progress-fill" style={{ width: `${c.score}%` }} />
                        </div>
                      </div>
                    ))}
                    <div className="score-bar-row">
                      <div className="score-bar-label">
                        <span>ATS compatibility</span>
                        <span>{resume.score.ats.score}/100</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${resume.score.ats.score}%` }} />
                      </div>
                    </div>
                  </div>

                
                </>
              ) : (
                <p className="muted" style={{ marginTop: 16 }}>Click "Compute score" to see your resume's score breakdown.</p>
              )}
            </div>
          )}

          {/* ---------- TAB: AI analysis ---------- */}
          {tab === "ai" && (
            <div className="detail-card" aria-live="polite">
              <h2 className="section-title">AI resume analysis</h2>
              <p className="muted">
                Run one evidence-based analysis for every resume section and its improvement suggestions.
              </p>
              {resumeAnalysis && (
                <p className="muted">Your latest analysis is saved and will be available when you return.</p>
              )}
              {!resumeAnalysis && (
                <p className="muted">Click "Analyze my resume" above to generate the section analyses and improvement suggestions.</p>
              )}
              {resumeAnalysis && analysisSections.map(({ key, title, suggestionSection }) => {
                const result = resumeAnalysis[key];
                return (
                  <section className="analysis-section" key={key}>
                    <h3>{title}</h3>
                    <SectionAnalysisToggles
                      section={key}
                      suggestionSection={suggestionSection}
                      result={result}
                      suggestions={resumeAnalysis.improvement_suggestions ?? []}
                      openAnalysis={openAnalysis}
                      setOpenAnalysis={setOpenAnalysis}
                      openImprovements={openImprovements}
                      setOpenImprovements={setOpenImprovements}
                    />
                  </section>
                );
              })}
              {resumeAnalysis && (
                <>
                  {Object.entries(resumeSectionAnalysis).map(([key, { title, suggestionSection }]) => {
                    const resultKey = key === "skills" ? "skills_analysis"
                      : key === "experience" ? "experience_analysis"
                      : key === "education" ? "education_analysis"
                      : key === "certifications" ? "certification_analysis"
                      : "project_analysis";
                    const result = resumeAnalysis[resultKey];
                    if (!result) return null;
                    return (
                      <section className="analysis-section" key={key}>
                        <h3>{title} analysis</h3>
                        <SectionAnalysisToggles
                          section={key}
                          suggestionSection={suggestionSection}
                          result={result}
                          suggestions={resumeAnalysis.improvement_suggestions ?? []}
                          openAnalysis={openAnalysis}
                          setOpenAnalysis={setOpenAnalysis}
                          openImprovements={openImprovements}
                          setOpenImprovements={setOpenImprovements}
                        />
                      </section>
                    );
                  })}
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ParserChoice({ value, onChange, disabled, compact = false }) {
  return <label className={compact ? "parser-choice parser-choice-compact" : "parser-choice"}>
    <span>{compact ? "Parser" : "Choose a parser"}</span>
    <select value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
      <option value="">Select…</option>
      <option value="ai">AI parsing</option>
      <option value="spacy">spaCy parsing</option>
    </select>
  </label>;
}