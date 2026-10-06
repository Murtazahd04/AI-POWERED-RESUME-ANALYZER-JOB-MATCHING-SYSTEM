"""
Built-in skills for common roles. Used when no AI key is configured, or the AI call fails.
Skill names are chosen to match the tags in learning_catalog.py so recommendations work well.
Add roles freely: {"required": [...], "preferred": [...], "aliases": [...]}.
"""

ROLE_SKILLS = {
    "Python Developer": {
        "required": ["Python", "REST API", "SQL", "Git", "Data Structures", "FastAPI"],
        "preferred": ["Docker", "AWS", "MongoDB"],
        "aliases": ["Python Engineer", "Python Programmer"],
    },
    "Backend Developer": {
        "required": ["Python", "REST API", "SQL", "MongoDB", "Docker", "Git", "System Design"],
        "preferred": ["AWS", "CI/CD", "Kubernetes"],
        "aliases": ["Backend Engineer", "Server Side Developer"],
    },
    "Frontend Developer": {
        "required": ["JavaScript", "React", "HTML", "CSS", "Git", "Responsive Design"],
        "preferred": ["TypeScript", "REST API"],
        "aliases": ["Frontend Engineer", "React Developer", "UI Developer", "Web Developer"],
    },
    "Full Stack Developer": {
        "required": ["JavaScript", "React", "Node.js", "REST API", "MongoDB", "SQL", "Git"],
        "preferred": ["Docker", "AWS", "TypeScript"],
        "aliases": ["Full Stack Engineer", "MERN Developer"],
    },
    "Software Engineer": {
        "required": ["Data Structures", "Algorithms", "Git", "System Design", "Problem Solving", "SQL"],
        "preferred": ["Docker", "CI/CD", "Agile"],
        "aliases": ["Software Developer", "SDE", "Software Development Engineer", "Programmer"],
    },
    "Java Developer": {
        "required": ["Java", "SQL", "REST API", "Data Structures", "Git", "OOP"],
        "preferred": ["Spring Boot", "Docker", "Microservices"],
        "aliases": ["Java Engineer"],
    },
    "Data Analyst": {
        "required": ["SQL", "Excel", "Python", "Pandas", "Data Visualization", "Power BI"],
        "preferred": ["Tableau", "Statistics"],
        "aliases": ["Business Intelligence Analyst", "BI Analyst", "Data Analytics"],
    },
    "Data Scientist": {
        "required": ["Python", "Machine Learning", "Statistics", "Pandas", "SQL", "Data Visualization"],
        "preferred": ["Deep Learning", "NLP", "Scikit-learn"],
        "aliases": ["Data Science"],
    },
    "Machine Learning Engineer": {
        "required": ["Python", "Machine Learning", "Deep Learning", "Scikit-learn", "Pandas", "SQL", "Docker"],
        "preferred": ["PyTorch", "TensorFlow", "AWS"],
        "aliases": ["ML Engineer", "AI Engineer", "AI Developer"],
    },
    "NLP Engineer": {
        "required": ["Python", "NLP", "Transformers", "Embeddings", "Machine Learning", "Deep Learning"],
        "preferred": ["PyTorch", "Docker"],
        "aliases": ["Natural Language Processing Engineer", "LLM Engineer"],
    },
    "DevOps Engineer": {
        "required": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform", "Git"],
        "preferred": ["Python", "Monitoring"],
        "aliases": ["Site Reliability Engineer", "SRE", "Platform Engineer"],
    },
    "Cloud Engineer": {
        "required": ["AWS", "Linux", "Networking", "Docker", "Terraform", "Python"],
        "preferred": ["Kubernetes", "Azure", "Google Cloud"],
        "aliases": ["Cloud Architect", "Cloud Developer"],
    },
    "Cybersecurity Analyst": {
        "required": ["Cybersecurity", "Network Security", "Linux", "Networking", "Cryptography", "Python"],
        "preferred": ["Incident Response", "SIEM"],
        "aliases": ["Security Analyst", "Information Security Analyst", "Security Engineer"],
    },
    "Network Engineer": {
        "required": ["Networking", "Cisco", "Routing", "Switching", "TCP/IP", "Network Security"],
        "preferred": ["Linux", "Python"],
        "aliases": ["Network Administrator"],
    },
    "Database Administrator": {
        "required": ["SQL", "Databases", "MongoDB", "Linux", "Backup and Recovery", "Performance Tuning"],
        "preferred": ["AWS", "Python"],
        "aliases": ["DBA", "Database Engineer"],
    },
    "QA Engineer": {
        "required": ["Test Automation", "Selenium", "SQL", "Git", "Agile", "Bug Tracking"],
        "preferred": ["Python", "CI/CD", "API Testing"],
        "aliases": ["Software Tester", "Test Engineer", "QA Analyst", "SDET"],
    },
    "Mobile App Developer": {
        "required": ["Flutter", "Dart", "REST API", "Git", "UI Design", "State Management"],
        "preferred": ["Firebase", "Kotlin", "Swift"],
        "aliases": ["Android Developer", "iOS Developer", "Flutter Developer", "React Native Developer"],
    },
    "Business Analyst": {
        "required": ["Excel", "SQL", "Communication", "Agile", "Data Analysis", "Requirements Gathering"],
        "preferred": ["Power BI", "Scrum", "Stakeholder Management"],
        "aliases": ["Systems Analyst"],
    },
    "Project Manager": {
        "required": ["Project Management", "Agile", "Scrum", "Communication", "Leadership", "Risk Management"],
        "preferred": ["Jira", "Stakeholder Management"],
        "aliases": ["Scrum Master", "Technical Project Manager", "Program Manager"],
    },
    "UI/UX Designer": {
        "required": ["Figma", "Wireframing", "Prototyping", "User Research", "Design Systems", "Communication"],
        "preferred": ["HTML", "CSS", "Accessibility"],
        "aliases": ["UX Designer", "UI Designer", "Product Designer"],
    },
}