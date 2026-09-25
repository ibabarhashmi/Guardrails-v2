"""Strict request/response schemas.

Only ``role: "user"`` is accepted from clients. ``system``/``assistant``/
``tool`` roles are rejected at validation (OWASP LLM01: prompt injection via
role spoofing). Extra fields are forbidden; lengths are bounded (LLM10).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class UserMessage(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["user"] = Field(
        description="Only the user role is accepted from clients."
    )
    content: Annotated[
        str, Field(min_length=1, max_length=4000, description="User prompt text.")
    ]


class ChatRequest(BaseModel):
    model_config = {"extra": "forbid"}

    messages: Annotated[
        list[UserMessage],
        Field(min_length=1, max_length=10, description="Conversation turns."),
    ]


class PolicyInfo(BaseModel):
    decision: Literal["allow", "deny"] = "allow"
    reason: str = ""
    gate: Literal["none", "input", "output"] = "none"


class ChatResponse(BaseModel):
    """Backward compatible: legacy clients read ``message``; new fields additive."""

    message: str
    request_id: str = ""
    policy: PolicyInfo = PolicyInfo()
