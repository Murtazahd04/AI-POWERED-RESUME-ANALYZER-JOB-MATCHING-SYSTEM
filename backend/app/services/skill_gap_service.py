"""
Skill Gap Analysis (Feature 9).

Pipeline
--------
1. Break the parsed resume into small pieces (skills, bullets, project lines...).
2. Each job requirement is compared with every piece:
      - exact / keyword match  -> score 1.0
      - otherwise sentence-embedding cosine similarity (meaning-based)
3. Requirements scoring below GAP_THRESHOLD are gaps.
4. Gaps get a priority (high / medium / low).
5. Each gap is matched against a learning catalog (same embeddings);
   recognised certifications are ranked above generic courses.
6. The top 2-3 recommendations per gap go to an LLM for a short explanation
   (falls back to a plain template if no API key / the call fails).

Everything here is synchronous; call it with run_in_threadpool from FastAPI.
"""

import json
import os
import re
from typing import Callable, Optional

import numpy as np

from app.data.learning_catalog import CATALOG, RECOGNISED_PROVIDERS
from app.data.role_skills import ROLE_SKILLS

# ----------------------------- configuration ------------------------------
GAP_THRESHOLD = float(os.getenv("SKILL_GAP_THRESHOLD", "0.55"))
HIGH_BELOW = float(os.getenv("SKILL_GAP_HIGH_BELOW", "0.30"))
MEDIUM_BELOW = float(os.getenv("SKILL_GAP_MEDIUM_BELOW", "0.45"))
TOP_K = 3                 # recommendations per gap
MIN_REC_SIMILARITY = 0.30  # ignore catalog items less related than this
CERT_BONUS = 0.08          # ranking boost for recognised certifications
MAX_EXPLAINED_GAPS = 8     # keep the single LLM call small

# ------------------------------- embeddings -------------------------------
# If Feature 7 already has an embedding helper, replace the body of `embed`
# with a call to it. It must return an (n, d) array of L2-normalised vectors.
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    return _model


def embed(texts: list) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1))
    vecs = _get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=float)


