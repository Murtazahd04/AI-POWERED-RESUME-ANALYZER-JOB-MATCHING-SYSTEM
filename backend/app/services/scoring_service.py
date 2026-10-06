"""Turns parsed resume data (from parser_service.py) into a 0-100 score, broken
down by category, plus an ATS compatibility checklist."""

WEIGHTS = {"skills": 0.30, "experience": 0.25, "education": 0.15, "projects": 0.15, "ats": 0.15}


def _factor(label: str, earned: float, max_points: float, note: str) -> dict:
    """One scored item, e.g. {'label': 'Technical skills', 'points': 18, 'max': 50, 'note': '...'}"""
    return {"label": label, "points": round(earned, 1), "max": max_points, "note": note}


def _total_out_of_100(factors: list[dict]) -> int:
    max_sum = sum(f["max"] for f in factors)
    earned_sum = sum(f["points"] for f in factors)
    return round(100 * earned_sum / max_sum) if max_sum else 0


def _capped_ratio(value: float, full_marks_at: float) -> float:
    """e.g. _capped_ratio(6, 10) -> 0.6   |   _capped_ratio(15, 10) -> 1.0 (can't exceed full marks)"""
    return min(value / full_marks_at, 1.0) if full_marks_at else 0.0


# ---------- Skills ----------
def _score_skills(parsed: dict) -> list[dict]:
    technical = len(parsed["skills"]["technical"])
    soft = len(parsed["skills"]["soft"])
    return [
        _factor("Technical skills", 70 * _capped_ratio(technical, 10), 70,
                f"{technical} technical skill(s) found (10+ earns full marks)."),
        _factor("Soft skills", 30 * _capped_ratio(soft, 3), 30,
                f"{soft} soft skill(s) found (3+ earns full marks)."),
    ]


# ---------- Experience ----------
def _score_experience(parsed: dict) -> list[dict]:
    entries = parsed["experience"]
    years = parsed["total_experience_years"]
    if not entries:
        return [_factor("Work experience", 0, 100, "No work experience was detected.")]

    with_highlights = sum(1 for e in entries if e["highlights"])
    with_tech = sum(1 for e in entries if e["technologies"])
    return [
        _factor("Years of experience", 45 * _capped_ratio(years, 3), 45,
                f"{years} year(s) detected (3+ earns full marks)."),
        _factor("Roles listed", 20, 20, f"{len(entries)} role(s) with dates found."),
        _factor("Bullet points describing work", 20 * with_highlights / len(entries), 20,
                f"{with_highlights} of {len(entries)} role(s) have bullet points."),
        _factor("Technologies mentioned", 15 * with_tech / len(entries), 15,
                f"{with_tech} of {len(entries)} role(s) mention specific tools/tech."),
    ]


# ---------- Education ----------
def _score_education(parsed: dict) -> list[dict]:
    entries = parsed["education"]
    if not entries:
        return [_factor("Education", 0, 100, "No education entries were detected.")]

    with_institution = sum(1 for e in entries if e["institution"])
    with_year = sum(1 for e in entries if e["year"])
    return [
        _factor("Degree listed", 60, 60, f"{len(entries)} education entry(ies) found."),
        _factor("Institution named", 25 if with_institution else 0, 25,
                "An institution name was found." if with_institution else "No institution name was detected."),
        _factor("Graduation year", 15 if with_year else 0, 15,
                "A graduation year was found." if with_year else "No graduation year was detected."),
    ]


# ---------- Projects ----------
def _score_projects(parsed: dict) -> list[dict]:
    projects = parsed["projects"]
    if not projects:
        return [_factor("Projects", 0, 100, "No projects were detected.")]

    with_tech = sum(1 for p in projects if p["technologies"])
    with_desc = sum(1 for p in projects if p["description"])
    return [
        _factor("Number of projects", 40 * _capped_ratio(len(projects), 3), 40,
                f"{len(projects)} project(s) found (3+ earns full marks)."),
        _factor("Technologies listed", 30 * with_tech / len(projects), 30,
                f"{with_tech} of {len(projects)} project(s) name the tools used."),
        _factor("Descriptions", 30 * with_desc / len(projects), 30,
                f"{with_desc} of {len(projects)} project(s) have a description."),
    ]


# ---------- ATS checklist ----------
def _score_ats(parsed: dict) -> list[dict]:
    c = parsed["contact"]
    bullet_count = sum(len(e["highlights"]) for e in parsed["experience"])
    bullet_count += sum(len(p["description"]) for p in parsed["projects"])

    def check(label: str, is_true: bool, points: float, good: str, bad: str) -> dict:
        return _factor(label, points if is_true else 0, points, good if is_true else bad)

    return [
        check("Email address", bool(c["email"]), 20, "Email found.",
              "No email found - ATS systems need this to create your candidate record."),
        check("Phone number", bool(c["phone"]), 15, "Phone number found.", "No phone number found."),
        check("Skills section", len(parsed["skills"]["technical"]) + len(parsed["skills"]["soft"]) > 0, 15,
              "A Skills section was detected.", "No Skills section was detected."),
        check("Experience section", len(parsed["experience"]) > 0, 15,
              "An Experience section was detected.", "No Experience section was detected."),
        check("Education section", len(parsed["education"]) > 0, 10,
              "An Education section was detected.", "No Education section was detected."),
        check("Bullet points used", bullet_count >= 3, 15,
              "Bullet points are used to describe work - easier for ATS to scan.",
              "Few or no bullet points found. Use '-' or 'bullet' to list achievements."),
        check("LinkedIn or GitHub link", bool(c["linkedin"] or c["github"]), 10,
              "A LinkedIn or GitHub link was found.", "No LinkedIn or GitHub link was found."),
    ]


def _grade(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Needs work"


def compute_score(parsed: dict) -> dict:
    skills_factors = _score_skills(parsed)
    experience_factors = _score_experience(parsed)
    education_factors = _score_education(parsed)
    projects_factors = _score_projects(parsed)
    ats_factors = _score_ats(parsed)

    components = {
        "skills": {"score": _total_out_of_100(skills_factors), "factors": skills_factors},
        "experience": {"score": _total_out_of_100(experience_factors), "factors": experience_factors},
        "education": {"score": _total_out_of_100(education_factors), "factors": education_factors},
        "projects": {"score": _total_out_of_100(projects_factors), "factors": projects_factors},
    }
    ats_score = _total_out_of_100(ats_factors)

    overall = round(
        sum(components[k]["score"] * WEIGHTS[k] for k in components) + ats_score * WEIGHTS["ats"]
    )
    weakest = min(components, key=lambda k: components[k]["score"])

    return {
        "overall": overall,
        "grade": _grade(overall),
        "components": components,
        "ats": {"score": ats_score, "checks": ats_factors},
        "weakest_area": weakest,
        "summary": f"Overall {overall}/100 ({_grade(overall)}). Biggest opportunity: {weakest} "
                   f"({components[weakest]['score']}/100).",
    }
