"""A dictionary of known skills, grouped by category, with common alternate spellings.
The parser scans resume text for these exact names so that 'ReactJS', 'React.js' and
'React' all get recognised as the same skill."""
import re

SKILLS: dict[str, dict[str, list[str]]] = {
    "Programming Languages": {
        "Python": [], "Java": [], "JavaScript": ["js", "ecmascript"], "TypeScript": ["ts"],
        "C++": ["cpp"], "C#": ["csharp"], "Go": ["golang"], "Rust": [], "PHP": [], "Ruby": [],
        "Kotlin": [], "Swift": [], "SQL": ["t-sql", "pl/sql"], "HTML": ["html5"], "CSS": ["css3"], "C": [],
    },
    "Frontend": {
        "React": ["reactjs", "react.js"], "Angular": ["angularjs"], "Vue.js": ["vue", "vuejs"],
        "Next.js": ["nextjs"], "Redux": [], "Tailwind CSS": ["tailwind", "tailwindcss"],
        "Bootstrap": [], "jQuery": [],
    },
    "Backend": {
        "Node.js": ["nodejs", "node"], "Express.js": ["express", "expressjs"], "FastAPI": [],
        "Django": [], "Flask": [], "Spring Boot": ["springboot"], ".NET": ["dotnet", "asp.net"],
        "REST API": ["rest apis", "restful api", "restful"], "GraphQL": [], "Microservices": [],
    },
    "Databases": {
        "MongoDB": ["mongo"], "MySQL": [], "PostgreSQL": ["postgres"], "SQLite": [],
        "Redis": [], "Firebase": [], "DynamoDB": [],
    },
    "Cloud & DevOps": {
        "AWS": ["amazon web services"], "Azure": ["microsoft azure"],
        "Google Cloud": ["gcp", "google cloud platform"], "Docker": [], "Kubernetes": ["k8s"],
        "Jenkins": [], "CI/CD": ["cicd", "continuous integration"], "GitHub Actions": [],
        "Linux": [], "Git": [], "GitHub": [], "GitLab": [],
    },
    "Data & AI": {
        "Machine Learning": ["ml"], "Deep Learning": [], "NLP": ["natural language processing"],
        "TensorFlow": [], "PyTorch": [], "scikit-learn": ["sklearn"], "Pandas": [], "NumPy": [],
        "Data Analysis": ["data analytics"], "Power BI": ["powerbi"], "Tableau": [],
        "Excel": ["ms excel", "microsoft excel"], "Data Structures": ["dsa"], "Statistics": [],
    },
    "Mobile": {
        "Android": [], "iOS": [], "Flutter": [], "React Native": [],
    },
    "Testing & Tools": {
        "Selenium": [], "Jest": [], "PyTest": [], "JUnit": [], "Postman": [], "Jira": [],
        "Figma": [], "Agile": [], "Scrum": [],
    },
    "Soft Skills": {
        "Leadership": ["team leadership"], "Communication": ["communication skills"],
        "Teamwork": ["team player", "collaboration"], "Problem Solving": ["problem-solving"],
        "Time Management": [], "Project Management": [], "Mentoring": ["mentorship"],
    },
}

SOFT_CATEGORY = "Soft Skills"

# Build a fast lookup: any spelling -> (proper name, category)
ALIAS_MAP: dict[str, tuple[str, str]] = {}
for _cat, _skills in SKILLS.items():
    for _name, _aliases in _skills.items():
        ALIAS_MAP[_name.lower()] = (_name, _cat)
        for _a in _aliases:
            ALIAS_MAP[_a.lower()] = (_name, _cat)


def _pattern(alias: str) -> re.Pattern:
    # \b-style boundaries so "Java" doesn't also match inside "JavaScript"
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.IGNORECASE)


SKILL_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (canon, cat, _pattern(alias))
    for alias, (canon, cat) in ALIAS_MAP.items()
    if alias not in {"c", "go", "node", "ml", "ts", "js"}  # too short/ambiguous to auto-detect safely
] + [
    ("Node.js", "Backend", re.compile(r"(?<![A-Za-z0-9])Node(?![A-Za-z0-9])")),
    ("Machine Learning", "Data & AI", re.compile(r"(?<![A-Za-z0-9])ML(?![A-Za-z0-9])")),
]


def normalize_skill(raw: str) -> str:
    hit = ALIAS_MAP.get(raw.strip().lower())
    return hit[0] if hit else raw.strip()