**AI-POWERED RESUME ANALYZER**  
**& JOB MATCHING SYSTEM**

**Merged Development Plan \+ Feature Specification**

Consolidated from the Project Development Plan and AI Resume Analyser Feature document

| PROJECT HIGHLIGHTS1\. Meaning-based resume–job matching using sentence embeddings \+ cosine similarity, blended with exact keyword checks.2\. Live job browsing through legitimate job-aggregator APIs rather than direct LinkedIn/Naukri scraping.3\. Skill-gap analysis that turns missing requirements into personalised course/certification recommendations.4\. End-to-end resume pipeline: Upload → Parse → AI Analysis → Score → Match → Recommendations → Skill Gap → Dashboard. |
| :---- |

**Technology Base: React.js • FastAPI • MongoDB • Cloudinary • GitHub • Vercel • Render • Gemini/OpenAI • Recharts**

# **1\. Project Technology Base**

| Component | Technology |
| :---- | :---- |
| **Frontend** | React.js |
| **Backend** | Python \+ FastAPI |
| **Database** | MongoDB |
| **File Storage** | Cloudinary |
| **Version Control** | GitHub |
| **Frontend Deployment** | Vercel |
| **Backend Deployment** | Render |
| **AI** | Gemini API / OpenAI API |
| **API Communication** | REST API \+ Axios |
| **Charts** | Recharts |

# **2\. Phase 1 — Project Base Setup**

| GoalSet up the complete technical foundation before feature development starts. Phase 1 must finish with React.js → FastAPI → MongoDB/Cloudinary and GitHub → Vercel/Render deployment working end-to-end. |
| :---- |

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ✓ | Create GitHub Repository | Create the main repository for the project. |
| ✓ | Create Repository Structure | Create frontend and backend folders. |
| ✓ | Initialize React Project | Create the React frontend application. |
| ✓ | Install Frontend Dependencies | Install React Router, Axios, Recharts and other required packages. |
| ✓ | Create Frontend Structure | Create folders for components, pages, services, assets and utilities. |
| ✓ | Initialize Python Backend | Create the FastAPI backend application. |
| ✓ | Configure Python Environment | Create virtual environment and requirements.txt. |
| ✓ | Create Backend Structure | Create routes, services, models, utilities and configuration folders. |
| ✓ | Configure Environment Variables | Set up MongoDB, Cloudinary and AI API variables. |
| ✓ | Connect MongoDB | Establish backend connection with MongoDB. |
| ✓ | Configure Cloudinary | Configure Cloudinary for resume/file storage. |
| ✓ | Create Basic Backend API | Create a health/status API to verify backend operation. |
| ✓ | Connect React → FastAPI | Establish frontend/backend communication using Axios \+ REST API. |
| ✓ | Create Basic Frontend Layout | Create navbar, sidebar and application layout. |
| ✓ | Configure React Routing | Create routes for Dashboard, Resume, Jobs, Skills and Profile. |
| ✓ | Test MongoDB | Insert and retrieve test data. |
| ✓ | Test Cloudinary | Upload and retrieve a test file. |
| ✓ | Test Resume Upload Flow | Verify React → FastAPI → Cloudinary. |
| ✓ | Configure Git Workflow | Establish branch, commit and push workflow. |
| ✓ | Deploy Frontend | Deploy the React application to Vercel. |
| ✓ | Deploy Backend | Deploy the FastAPI backend to Render. |
| ✓ | Configure Production Variables | Add required environment variables to Vercel \+ Render. |
| ✓ | Connect Production Frontend \+ Backend | Connect the live React frontend to the live API. |
| ✓ | Final Project Base Test | Verify React → FastAPI → MongoDB/Cloudinary works successfully. |

# **3\. Phase 2 — Feature Development**

| Assignment RuleOne feature/module → One team member → Complete implementation → Testing → GitHub push → Complete. The Team Member column remains available for later assignment. |
| :---- |

| Feature | Done | Pending |
| :---- | :---- | :---- |
| User Authentication & Profile | 0 | 7 |
| Resume Upload & Management | 0 | 9 |
| Resume Parser | 0 | 10 |
| AI Resume Analysis | 0 | 12 |
| Resume Scoring & ATS Analysis | 0 | 8 |
| Job Database & Job Management | 0 | 11 |
| AI Job Matching Engine | 0 | 10 |
| Job Recommendation Interface | 0 | 9 |
| Skill Gap Analysis | 0 | 7 |
| Main Dashboard | 0 | 9 |
| Resume Improvement Recommendations | 0 | 6 |
| UI/UX & Error Handling | 0 | 7 |

