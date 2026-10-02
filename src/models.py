from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TableModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Assignment(TableModel):
    assignment_id: str
    employee_id: str
    category: str
    asset_tag: str | None = None
    status: str | None = None
    assigned_on: date | None = None


class Staff(TableModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    name: str
    role: str
    hire_date: date
    department: str | None = None
    equipment: list[Assignment] | None = Field(default_factory=list)


class PolicyLimit(TableModel):
    role: str
    category: str
    cap_active: int
    refresh_years: int | None = None
    policy_rule: str | None = None


class ReviewStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class ReviewTicket(TableModel):
    review_ticket_id: str
    employee_id: str
    request: str
    reason: str
    status: ReviewStatus = ReviewStatus.OPEN
