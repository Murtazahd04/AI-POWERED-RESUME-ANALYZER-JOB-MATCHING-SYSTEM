# AI-Powered Resume Analyzer & Job Matching System

This project is a full-stack application built with React for the frontend and FastAPI for the backend. It helps users upload resumes, analyze them using AI, compare them against job descriptions, identify skill gaps, and get role-based recommendations.

This repository is structured for team collaboration and includes a project development tracker in the root folder so each teammate can mark tasks as they complete them.

## Important for your teammate

Please open the development tracker file at the project root:

- Data Science Project.md
- Current file in this repository: Data Science Project.docx.md

This file contains the project setup tasks that are already completed and the feature checklist for the upcoming development work. Please update the checkbox status as you finish each task. This file should also be used as the working reference when developing features with AI tools.

> If your teammate prefers a cleaner name for AI-assisted work, keep the checklist in this file and update it consistently while developing.

## Deployment

- Frontend: Vercel
- Backend: Render

Make sure to check the live app and API after deployment, and confirm the production environment variables are correctly configured.

---

## 1. Clone the project

Open Command Prompt or Git Bash and run:

```bash
git clone <your-github-repository-url>
cd "Data Science Project"
```

If your folder path contains spaces, keep it in quotes as shown above.

---

## 2. Backend setup

### 2.1 Create and activate the virtual environment

#### Command Prompt / PowerShell

```bash
cd backend
python -m venv venv
venv\Scripts\activate
```

#### Git Bash

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
```

### 2.2 Install backend dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Configure environment variables

Create a `.env` file in the `backend` folder using the sample file:

#### Command Prompt / PowerShell

```bash
copy .env.example .env
```

#### Git Bash

```bash
cp .env.example .env
```

Then update the values inside `.env` with your own credentials:

```env
MONGODB_URL=your_mongodb_connection_string
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
AI_API_KEY=your_ai_api_key
AI_MODEL_NAME=gemini-2.5-flash
PYTHON_VERSION=3.13
FRONTEND_URL=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 2.4 Start the backend

#### Command Prompt / PowerShell

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Git Bash

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend should run at:

- http://localhost:8000
- API docs: http://localhost:8000/docs

---

## 3. Frontend setup

Open a new terminal window for the frontend.

### 3.1 Install frontend dependencies

```bash
cd frontend
npm install
```

### 3.2 Start the frontend development server

#### Command Prompt / PowerShell

```bash
npm run dev -- --host
```

#### Git Bash

```bash
npm run dev -- --host
```

Frontend should run at:

- http://localhost:5173

If needed, you can also build the frontend for production:

```bash
npm run build
```

---

## 4. Full setup flow for teammates

Use these commands in order.

### Command Prompt / PowerShell

```bash
git clone <your-github-repository-url>
cd "Data Science Project"

cd backend
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env

cd ..
cd frontend
npm install

cd ..
start "Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
start "Frontend" cmd /k "cd frontend && npm run dev -- --host"
```

### Git Bash

```bash
git clone <your-github-repository-url>
cd "Data Science Project"

cd backend
python -m venv venv
source venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env

cd ../frontend
npm install

# Start backend in one terminal
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend in another terminal
cd ../frontend
npm run dev -- --host
```

---

## 5. How to use the development checklist

The team should use the tracker file in the root folder:

- Data Science Project.md
- Current repository file: Data Science Project.docx.md

Instructions:

1. Open the file before starting work.
2. Review the setup tasks already marked as completed.
3. Check the box next to each feature as it is completed.
4. Keep the checklist updated after every milestone.
5. Use the file with AI tools to generate implementation help, feature breakdowns, and follow-up tasks.

This is meant to keep progress visible, organized, and aligned between team members.

---

## 6. Project structure

### Root folder

```text
Data Science Project/
├── README.md
├── Data Science Project.docx.md
├── render.yaml
├── backend/
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── routes/
│   │   │   └── media.py
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   └── cloudinary_service.py
│   │   └── ...
│   └── venv/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   ├── src/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── assets/
│   │   ├── components/
│   │   │   └── FileUpload.jsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── JobsPage.jsx
│   │   │   ├── ProfilePage.jsx
│   │   │   ├── ResumePage.jsx
│   │   │   └── SkillsPage.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   └── utils/
│   └── ...
└── .gitignore
```

### Backend structure description

- `backend/app/main.py`  
  Main FastAPI application entry point.

- `backend/app/core/config.py`  
  Environment configuration and app settings.

- `backend/app/core/database.py`  
  MongoDB database connection setup.

- `backend/app/routes/media.py`  
  API routes for media, uploads, and related requests.

- `backend/app/services/ai_service.py`  
  AI-powered analysis logic and model integration.

- `backend/app/services/cloudinary_service.py`  
  File upload logic and Cloudinary integration.

- `backend/requirements.txt`  
  All Python dependencies for the backend.

### Frontend structure description

- `frontend/src/App.jsx`  
  Main React application component and route setup.

- `frontend/src/main.jsx`  
  App bootstrap file for rendering the React app.

- `frontend/src/pages/`  
  Different application pages such as Dashboard, Jobs, Profile, Resume, and Skills.

- `frontend/src/components/`  
  Reusable frontend UI components.

- `frontend/src/services/api.js`  
  API calls to the backend.

- `frontend/src/assets/`  
  Static visual assets for the app.

- `frontend/src/utils/`  
  Helper functions and utility logic.

- `frontend/package.json`  
  Frontend scripts and dependency list.

---

## 7. Common development commands

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Git Bash
venv\Scripts\activate          # Command Prompt / PowerShell
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host
```

---

## 8. Team workflow notes

- Always update the checklist file after completing a milestone.
- Keep commits small and feature-based.
- Use the project tracker for AI-assisted planning and feature development tasks.
- Verify both frontend and backend work together before pushing final changes.
- Make sure environment variables are configured before running the app.

---

## 9. Final checklist before deployment

Before submitting work, confirm:

- Backend environment variables are correctly set.
- MongoDB is connected.
- Cloudinary is configured.
- AI API key is valid.
- Frontend is connected to the correct backend URL.
- Vercel and Render environment variables are configured correctly.
- Feature status is updated in the development tracker file.

This project is ready for the team to continue development and feature delivery using the checklist and setup steps above.