## **Feature 1 — User Authentication & Profile**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | User Registration | Create account functionality. |
| ☐ | User Login | Allow registered users to log in. |
| ☐ | User Logout | Allow users to log out. |
| ☐ | Authentication | Implement authentication between frontend and backend. |
| ☐ | Protected Routes | Protect private pages from unauthenticated users. |
| ☐ | User Profile | Display and manage user information. |
| ☐ | User Data Storage | Store user data in MongoDB. |

## **Feature 2 — Resume Upload & Management**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Resume Upload UI | Create drag-and-drop/browse interface. |
| ☐ | PDF Upload | Support PDF resumes. |
| ☐ | DOCX Upload | Support DOCX resumes. |
| ☐ | File Validation | Validate file type and size. |
| ☐ | Cloudinary Upload | Upload resume to Cloudinary. |
| ☐ | Upload Status | Display upload progress/status. |
| ☐ | Resume Preview | Allow users to preview uploaded resumes. |
| ☐ | Resume History | Display previous resumes. |
| ☐ | Resume Delete | Allow users to delete resumes. |

## **Feature 3 — Resume Parser**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | PDF Text Extraction | Extract text from PDF resumes. |
| ☐ | DOCX Text Extraction | Extract text from DOCX resumes. |
| ☐ | Text Cleaning | Clean extracted resume text. |
| ☐ | Name Extraction | Extract candidate name. |
| ☐ | Contact Extraction | Extract relevant contact information. |
| ☐ | Education Extraction | Extract degrees and institutions. |
| ☐ | Experience Extraction | Extract work experience. |
| ☐ | Project Extraction | Extract projects and technologies. |
| ☐ | Certification Extraction | Extract certifications. |
| ☐ | Skill Extraction | Extract technical and soft skills. |

## **Feature 4 — AI Resume Analysis**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | AI API Integration | Connect Gemini/OpenAI API. |
| ☐ | Resume Analysis Prompt | Create structured AI prompts. |
| ☐ | AI Skill Analysis | Analyze candidate skills. |
| ☐ | Experience Analysis | Analyze experience quality and relevance. |
| ☐ | Education Analysis | Analyze educational background. |
| ☐ | Project Analysis | Analyze projects and technologies. |
| ☐ | Resume Strengths | Identify resume strengths. |
| ☐ | Resume Weaknesses | Identify weaknesses. |
| ☐ | AI Resume Summary | Generate candidate summary. |
| ☐ | Improvement Suggestions | Generate actionable suggestions. |
| ☐ | Structured AI Output | Return AI results in consistent JSON format. |
| ☐ | Save AI Results | Store results in MongoDB. |

## **Feature 5 — Resume Scoring & ATS Analysis**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Overall Resume Score | Generate score out of 100\. |
| ☐ | Skills Score | Score skill relevance. |
| ☐ | Experience Score | Score experience relevance. |
| ☐ | Education Score | Score education relevance. |
| ☐ | Project Score | Score project quality/relevance. |
| ☐ | ATS Score | Estimate ATS compatibility. |
| ☐ | Score Explanation | Explain how scores were generated. |
| ☐ | Score API | Create API to return scoring results. |

## **Feature 6 — Job Database & Job Management**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Job Database Schema | Create MongoDB job structure. |
| ☐ | Sample Job Dataset | Add sample jobs for testing. |
| ☐ | Job Title | Store job titles. |
| ☐ | Company | Store company information. |
| ☐ | Job Description | Store job descriptions. |
| ☐ | Required Skills | Store required skills. |
| ☐ | Experience Requirement | Store required experience. |
| ☐ | Location | Store job location/remote status. |
| ☐ | Job Type | Store internship/full-time/etc. |
| ☐ | Application Link | Store application URL. |
| ☐ | Job API | Create API for retrieving jobs. |

## **Feature 7 — AI Job Matching Engine**

| KEY ENHANCEMENT: SMART SEMANTIC MATCHINGMatching is meaning-based rather than keyword-only. Resume and job-description content is split into small pieces such as skills, bullet points and requirements. Each piece is converted into an embedding, and cosine similarity is used to compare meaning. Exact/keyword matching remains available for requirements that genuinely need exact checks, such as certifications or explicit years of experience. |
| :---- |

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Resume-to-Job Comparison | Compare resume with job requirements. |
| ☐ | Skill Matching | Compare candidate and job skills. |
| ☐ | Skill Match Percentage | Calculate skill compatibility. |
| ☐ | Experience Matching | Compare experience requirements. |
| ☐ | Education Matching | Compare education requirements. |
| ☐ | Weighted Matching | Assign different importance to requirements. |
| ☐ | Overall Match Score | Generate final compatibility score. |
| ☐ | Missing Skills Detection | Identify missing job skills. |
| ☐ | Job Ranking | Rank jobs based on compatibility. |
| ☐ | Save Match Results | Store results in MongoDB. |

