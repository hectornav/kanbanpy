"""
schemas.py - Pydantic request/response models for the API.
"""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=256)
    security_q: str = ""
    security_a: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotResetRequest(BaseModel):
    username: str
    answer: str
    new_password: str = Field(min_length=4, max_length=256)


class UserOut(BaseModel):
    id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "#5b8cff"


class BoardUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    color: str | None = None
    is_shared: bool | None = None
    member_ids: list[int] | None = None


class TaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    description: str = ""
    priority: str = "Medium"
    tags: list[str] = []
    due_date: str = ""
    column_name: str = "ToDo"
    assignee_id: int | None = None
    recurrence: str = ""


class SubtaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class SubtaskUpdate(BaseModel):
    text: str | None = Field(default=None, max_length=300)
    done: bool | None = None


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class AiPlanRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=2000)


class AiConfigIn(BaseModel):
    provider: str = "anthropic"  # "anthropic" | "ollama"
    anthropic_api_key: str | None = None  # None/empty = keep existing (write-only)
    anthropic_model: str | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None


class MoveRequest(BaseModel):
    column_name: str
    sort_order: int | None = None


class ReorderRequest(BaseModel):
    board_id: int
    column_name: str
    ordered_ids: list[int]
