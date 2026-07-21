"""Data storage layer for raw GitHub API responses."""

import json
from pathlib import Path
from typing import Any, Optional, Union


class DataStorageError(Exception):
    """Exception raised when data storage operations fail."""


class DataStorage:
    """Save and load raw GitHub API responses."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None) -> None:
        base_dir = Path(raw_dir) if raw_dir is not None else Path(__file__).resolve().parents[1] / "data" / "raw"
        self.raw_dir = base_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _save_json(self, filename: str, data: Any) -> Path:
        """Save JSON data to a file in the raw data directory."""
        file_path = self.raw_dir / filename
        try:
            with file_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise DataStorageError(f"Unable to save data to {file_path}") from exc
        return file_path

    def save_repository(self, owner: str, repo: str, data: Any) -> Path:
        """Save repository response data to raw JSON."""
        filename = f"{owner}_{repo}_repository.json"
        return self._save_json(filename, data)

    def save_contributors(self, owner: str, repo: str, data: Any) -> Path:
        """Save contributor response data to raw JSON."""
        filename = f"{owner}_{repo}_contributors.json"
        return self._save_json(filename, data)

    def save_commits(self, owner: str, repo: str, data: Any) -> Path:
        """Save commit response data to raw JSON."""
        filename = f"{owner}_{repo}_commits.json"
        return self._save_json(filename, data)

    def save_issues(self, owner: str, repo: str, data: Any) -> Path:
        """Save issue response data to raw JSON."""
        filename = f"{owner}_{repo}_issues.json"
        return self._save_json(filename, data)

    def save_languages(self, owner: str, repo: str, data: Any) -> Path:
        """Save language response data to raw JSON."""
        filename = f"{owner}_{repo}_languages.json"
        return self._save_json(filename, data)

    def load_json(self, filename: Union[str, Path]) -> Any:
        """Load a JSON file from the raw data directory."""
        file_path = Path(filename)
        if not file_path.is_absolute():
            file_path = self.raw_dir / file_path

        try:
            with file_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError as exc:
            raise DataStorageError(f"JSON file not found: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise DataStorageError(f"Invalid JSON in file: {file_path}") from exc
        except OSError as exc:
            raise DataStorageError(f"Unable to read JSON file: {file_path}") from exc