| CORE TECHNIQUESentence embeddings \+ cosine similarity, blended with keyword/exact matching. Example: “led a team of 5 engineers” can be recognised as related to “team leadership experience” even when the wording differs. |
| :---- |

## **Feature 8 — Job Recommendation Interface**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Recommended Jobs Page | Display personalized jobs. |
| ☐ | Match Percentage | Display compatibility percentage. |
| ☐ | Matching Skills | Display skills that match. |
| ☐ | Missing Skills | Display missing skills. |
| ☐ | Job Details | Display complete job information. |
| ☐ | Search Jobs | Search by title/company/keyword. |
| ☐ | Filter Jobs | Filter by location/type/match score. |
| ☐ | Sort Jobs | Sort by compatibility. |
| ☐ | Apply Job | Provide external application link. |

| KEY ENHANCEMENT: LIVE JOB BROWSINGProvide current job listings inside the application through legitimate job-aggregator APIs instead of direct scraping of LinkedIn or Naukri. Candidate sources documented in the feature specification are Adzuna API, JSearch via RapidAPI, and Google Jobs via SerpAPI. The app sends search terms such as job title/location and displays returned listings. |
| :---- |

* Adzuna API — documented as having a free tier and global job coverage.  
* JSearch via RapidAPI — documented as aggregating listings from multiple sources.  
* Google Jobs via SerpAPI — documented as paid with a small free tier.  
* Data source principle: legitimate aggregator APIs, not direct LinkedIn/Naukri scraping.

## **Feature 9 — Skill Gap Analysis**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Target Career Selection | Allow user to select desired career/role. |
| ☐ | Identify Skill Gaps | Identify missing skills for target role. |
| ☐ | Skill Gap Priority | Categorize gaps as high/medium/low. |
| ☐ | Career Compatibility | Calculate compatibility with target career. |
| ☐ | Skill Gap Dashboard | Display gaps visually. |
| ☐ | Learning Recommendations | Recommend skills to learn. |
| ☐ | Learning Resources | Provide optional learning resources. |

| KEY ENHANCEMENT: PERSONALISED GAP-TO-LEARNING RECOMMENDATIONSFor each job requirement, a similarity score is produced. Requirements below a configured threshold can be flagged as gaps. A catalog of courses/certifications (including examples such as AWS, Google Cloud, Microsoft, CompTIA, Cisco and general online courses) is searched using the same meaning-based matching approach. The closest resources are ranked, with recognised certifications preferred where possible. The top 2–3 recommendations per gap can then be passed to an AI language model to produce a short explanation. |
| :---- |

## **Feature 10 — Main Dashboard**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Dashboard Layout | Create main dashboard. |
| ☐ | Resume Score Card | Display resume score. |
| ☐ | Skills Count | Display number of detected skills. |
| ☐ | Jobs Matched | Display number of matching jobs. |
| ☐ | Skill Gap Count | Display number of skill gaps. |
| ☐ | Top Job Matches | Display best job matches. |
| ☐ | Resume Summary | Display AI-generated summary. |
| ☐ | Skill Charts | Visualize skill data using Recharts. |
| ☐ | Recent Activity | Display recent system activity. |

## **Feature 11 — Resume Improvement Recommendations**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Resume Strengths | Display strongest resume areas. |
| ☐ | Resume Weaknesses | Display areas requiring improvement. |
| ☐ | Missing Keywords | Identify useful missing keywords. |
| ☐ | Formatting Suggestions | Suggest resume formatting improvements. |
| ☐ | Actionable Recommendations | Provide specific improvement steps. |
| ☐ | Job-Specific Suggestions | Generate suggestions for a selected job. |

## **Feature 12 — UI/UX & Error Handling**

| ✓ | Task | Description |
| :---- | :---- | :---- |
| ☐ | Loading States | Display loading indicators during API/AI processing. |
| ☐ | Error Handling | Display useful error messages. |
| ☐ | Success Messages | Show successful operation messages. |
| ☐ | Empty States | Handle missing resume/job/results. |
| ☐ | Responsive Design | Support desktop, tablet and mobile. |
| ☐ | Navigation | Maintain consistent navigation across the application. |

