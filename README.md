# AI-POWERED-RESUME-ANALYZER-JOB-MATCHING-SYSTEM

## Backend setup and startup

From the project root, open PowerShell and run:

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m uvicorn app.main:app --reload
```

For subsequent starts, activate the existing environment and run the server:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

## AI resume analysis

Authenticated resume-analysis endpoints return a consistent response envelope:

```json
{
  "id": "resume-id",
  "analysis": {
    "type": "improvement_suggestions",
    "result": {},
    "generated_at": "2026-10-03T12:00:00+00:00"
  }
}
```

Validated analysis results are saved on the owned resume document under
`ai_results`, and the resume detail page restores them when reopened. Editing
parsed resume details or reparsing clears saved analyses so outdated results
are not shown. Improvement suggestions are grouped by resume section and can
be downloaded from the detail page as a paginated PDF report.

The parser uses spaCy's `en_core_web_sm` English model. Install it once in the
backend virtual environment with the command above. The API is available at
`http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

If using Git Bash, the equivalent first-time setup and startup commands are:

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m uvicorn app.main:app --reload
```