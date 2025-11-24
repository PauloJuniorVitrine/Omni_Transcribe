from pathlib import Path

from infrastructure.container import components_storage


class _Settings:
    persistence_backend = "file"
    profiles_dir: Path

    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir


def test_build_repositories_file_backend(tmp_path):
    settings = _Settings(profiles_dir=tmp_path)
    job_repo, artifact_repo, log_repo, review_repo, profile_provider = components_storage.build_repositories(
        tmp_path, settings
    )
    assert job_repo.__class__.__name__.startswith("File")
    assert artifact_repo.__class__.__name__.startswith("File")
    assert log_repo.__class__.__name__.startswith("File")
    assert review_repo.__class__.__name__.startswith("File")
    assert profile_provider is not None