# **4\. Phase 3 — Final Integration & Testing**

| Start ConditionBegin only after all assigned features have been individually completed and pushed to GitHub. |
| :---- |

| ✓ | Task | Notes |
| :---- | :---- | :---- |
| ☐ | Merge all completed feature branches |  |
| ☐ | Resolve integration conflicts |  |
| ☐ | Connect complete resume pipeline |  |
| ☐ | Connect AI analysis with dashboard |  |
| ☐ | Connect resume data with matching engine |  |
| ☐ | Connect matching results with recommendations |  |
| ☐ | Connect skill gaps with recommendations |  |
| ☐ | Complete end-to-end testing |  |
| ☐ | API testing |  |
| ☐ | Resume upload testing |  |
| ☐ | AI response testing |  |
| ☐ | Job matching accuracy testing |  |
| ☐ | Database testing |  |
| ☐ | Cloudinary testing |  |
| ☐ | Responsive UI testing |  |
| ☐ | Security testing |  |
| ☐ | Production testing |  |

# **5\. GitHub Workflow for Every Feature**

**1\. Feature Assigned**  ↓

**2\. Create Feature Branch**  ↓

**3\. Develop Complete Feature**  ↓

**4\. Test Locally**  ↓

**5\. Fix Bugs**  ↓

**6\. Commit Changes**  ↓

**7\. Push to GitHub**  ↓

**8\. Code Review / Verification**  ↓

**9\. Merge**  ↓

**10\. Mark Feature ✓**  ↓

**11\. Assign / Start Next Feature**

| TEAM RULEA team member completes the assigned feature end-to-end. The documented example shows Member 2 developing AI Resume Analysis, testing it, committing, pushing, merging and marking it complete; the next unassigned feature can then be taken by that member. |
| :---- |

# **6\. Final Project Architecture**

* User  
* React.js Frontend  
* REST API  
* FastAPI Backend  
* Backend services connect to:

* Cloudinary — resumes/files  
* MongoDB — users, resumes, jobs, results  
* AI Model — Gemini/OpenAI

* Deployment: GitHub → Vercel (React Frontend) and Render (FastAPI Backend)

| ARCHITECTURE SUMMARYUSER → React.js Frontend → REST API → FastAPI Backend → {Cloudinary, MongoDB, Gemini/OpenAI}. Deployment uses GitHub, Vercel and Render. |
| :---- |

# **7\. Core Application Flow**

**Upload Resume**

**↓**

**Cloudinary**

**↓**

**Resume Parser**

**↓**

**AI Resume Analysis**

**↓**

**Resume Score**

**↓**

**Skills \+ Experience \+ Education**

**↓**

**Job Matching Engine**

**↓**

**Match Percentage**

**↓**

**Recommended Jobs**

**↓**

**Skill Gap Analysis**

**↓**

**Learning / Career Recommendations**

**↓**

**React Dashboard**

# **8\. Consolidated Feature Highlights**

| Feature | What the user gets |
| :---- | :---- |
| **Smart Matching** | Meaning-based matching using embeddings \+ cosine similarity, blended with exact matching. |
| **Live Job Browsing** | Current listings through legitimate aggregator APIs rather than direct LinkedIn/Naukri scraping. |
| **AI Resume Analysis** | Structured analysis of skills, experience, education and projects, with strengths, weaknesses, summary and suggestions. |
| **Resume & ATS Scoring** | Overall, skill, experience, education and project scores plus ATS compatibility and explanations. |
| **Skill Gap Analysis** | Automatic identification and prioritisation of missing skills. |
| **Personalised Learning** | Course/certification matching and AI-written explanations for recommended learning actions. |
| **Job Recommendations** | Search, filter, sort and apply through external job links. |
| **Dashboard** | Resume score, skills, matching jobs, gaps, top matches, AI summary, charts and activity. |

# **9\. Final Completion Checklist**

* ☐ Phase 1 foundation is operational.  
* ☐ All 12 feature modules are implemented and individually tested.  
* ☐ Semantic job matching and exact-match checks are integrated.  
* ☐ Live job browsing is connected through a legitimate aggregator API.  
* ☐ Skill gaps connect to personalised learning/certification recommendations.  
* ☐ All feature branches are reviewed and merged.  
* ☐ End-to-end resume → analysis → matching → recommendation flow passes testing.  
* ☐ Production frontend and backend are connected.  
* ☐ Responsive UI, API, database, Cloudinary and security testing are completed.