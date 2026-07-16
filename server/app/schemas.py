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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str


class TaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    description: str = ""
    priority: str = "Medium"
    tags: list[str] = []
    due_date: str = ""
    column_name: str = "ToDo"
    is_shared: bool = False
    shared_user_ids: list[int] | None = None


class MoveRequest(BaseModel):
    column_name: str
    sort_order: int | None = None


class ReorderRequest(BaseModel):
    column_name: str
    ordered_ids: list[int]


TokenResponse.model_rebuild()
