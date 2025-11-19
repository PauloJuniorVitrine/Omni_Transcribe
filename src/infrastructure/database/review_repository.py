from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from domain.entities.user_review import UserReview
from domain.ports.repositories import ReviewRepository

from .serializers import review_from_dict, review_to_dict
from . import file_storage


class FileReviewRepository(ReviewRepository):
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def save(self, review: UserReview) -> UserReview:
        data = self._load_all()
        data.append(review_to_dict(review))
        self._save_all(data)
        return review

    def find_latest(self, job_id: str) -> Optional[UserReview]:
        data = self._load_all()
        filtered = [review_from_dict(item) for item in data if item["job_id"] == job_id]
        if not filtered:
            return None
        return sorted(filtered, key=lambda item: item.timestamp, reverse=True)[0]

    def _load_all(self) -> List[dict]:
        return file_storage.read_json_list(self.storage_path)

    def _save_all(self, data: List[dict]) -> None:
        file_storage.write_json_list(self.storage_path, data)
