from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.user_review import UserReview
from domain.ports.repositories import ArtifactRepository, JobRepository, LogRepository, ReviewRepository

from .serializers import (
    artifact_from_dict,
    artifact_to_dict,
    job_from_dict,
    job_to_dict,
    logentry_from_dict,
    logentry_to_dict,
    review_from_dict,
    review_to_dict,
)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


class SqlJobRepository(JobRepository):
    def __init__(self, db_path: Path) -> None:
        self.conn = _connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def create(self, job: Job) -> Job:
        payload = json.dumps(job_to_dict(job), ensure_ascii=False)
        self.conn.execute("INSERT OR REPLACE INTO jobs (id, payload) VALUES (?, ?)", (job.id, payload))
        self.conn.commit()
        return job

    def update(self, job: Job) -> Job:
        payload = json.dumps(job_to_dict(job), ensure_ascii=False)
        self.conn.execute("INSERT OR REPLACE INTO jobs (id, payload) VALUES (?, ?)", (job.id, payload))
        self.conn.commit()
        return job

    def find_by_id(self, job_id: str) -> Optional[Job]:
        cur = self.conn.execute("SELECT payload FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        return job_from_dict(json.loads(row[0])) if row else None

    def list_recent(self, limit: int = 50) -> List[Job]:
        cur = self.conn.execute("SELECT payload FROM jobs ORDER BY json_extract(payload, '$.updated_at') DESC LIMIT ?", (limit,))
        return [job_from_dict(json.loads(row[0])) for row in cur.fetchall()]


class SqlArtifactRepository(ArtifactRepository):
    def __init__(self, db_path: Path) -> None:
        self.conn = _connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )

    def save_many(self, artifacts: Iterable[Artifact]) -> None:
        rows = []
        for artifact in artifacts:
            payload = json.dumps(artifact_to_dict(artifact), ensure_ascii=False)
            rows.append((artifact.id, artifact.job_id, payload))
        self.conn.executemany("INSERT OR REPLACE INTO artifacts (id, job_id, payload) VALUES (?, ?, ?)", rows)
        self.conn.commit()

    def list_by_job(self, job_id: str) -> List[Artifact]:
        cur = self.conn.execute("SELECT payload FROM artifacts WHERE job_id = ?", (job_id,))
        return [artifact_from_dict(json.loads(row[0])) for row in cur.fetchall()]


class SqlLogRepository(LogRepository):
    def __init__(self, db_path: Path) -> None:
        self.conn = _connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )

    def append(self, entry: LogEntry) -> None:
        payload = json.dumps(logentry_to_dict(entry), ensure_ascii=False)
        self.conn.execute("INSERT INTO logs (job_id, payload) VALUES (?, ?)", (entry.job_id, payload))
        self.conn.commit()

    def list_by_job(self, job_id: str) -> List[LogEntry]:
        cur = self.conn.execute("SELECT payload FROM logs WHERE job_id = ? ORDER BY id DESC", (job_id,))
        return [logentry_from_dict(json.loads(row[0])) for row in cur.fetchall()]

    def list_recent(self, limit: int = 20) -> List[LogEntry]:
        cur = self.conn.execute("SELECT payload FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        return [logentry_from_dict(json.loads(row[0])) for row in cur.fetchall()]


class SqlReviewRepository(ReviewRepository):
    def __init__(self, db_path: Path) -> None:
        self.conn = _connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                job_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

    def save(self, review: UserReview) -> UserReview:
        payload = json.dumps(review_to_dict(review), ensure_ascii=False)
        self.conn.execute("INSERT OR REPLACE INTO reviews (job_id, payload) VALUES (?, ?)", (review.job_id, payload))
        self.conn.commit()
        return review

    def find_latest(self, job_id: str) -> Optional[UserReview]:
        cur = self.conn.execute("SELECT payload FROM reviews WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        return review_from_dict(json.loads(row[0])) if row else None
