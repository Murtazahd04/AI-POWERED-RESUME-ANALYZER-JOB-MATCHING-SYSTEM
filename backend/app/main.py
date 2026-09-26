from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import close, connect
from .routes import auth_routes, health_routes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect()
    yield
    await close()


app = FastAPI(title="AI Resume Analyzer API", lifespan=lifespan)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router)
app.include_router(auth_routes.router)


# Turns FastAPI's technical validation errors into one plain sentence,
# e.g. "password: Password must contain at least one letter and one number."
@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    msg = first["msg"]
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    field = ".".join(str(p) for p in first["loc"] if p != "body")
    detail = f"{field}: {msg}" if field else msg
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/")
async def root():
    return {"name": "AI Resume Analyzer API", "docs": "/docs"}