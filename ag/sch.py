from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ActionType = Literal[
    "navigate",
    "click",
    "type",
    "press",
    "scroll",
    "wait",
    "extract",
    "back",
    "done",
]


class Act(BaseModel):
    model_config = {"extra": "forbid"}
    thought: Optional[str] = None
    action: ActionType
    url: Optional[str] = None
    query: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    key: Optional[str] = None
    ms: Optional[int] = None
    dx: Optional[int] = None
    dy: Optional[int] = None
    field: Optional[str] = None


class Obs(BaseModel):
    url: str = ""
    title: str = ""
    text: str = ""
    step: int = 0
    note: str = ""


class Step(BaseModel):
    act: Act
    obs: Obs


class RunRes(BaseModel):
    goal: str
    steps: list[Step] = Field(default_factory=list)
    answer: str = ""