# ------------------------------ text helpers ------------------------------
def _norm(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_term(haystack_norm: str, term: str) -> bool:
    term_norm = _norm(term)
    if not term_norm:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(term_norm) + r"(?![a-z0-9])"
    return re.search(pattern, haystack_norm) is not None


def resume_pieces(parsed: dict) -> list:
    """Flatten the parsed resume into small, meaningful text pieces."""
    pieces = []
    skills = parsed.get("skills") or {}
    pieces += list(skills.get("technical") or [])
    pieces += list(skills.get("soft") or [])
    if parsed.get("summary"):
        pieces.append(parsed["summary"])
    for exp in parsed.get("experience") or []:
        if exp.get("title"):
            pieces.append(exp["title"])
        pieces += list(exp.get("highlights") or [])
        pieces += list(exp.get("technologies") or [])
    for proj in parsed.get("projects") or []:
        if proj.get("name"):
            pieces.append(proj["name"])
        pieces += list(proj.get("description") or [])
        pieces += list(proj.get("technologies") or [])
    pieces += list(parsed.get("certifications") or [])
    for edu in parsed.get("education") or []:
        if edu.get("degree"):
            pieces.append(edu["degree"])

    seen, unique = set(), []
    for piece in pieces:
        piece = str(piece).strip()
        key = piece.lower()
        if piece and key not in seen:
            seen.add(key)
            unique.append(piece)
    return unique


# ------------------------------- core logic -------------------------------
def priority_for(score: float, kind: str) -> str:
    if score < HIGH_BELOW:
        level = "high"
    elif score < MEDIUM_BELOW:
        level = "medium"
    else:
        level = "low"
    if kind == "preferred":  # nice-to-have skills are one step less urgent
        level = {"high": "medium", "medium": "low", "low": "low"}[level]
    return level


def score_requirements(
    requirements: list,
    pieces: list,
    embed_fn: Callable = embed,
):
    """
    requirements: [{"skill": str, "kind": "required" | "preferred"}]
    Returns (results, requirement_vectors). One result per requirement.
    """
    skills = [r["skill"] for r in requirements]
    req_vecs = embed_fn(skills)
    piece_vecs = embed_fn(pieces)
    haystack = _norm(" \n ".join(pieces))

    if len(pieces) and len(skills):
        sims = req_vecs @ piece_vecs.T
    else:
        sims = np.zeros((len(skills), max(len(pieces), 1)))

    results = []
    for i, req in enumerate(requirements):
        best_idx = int(np.argmax(sims[i])) if len(pieces) else -1
        semantic = float(max(0.0, sims[i][best_idx])) if best_idx >= 0 else 0.0

        if _contains_term(haystack, req["skill"]):
            score, via, evidence = 1.0, "exact", None
            for piece in pieces:  # find a nice evidence line
                if _contains_term(_norm(piece), req["skill"]):
                    evidence = piece
                    break
        else:
            score, via = semantic, "semantic"
            evidence = pieces[best_idx] if best_idx >= 0 and semantic >= GAP_THRESHOLD else None

        is_gap = score < GAP_THRESHOLD
        results.append(
            {
                "skill": req["skill"],
                "kind": req.get("kind", "required"),
                "score": round(score, 3),
                "status": "gap" if is_gap else "matched",
                "matched_via": None if is_gap else via,
                "evidence": evidence,
                "priority": priority_for(score, req.get("kind", "required")) if is_gap else None,
            }
        )
    return results, req_vecs


def compatibility(results: list) -> int:
    """Weighted coverage: matched = full credit, gaps get partial credit."""
    if not results:
        return 0
    total_weight = credit = 0.0
    for r in results:
        weight = 1.0 if r["kind"] == "required" else 0.5
        total_weight += weight
        credit += weight * min(r["score"] / GAP_THRESHOLD, 1.0)
    return int(round(100 * credit / total_weight))


# ------------------------------ recommendations ---------------------------
_catalog_vecs: Optional[np.ndarray] = None


def _catalog_text(item: dict) -> str:
    return f'{item["title"]}. {item["description"]} Skills: {", ".join(item["skills"])}.'


def _get_catalog_vectors(embed_fn: Callable) -> np.ndarray:
    global _catalog_vecs
    if _catalog_vecs is None:
        _catalog_vecs = embed_fn([_catalog_text(c) for c in CATALOG])
    return _catalog_vecs


def recommend(gap_vec: np.ndarray, catalog_vecs: np.ndarray, skill: str) -> list:
    sims = catalog_vecs @ gap_vec
    ranked = []
    for idx, item in enumerate(CATALOG):
        sim = float(sims[idx])
        # a catalog tag that literally names the skill is a strong signal,
        # but we add to the real similarity so closer matches still rank first
        if any(_norm(tag) == _norm(skill) for tag in item["skills"]):
            sim = min(1.0, sim + 0.30)
        if sim < MIN_REC_SIMILARITY:
            continue
        bonus = CERT_BONUS if (item["type"] == "certification" and item["provider"] in RECOGNISED_PROVIDERS) else 0.0
        ranked.append((sim + bonus, sim, item))
    ranked.sort(key=lambda t: t[0], reverse=True)
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "provider": item["provider"],
            "type": item["type"],
            "level": item["level"],
            "url": item["url"],
            "relevance": round(sim, 3),
        }
        for _, sim, item in ranked[:TOP_K]
    ]


# ------------------------------ AI explanation ----------------------------
_llm_key: Optional[str] = None
_llm_model: Optional[str] = None


def configure_llm(api_key: Optional[str], model: Optional[str]) -> None:
    """Called by the router with the app's existing AI settings (ai_api_key / ai_model_name)."""
    global _llm_key, _llm_model
    _llm_key = api_key or None
    _llm_model = model or None


