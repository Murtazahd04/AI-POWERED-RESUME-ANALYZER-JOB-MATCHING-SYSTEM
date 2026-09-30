"""Turns a raw resume file into structured data: name, contact info, education,
work experience, projects, certifications and skills."""
import io
import re
import unicodedata
from datetime import date

from ..skills_data import ALIAS_MAP, SKILL_PATTERNS, SOFT_CATEGORY


class ParseError(Exception):
    """Raised when a file's text genuinely can't be read (corrupted, password-protected, etc.)."""


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
    except Exception as exc:
        raise ParseError("This PDF could not be read. It may be corrupted or password-protected.") from exc
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
    "summary": ["summary", "profile", "objective", "about me"],
    "experience": ["experience", "work experience", "employment history", "internships"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "key skills", "core competencies"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "courses"],
}
_HEADING_LOOKUP = {a: sec for sec, aliases in SECTION_ALIASES.items() for a in aliases}


def _heading_of(line: str) -> str | None:
    if not line or len(line) > 40 or line.startswith("- "):
        return None
    clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
    return _HEADING_LOOKUP.get(clean)


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


def extract_name(header_lines: list[str]) -> str | None:
    for line in header_lines[:8]:
        line = line.strip()
        if not line or EMAIL_RE.search(line) or re.search(r"\d", line):
            continue
        words = line.replace("|", " ").split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            if not any(w.lower() in _NON_NAME for w in words):
                return line.title() if line.isupper() else line
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
    date_positions = [i for i, l in enumerate(lines) if DATE_RANGE.search(l)]
    entries, spans = [], []

    for idx, pos in enumerate(date_positions):
        start = pos
        while start - 1 >= 0 and start - 1 not in date_positions and len(lines[start - 1].split()) <= 12:
            start -= 1
            if idx > 0 and start <= date_positions[idx - 1]:
                break
        next_pos = date_positions[idx + 1] if idx + 1 < len(date_positions) else len(lines)
        header_lines = lines[start:pos + 1]
        body_lines = [re.sub(r"^-\s*", "", l) for l in lines[pos + 1:next_pos] if l]

        header_text = " ".join(header_lines)
        title_match = _TITLE_WORDS.search(header_text)
        title = None
        if title_match:
            for part in re.split(r"\s+(?:at|@)\s+|\s*\|\s*|\s+-\s+", header_text):
                if _TITLE_WORDS.search(part):
                    title = DATE_RANGE.sub("", part).strip(" ,|-")
                    break

        m = DATE_RANGE.search(lines[pos])
        s_idx, e_idx = _month_index(m.group(1)), _month_index(m.group(2))
        if s_idx and e_idx and e_idx >= s_idx:
            spans.append((s_idx, e_idx))

        entries.append({
            "title": title,
            "date_range": f"{m.group(1)} - {m.group(2)}",
            "highlights": body_lines[:10],
            "technologies": [n for n, _ in find_skills(" ".join(body_lines))],
        })

    years = round(_total_months(spans) / 12, 1)
    return entries, years


# ---------- 8. Education ----------
_DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?sc|bca|b\.?\s?com|bba|bachelors?|m\.?\s?tech|m\.?\s?sc|mca|mba|"
    r"masters?|phd|diploma|hsc|ssc|12th|10th)\b", re.I)
_INSTITUTION_RE = re.compile(r"\b(university|college|institute|school|academy)\b", re.I)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_education(lines: list[str]) -> list[dict]:
    entries = []
    for raw in lines:
        line = re.sub(r"^-\s*", "", raw.strip())
        if not line:
            continue
        if _DEGREE_RE.search(line) or _INSTITUTION_RE.search(line):
            years = _YEAR_RE.findall(line)
            entries.append({
                "text": line,
                "is_degree_line": bool(_DEGREE_RE.search(line)),
                "institution": line if _INSTITUTION_RE.search(line) and not _DEGREE_RE.search(line) else None,
                "year": years[-1] if years else None,
            })
    # Merge a "degree" line with the very next "institution" line if they're split across two lines
    merged = []
    skip_next = False
    for i, e in enumerate(entries):
        if skip_next:
            skip_next = False
            continue
        if e["is_degree_line"] and i + 1 < len(entries) and entries[i + 1]["institution"]:
            merged.append({"degree": e["text"], "institution": entries[i + 1]["institution"],
                            "year": e["year"] or entries[i + 1]["year"]})
            skip_next = True
        elif e["is_degree_line"]:
            merged.append({"degree": e["text"], "institution": None, "year": e["year"]})
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

    experience, years = parse_experience(sections.get("experience", []))

    return {
        "name": extract_name(header),
        "contact": extract_contact(text),
        "summary": " ".join(sections.get("summary", [])).strip()[:500] or None,
        "education": parse_education(sections.get("education", []) or text.splitlines()),
        "experience": experience,
        "total_experience_years": years,
        "projects": parse_projects(sections.get("projects", [])),
        "certifications": parse_certifications(sections.get("certifications", [])),
        "skills": extract_skills(text),
    }
 
 