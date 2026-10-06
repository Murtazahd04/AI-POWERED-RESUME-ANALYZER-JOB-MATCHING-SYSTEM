import re
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _validate_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _require_profile_field(self):
        if self.name is None and self.email is None:
            raise ValueError("Provide a name or email address to update.")
        return self


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class ResumeContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None
    phone: str | None = Field(max_length=40)
    linkedin: str | None = Field(max_length=500)
    github: str | None = Field(max_length=500)


class ResumeEducationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    degree: str | None = Field(max_length=200)
    institution: str | None = Field(max_length=200)
    year: str | None = Field(max_length=40)


class ResumeExperienceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(max_length=200)
    date_range: str = Field(max_length=120)
    highlights: list[Annotated[str, Field(max_length=500)]] = Field(max_length=30)
    technologies: list[Annotated[str, Field(max_length=80)]] = Field(max_length=50)


class ResumeProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: list[Annotated[str, Field(max_length=500)]] = Field(max_length=30)
    technologies: list[Annotated[str, Field(max_length=80)]] = Field(max_length=50)


class ResumeSkillsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical: list[Annotated[str, Field(max_length=80)]] = Field(max_length=100)
    soft: list[Annotated[str, Field(max_length=80)]] = Field(max_length=100)


class ParsedResumeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(max_length=120)
    contact: ResumeContactUpdate
    summary: str | None = Field(max_length=2000)
    education: list[ResumeEducationUpdate] = Field(max_length=20)
    experience: list[ResumeExperienceUpdate] = Field(max_length=50)
    total_experience_years: float = Field(ge=0, le=100)
    projects: list[ResumeProjectUpdate] = Field(max_length=50)
    certifications: list[Annotated[str, Field(max_length=300)]] = Field(max_length=50)
    skills: ResumeSkillsUpdate


class ReparseRequest(BaseModel):
    parser: Literal["spacy", "ai"]
