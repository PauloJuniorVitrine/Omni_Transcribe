from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SummaryCounters(BaseModel):
    total: int
    awaiting_review: int
    approved: int
    failed: int


class AccuracySummary(BaseModel):
    evaluated: int
    needs_review: int
    passing: int
    average_score: Optional[float] = None
    average_wer: Optional[float] = None


class DashboardSummaryResponse(BaseModel):
    summary: SummaryCounters
    accuracy: AccuracySummary
    generated_at: datetime


class IncidentPayload(BaseModel):
    job_id: str
    event: str
    level: str
    message: str = ""
    timestamp: str
    timestamp_human: str
    icon: str = ""


class DashboardIncidentsResponse(BaseModel):
    items: List[IncidentPayload]
    generated_at: datetime

class JobFeedItem(BaseModel):
    id: str
    source_name: str
    profile_id: str
    status: str
    language: Optional[str] = None
    accuracy_status: Optional[str] = None
    accuracy_score: Optional[float] = None
    accuracy_wer: Optional[float] = None
    accuracy_requires_review: bool = False
    updated_at: str


class JobsFeedResponse(BaseModel):
    jobs: List[JobFeedItem]
    summary: SummaryCounters
    accuracy: AccuracySummary
    page: int
    limit: int
    has_more: bool
    generated_at: datetime


class LogEntryPayload(BaseModel):
    timestamp: str
    level: str
    event: str
    message: Optional[str] = None


class JobLogsResponse(BaseModel):
    job_id: str
    filters: Dict[str, Any]
    page: int
    page_size: int
    total: int
    has_more: bool
    generated_at: datetime
    logs: List[LogEntryPayload]


class ProcessJobResponse(BaseModel):
    job_id: str
    status: str


class UploadTokenResponse(BaseModel):
    token: str
    expires: str
    profile: str
    engine: str
    expires_in_minutes: int


class UploadJobResponse(BaseModel):
    job_id: str
    status: str
    profile_id: str
    auto_processed: bool


class TemplateRawResponse(BaseModel):
    id: str
    name: str
    description: str
    body: str
    locale: Optional[str] = None


class TemplatePreviewResponse(BaseModel):
    rendered: str


class UpdateTemplateResponse(BaseModel):
    status: str
    template: Dict[str, str]
    updated_at: Optional[str] = None
    updated_at_human: Optional[str] = None
    message: Optional[str] = None


class UpdateLocaleResponse(BaseModel):
    status: str
    locale: Optional[str]
    updated_at: Optional[str] = None
    updated_at_human: Optional[str] = None
    message: Optional[str] = None
