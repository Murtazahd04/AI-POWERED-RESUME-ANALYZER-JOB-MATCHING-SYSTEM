"""Turns a raw resume file into structured data: name, contact info, education,
work experience, projects, certifications and skills."""
import io
import re
import unicodedata
from datetime import date
from functools import lru_cache

from ..skills_data import SKILL_PATTERNS, SOFT_CATEGORY


class ParseError(Exception):
    """Raised when a file's text genuinely can't be read (corrupted, password-protected, etc.)."""


@lru_cache(maxsize=1)
def _load_nlp():
    try:
        import spacy
    except ModuleNotFoundError as exc:
        raise ParseError("spaCy is required to parse resumes. Install the backend requirements.") from exc
    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:
        raise ParseError(
            "The spaCy English model is missing. Install it with "
            "`python -m spacy download en_core_web_sm`."
        ) from exc


# ---------- 1. Get raw text out of the file ----------
def extract_text(data: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return _pdf_text(data)
    if file_type == "docx":
        return _docx_text(data)
    raise ParseError(f"Unsupported file type: {file_type}")


def _pdf_text(data: bytes) -> str:
    import pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [(page.extract_text() or "") for page in pdf.pages]
            # A resume often shows a clickable word like "LinkedIn" or "GitHub"
            # instead of the actual URL - the real address only lives in the
            # PDF's hyperlink target, which extract_text() above can't see.
            # Pull those out separately so contact extraction can still find them.
            links = [
                link["uri"]
                for page in pdf.pages
                for link in (getattr(page, "hyperlinks", None) or [])
                if link.get("uri")
            ]
    except Exception as exc:
        raise ParseError("This PDF could not be read. It may be corrupted or password-protected.") from exc
    if links:
        pages.append("Links\n" + "\n".join(links))
    return "\n".join(pages)


def _docx_text(data: bytes) -> str:
    from docx import Document
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise ParseError("This DOCX file could not be read. It may be corrupted.") from exc
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
    return "\n".join(lines)


# ---------- 2. Clean the text up ----------
_BULLET_LEAD = re.compile(r"^\s*[•●▪■◦○‣∙·*]\s*")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    lines = []
    for line in text.splitlines():
        line = _BULLET_LEAD.sub("- ", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ---------- 3. Split into sections (Experience, Education, etc.) ----------
SECTION_ALIASES = {
    "summary": ["summary", "profile", "objective", "about me", "professional summary"],
    "experience": ["experience", "work experience", "employment history", "internships",
                   "internship experience", "professional experience", "relevant experience"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "key skills", "core competencies"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "courses"],
    "links": ["links", "profiles", "contact links"],
}
_HEADING_LOOKUP = {a: sec for sec, aliases in SECTION_ALIASES.items() for a in aliases}


def _heading_of(line: str) -> str | None:
    if not line or len(line) > 40 or line.startswith("- "):
        return None
    clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
    if not clean:
        return None
    # Exact match first (e.g. "experience")
    if clean in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[clean]
    # Then allow a known alias to appear anywhere in the heading
    # (e.g. "internship experience" contains "experience")
    for alias, sec in sorted(_HEADING_LOOKUP.items(), key=lambda kv: -len(kv[0])):
        if alias in clean:
            return sec
    return None


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        heading = _heading_of(line.strip())
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


# ---------- 4. Contact info ----------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s\-.]?)?\(?\d{2,5}\)?[\s\-.]?\d{3,5}[\s\-.]?\d{0,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9\-_%]+/?", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+", re.I)
_NON_NAME = {"resume", "cv", "curriculum", "vitae", "profile"}


def extract_name(header_lines: list[str], nlp) -> str | None:
    for line in header_lines[:8]:
        line = line.strip()
        if not line or EMAIL_RE.search(line) or re.search(r"\d", line):
            continue
        words = line.replace("|", " ").split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            if not any(w.lower() in _NON_NAME for w in words):
                return line.title() if line.isupper() else line
    header_doc = nlp("\n".join(header_lines[:8]))
    for entity in header_doc.ents:
        if entity.label_ == "PERSON":
            return entity.text.strip()
    return None


def extract_contact(text: str) -> dict:
    email = EMAIL_RE.search(text)
    linkedin = LINKEDIN_RE.search(text)
    github = GITHUB_RE.search(text)
    phone = None
    for m in PHONE_RE.finditer(text[:800]):
        digits = re.sub(r"\D", "", m.group())
        if 10 <= len(digits) <= 13:
            phone = m.group().strip()
            break
    return {
        "email": email.group().lower() if email else None,
        "phone": phone,
        "linkedin": linkedin.group() if linkedin else None,
        "github": github.group() if github else None,
    }


# ---------- 5. Dates (for calculating years of experience) ----------
_MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
_DATE = rf"(?:{_MONTHS}\.?\s*'?\d{{2,4}}|(?:19|20)\d{{2}})"
_PRESENT = r"(?:present|current|ongoing|till date)"
DATE_RANGE = re.compile(rf"({_DATE})\s*(?:-|–|to)\s*({_DATE}|{_PRESENT})", re.I)
_MONTH_NUM = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _month_index(token: str) -> int | None:
    token = token.strip().lower()
    if re.fullmatch(_PRESENT, token):
        today = date.today()
        return today.year * 12 + today.month
    name = re.match(_MONTHS, token)
    month = _MONTH_NUM[name.group()[:3]] if name else 1
    year_match = re.search(r"(?:19|20)\d{2}", token)
    if not year_match:
        return None
    return int(year_match.group()) * 12 + month


def _total_months(spans: list[tuple[int, int]]) -> int:
    total, cur_start, cur_end = 0, None, None
    for s, e in sorted(spans):
        if cur_end is None or s > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = s, e
        else:
            cur_end = max(cur_end, e)
    if cur_end is not None:
        total += cur_end - cur_start
    return total


# ---------- 6. Skills ----------
def find_skills(text: str) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for canon, cat, pattern in SKILL_PATTERNS:
        if canon not in found and pattern.search(text):
            found[canon] = cat
    return list(found.items())


def extract_skills(text: str) -> dict:
    found = dict(find_skills(text))
    technical = [n for n, c in found.items() if c != SOFT_CATEGORY]
    soft = [n for n, c in found.items() if c == SOFT_CATEGORY]
    return {"technical": technical, "soft": soft}


# ---------- 7. Experience ----------
_TITLE_WORDS = re.compile(
    r"\b(engineer|developer|intern|analyst|manager|consultant|lead|architect|scientist|designer|"
    r"associate|trainee|administrator|specialist|executive)\b", re.I)


def parse_experience(lines: list[str]) -> tuple[list[dict], float]:
    lines = [l.strip() for l in lines if l.strip()]

    # A "header" line is one that names a role (contains a title word like "Intern",
    # "Developer", "Engineer"...) and isn't a bullet point.
    header_positions = [i for i, l in enumerate(lines) if _TITLE_WORDS.search(l) and not l.startswith("-")]
    entries, spans = [], []

    for idx, pos in enumerate(header_positions):
        next_pos = header_positions[idx + 1] if idx + 1 < len(header_positions) else len(lines)
        header_text = lines[pos]
        body_lines = [re.sub(r"^-\s*", "", l) for l in lines[pos + 1:next_pos] if l]

        # Pull out the role title (the part containing the title word)
        title = None
        for part in re.split(r"\s+(?:at|@)\s+|\s*\|\s*|\s+[-—]\s+", header_text):
            if _TITLE_WORDS.search(part):
                title = DATE_RANGE.sub("", part).strip(" ,|-")
                break
        if title is None:
            title = header_text

        # A date range is a bonus, not a requirement — many resumes just say "Ongoing"
        m = DATE_RANGE.search(header_text)
        is_current = bool(re.search(_PRESENT, header_text, re.I)) or "ongoing" in header_text.lower()
        date_label = None
        if m:
            date_label = f"{m.group(1)} - {m.group(2)}"
            s_idx, e_idx = _month_index(m.group(1)), _month_index(m.group(2))
            if s_idx and e_idx and e_idx >= s_idx:
                spans.append((s_idx, e_idx))
        elif is_current:
            date_label = "Ongoing"

        entries.append({
            "title": title,
            "date_range": date_label,
            "is_current": is_current,
            "highlights": body_lines[:10],
            "technologies": [n for n, _ in find_skills(" ".join(body_lines))],
        })

    years = round(_total_months(spans) / 12, 1)
    return entries, years


# ---------- 8. Education ----------
_DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?sc|bca|b\.?\s?com|bba|bachelors?|m\.?\s?tech|m\.?\s?sc|mca|mba|"
    r"masters?|phd|diploma|hsc|ssc|12th|10th)\b", re.I)
# "B.E." / "M.E." are common too, but checked separately (case-sensitive) because
# lowercase "be" is also just the common English word "be" and would cause false matches.
_DEGREE_RE_SHORT = re.compile(r"\bB\.?E\.?\b|\bM\.?E\.?\b")


def _is_degree_line(line: str) -> bool:
    return bool(_DEGREE_RE.search(line) or _DEGREE_RE_SHORT.search(line))
_INSTITUTION_RE = re.compile(r"\b(university|college|institute|school|academy)\b", re.I)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def parse_education(lines: list[str], nlp=None) -> list[dict]:
    raw = []
    for ln in lines:
        line = re.sub(r"^-\s*", "", ln.strip())
        if not line:
            continue
        has_degree = _is_degree_line(line)
        has_institution = bool(_INSTITUTION_RE.search(line))
        if not (has_degree or has_institution):
            continue
        years = _YEAR_RE.findall(line)
        raw.append({
            "has_degree": has_degree,
            "has_institution": has_institution,
            "degree": line if has_degree else None,
            "institution": line if has_institution and not has_degree else None,
            "year": years[-1] if years else None,
        })

    # A degree and its institution might be split across two lines, in EITHER order
    # (institution-then-degree, or degree-then-institution). Check both neighbors.
    merged, used = [], set()
    for i, e in enumerate(raw):
        if i in used:
            continue
        if e["has_degree"] and not e["has_institution"]:
            institution, year = None, e["year"]
            for j in (i - 1, i + 1):
                if 0 <= j < len(raw) and j not in used and raw[j]["institution"]:
                    institution = raw[j]["institution"]
                    year = year or raw[j]["year"]
                    used.add(j)
                    break
            merged.append({"degree": e["degree"], "institution": institution, "year": year})
            used.add(i)
        elif e["has_institution"] and not e["has_degree"]:
            merged.append({"degree": None, "institution": e["institution"], "year": e["year"]})
            used.add(i)
        else:  # a single line that has both
            merged.append({"degree": e["degree"], "institution": e["institution"], "year": e["year"]})
            used.add(i)
    return merged[:6]


# ---------- 9. Projects ----------
def parse_projects(lines: list[str]) -> list[dict]:
    projects, current = [], None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("-") and len(line.split()) <= 12:
            current = {"name": line.split("|")[0].strip(), "description": []}
            projects.append(current)
        elif current is not None:
            current["description"].append(re.sub(r"^-\s*", "", line))
    for p in projects:
        block = p["name"] + " " + " ".join(p["description"])
        p["technologies"] = [n for n, _ in find_skills(block)]
        p["description"] = p["description"][:5]
    return projects[:8]


# ---------- 10. Certifications ----------
def parse_certifications(lines: list[str]) -> list[str]:
    certs = []
    for raw in lines:
        line = re.sub(r"^-\s*", "", raw.strip())
        if 3 < len(line) <= 150:
            certs.append(line)
    return certs[:10]


# ---------- Put it all together ----------
def parse_resume(raw_text: str) -> dict:
    text = clean_text(raw_text)
    sections = split_sections(text)
    header = [l for l in sections.get("header", []) if l.strip()]
    nlp = _load_nlp()

    experience, years = parse_experience(sections.get("experience", []))

    return {
        "name": extract_name(header, nlp),
        "contact": extract_contact(text),
        "summary": " ".join(sections.get("summary", [])).strip()[:500] or None,
        "education": parse_education(sections.get("education", []) or text.splitlines(), nlp),
        "experience": experience,
        "total_experience_years": years,
        "projects": parse_projects(sections.get("projects", [])),
        "certifications": parse_certifications(sections.get("certifications", [])),
        "skills": extract_skills(text),
    }
 
 