def _call_provider(httpx, key: str, model: str, prompt: str) -> Optional[str]:
    """Detects Gemini / Anthropic / OpenAI from the key or model name."""
    m = (model or "").lower().replace("models/", "")
    try:
        if "gemini" in m or key.startswith("AIza"):
            model_name = m or "gemini-2.5-flash"
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                params={"key": key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        if "claude" in m or key.startswith("sk-ant"):
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        if m.startswith(("gpt", "o1", "o3", "o4")) or key.startswith("sk-"):
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model or "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None
    return None


def _llm(prompt: str) -> Optional[str]:
    """Uses the app's AI key if configured, then optional env keys. Returns None if nothing works."""
    try:
        import httpx
    except Exception:
        return None
    candidates = []
    if _llm_key:
        candidates.append((_llm_key, _llm_model or ""))
    if os.getenv("GEMINI_API_KEY"):
        candidates.append((os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL", "gemini-2.5-flash")))
    if os.getenv("OPENAI_API_KEY"):
        candidates.append((os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_MODEL", "gpt-4o-mini")))
    for key, model in candidates:
        text = _call_provider(httpx, key, model, prompt)
        if text:
            return text
    return None


def _fallback_text(gap: dict) -> str:
    recs = gap["recommendations"]
    if not recs:
        return (
            f'Your resume doesn\'t show clear evidence of {gap["skill"]}. '
            "Adding a project or bullet that uses it would help."
        )
    names = " or ".join(f'{r["title"]} ({r["provider"]})' for r in recs[:2])
    return (
        f'Your resume doesn\'t show clear evidence of {gap["skill"]}. '
        f"Consider {names}, then add a project that uses it."
    )


def explain_gaps(job_title: str, gaps: list) -> dict:
    """Return {skill: explanation}. One LLM call for all gaps."""
    if not gaps:
        return {}
    subset = gaps[:MAX_EXPLAINED_GAPS]
    payload = [
        {
            "skill": g["skill"],
            "priority": g["priority"],
            "recommended": [f'{r["title"]} ({r["provider"]}, {r["type"]})' for r in g["recommendations"]],
        }
        for g in subset
    ]
    prompt = (
        f'A candidate is applying for "{job_title}". Their resume lacks evidence of the skills below.\n'
        "For each skill write 2 short, friendly sentences: why it matters for this role and which of "
        "the listed resources to start with. Only mention resources from the list. Do not invent facts.\n"
        'Reply with ONLY JSON: {"<skill>": "<explanation>", ...}\n\n'
        f"{json.dumps(payload)}"
    )
    out = {}
    raw = _llm(prompt)
    if raw:
        try:
            start, end = raw.find("{"), raw.rfind("}")
            parsed = json.loads(raw[start : end + 1])
            out = {str(k): str(v) for k, v in parsed.items() if isinstance(v, str)}
        except Exception:
            out = {}
    for g in gaps:
        out.setdefault(g["skill"], _fallback_text(g))
    return out


# --------------------------------- entry point ----------------------------
def analyze(parsed_resume: dict, job: dict, embed_fn: Callable = embed, use_llm: bool = True) -> dict:
    requirements = [{"skill": s.strip(), "kind": "required"} for s in job.get("required_skills") or [] if str(s).strip()]
    requirements += [{"skill": s.strip(), "kind": "preferred"} for s in job.get("preferred_skills") or [] if str(s).strip()]

    pieces = resume_pieces(parsed_resume)
    results, req_vecs = score_requirements(requirements, pieces, embed_fn)

    catalog_vecs = _get_catalog_vectors(embed_fn)
    gaps = []
    for i, r in enumerate(results):
        if r["status"] != "gap":
            continue
        gaps.append(
            {
                "skill": r["skill"],
                "kind": r["kind"],
                "score": r["score"],
                "priority": r["priority"],
                "recommendations": recommend(req_vecs[i], catalog_vecs, r["skill"]),
            }
        )
    order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: (order[g["priority"]], g["score"]))

    explanations = explain_gaps(job.get("title", "this role"), gaps) if use_llm else {}
    for g in gaps:
        g["explanation"] = explanations.get(g["skill"]) or _fallback_text(g)

    matched = [r for r in results if r["status"] == "matched"]
    return {
        "job_title": job.get("title", ""),
        "company": job.get("company", ""),
        "compatibility": compatibility(results),
        "total_requirements": len(results),
        "matched_count": len(matched),
        "gap_count": len(gaps),
        "threshold": GAP_THRESHOLD,
        "requirements": results,
        "gaps": gaps,
    }


# ------------------------------ role -> skills ----------------------------
ROLE_MATCH_THRESHOLD = float(os.getenv("ROLE_MATCH_THRESHOLD", "0.6"))
_role_cache: dict = {}          # normalised role -> resolved result
_role_label_vecs = None
_ROLE_LABELS = []               # [(label_text, canonical_role_name)]
for _name, _data in ROLE_SKILLS.items():
    _ROLE_LABELS.append((_name, _name))
    for _alias in _data.get("aliases", []):
        _ROLE_LABELS.append((_alias, _name))


def list_roles() -> list:
    return sorted(ROLE_SKILLS.keys())


def _clean_skill_list(values, limit: int) -> list:
    out, seen = [], set()
    for v in values or []:
        v = str(v).strip()
        if 0 < len(v) <= 40 and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out[:limit]


def _ai_role_skills(role: str) -> Optional[dict]:
    prompt = (
        f'List the skills typically required for the job role "{role}".\n'
        'Reply with ONLY JSON: {"required": [8 to 12 specific skills], "preferred": [3 to 5 nice-to-have skills]}\n'
        'Use short skill names such as "Python", "Docker", "REST API", not sentences. '
        'If this is not a real job role, reply {"required": [], "preferred": []}.'
    )
    raw = _llm(prompt)
    if not raw:
        return None
    try:
        parsed = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
        required = _clean_skill_list(parsed.get("required"), 12)
        preferred = [s for s in _clean_skill_list(parsed.get("preferred"), 5) if s.lower() not in {r.lower() for r in required}]
    except Exception:
        return None
    if not required:
        return None
    return {"required": required, "preferred": preferred}


def _builtin_role_skills(role: str, embed_fn: Callable) -> Optional[tuple]:
    """Returns (skills_dict, matched_role_name) or None."""
    global _role_label_vecs
    key = _norm(role)
    for label, name in _ROLE_LABELS:  # exact title or alias
        if _norm(label) == key:
            return ROLE_SKILLS[name], name
    if _role_label_vecs is None:
        _role_label_vecs = embed_fn([label for label, _ in _ROLE_LABELS])
    vec = embed_fn([role])[0]
    sims = _role_label_vecs @ vec
    best = int(np.argmax(sims))
    if float(sims[best]) >= ROLE_MATCH_THRESHOLD:
        name = _ROLE_LABELS[best][1]
        return ROLE_SKILLS[name], name
    return None


def resolve_role_skills(role: str, embed_fn: Callable = embed, use_llm: bool = True) -> dict:
    """
    Returns {"required": [...], "preferred": [...], "source": "ai" | "built-in", "matched_role": str | None}
    Raises ValueError if the role can't be resolved.
    """
    key = _norm(role)
    if not key:
        raise ValueError("Enter a job role, for example “Python Developer”.")
    cached = _role_cache.get(key)
    if cached:
        return cached

    result = None
    if use_llm:
        ai = _ai_role_skills(role)
        if ai:
            result = {**ai, "source": "ai", "matched_role": None}
    if result is None:
        found = _builtin_role_skills(role, embed_fn)
        if found:
            data, name = found
            result = {
                "required": list(data["required"]),
                "preferred": list(data.get("preferred", [])),
                "source": "built-in",
                "matched_role": name,
            }
    if result is None:
        raise ValueError(
            f"Couldn't work out the skills for “{role}”. Try a more common title like “Data Analyst”, "
            "or set GEMINI_API_KEY so any role can be looked up."
        )
    _role_cache[key] = result
    return result


def analyze_role(parsed_resume: dict, role: str, embed_fn: Callable = embed, use_llm: bool = True) -> dict:
    role = " ".join(role.split())
    skills = resolve_role_skills(role, embed_fn, use_llm)
    job = {"title": role, "required_skills": skills["required"], "preferred_skills": skills["preferred"]}
    result = analyze(parsed_resume, job, embed_fn, use_llm)
    result["role"] = role
    result["role_source"] = skills["source"]
    result["role_matched"] = skills["matched_role"]
    return result

def analyze_role(parsed_resume: dict, role: str, embed_fn: Callable = embed, use_llm: bool = True) -> dict:
    """Connects a typed role name to the full analysis. This is what the router calls."""
    skills_info = resolve_role_skills(role, embed_fn=embed_fn, use_llm=use_llm)
    job = {
        "title": skills_info.get("matched_role") or role,
        "company": "",
        "required_skills": skills_info["required"],
        "preferred_skills": skills_info.get("preferred", []),
    }
    result = analyze(parsed_resume, job, embed_fn=embed_fn, use_llm=use_llm)
    result["role"] = role
    result["role_source"] = skills_info.get("source")
    result["role_matched"] = skills_info.get("matched_role")
    return result