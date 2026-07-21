"""Data cleaning and transformation for GitHub repository data."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class DataCleaningError(Exception):
    """Exception raised when data cleaning operations fail."""


class DataCleaner:
    """Transform raw GitHub JSON into cleaned Pandas DataFrames."""

    def __init__(
        self,
        raw_dir: Optional[Union[str, Path]] = None,
        processed_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.raw_dir = Path(raw_dir) if raw_dir is not None else Path(__file__).resolve().parents[1] / "data" / "raw"
        self.processed_dir = Path(processed_dir) if processed_dir is not None else Path(__file__).resolve().parents[1] / "data" / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, filename: Union[str, Path]) -> Any:
        """Load raw JSON from the storage layer."""
        file_path = Path(filename)
        if not file_path.is_absolute():
            file_path = self.raw_dir / file_path

        try:
            with file_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError as exc:
            raise DataCleaningError(f"Raw JSON file not found: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise DataCleaningError(f"Invalid JSON content in file: {file_path}") from exc
        except OSError as exc:
            raise DataCleaningError(f"Unable to open raw file: {file_path}") from exc

    def _save_dataframe(self, filename: str, df: pd.DataFrame) -> Path:
        """Save cleaned DataFrame to the processed directory."""
        file_path = self.processed_dir / filename
        try:
            df.to_csv(file_path, index=False)
        except OSError as exc:
            raise DataCleaningError(f"Unable to save cleaned data to {file_path}") from exc
        return file_path

    def _to_datetime(self, series: pd.Series) -> pd.Series:
        return pd.to_datetime(series, errors="coerce", utc=True)

    def clean_repository(self, owner: str, repo: str) -> pd.DataFrame:
        """Clean raw repository JSON and return a DataFrame."""
        file_name = f"{owner}_{repo}_repository.json"
        raw_data = self.load_json(file_name)

        if isinstance(raw_data, list):
            records = raw_data
        else:
            records = [raw_data]

        if not records:
            return pd.DataFrame()

        raw_dict = records[0]
        owner_data = raw_dict.get("owner", {}) or {}
        license_data = raw_dict.get("license") or {}
        cleaned = {
            "repository_id": raw_dict.get("id"),
            "repository_name": raw_dict.get("name"),
            "full_name": raw_dict.get("full_name"),
            "owner_login": owner_data.get("login"),
            "owner_id": owner_data.get("id"),
            "description": raw_dict.get("description"),
            "repository_url": raw_dict.get("html_url"),
            "stars": raw_dict.get("stargazers_count"),
            "forks": raw_dict.get("forks_count"),
            "watchers": raw_dict.get("watchers_count"),
            "open_issues": raw_dict.get("open_issues_count"),
            "language": raw_dict.get("language"),
            "license": license_data.get("spdx_id") or license_data.get("name"),
            "created_at": raw_dict.get("created_at"),
            "updated_at": raw_dict.get("updated_at"),
            "pushed_at": raw_dict.get("pushed_at"),
            "visibility": raw_dict.get("visibility") or ("private" if raw_dict.get("private") else "public"),
            "size": raw_dict.get("size"),
            "default_branch": raw_dict.get("default_branch"),
        }

        df = pd.DataFrame([cleaned])
        df["created_at"] = self._to_datetime(df["created_at"])
        df["updated_at"] = self._to_datetime(df["updated_at"])
        df["pushed_at"] = self._to_datetime(df["pushed_at"])

        return df

    def clean_commits(self, owner: str, repo: str) -> pd.DataFrame:
        """Clean raw commit JSON and return a DataFrame."""
        file_name = f"{owner}_{repo}_commits.json"
        raw_data = self.load_json(file_name)

        if not isinstance(raw_data, list):
            return pd.DataFrame()

        records: List[Dict[str, Any]] = []
        for item in raw_data:
            commit = item.get("commit", {}) or {}
            author_info = commit.get("author", {}) or {}
            committer_info = commit.get("committer", {}) or {}
            author = item.get("author") or {}
            committer = item.get("committer") or {}

            records.append(
                {
                    "sha": item.get("sha"),
                    "author_login": author.get("login"),
                    "author_id": author.get("id"),
                    "committer_login": committer.get("login"),
                    "committer_id": committer.get("id"),
                    "commit_author_name": author_info.get("name"),
                    "commit_author_email": author_info.get("email"),
                    "commit_author_date": author_info.get("date"),
                    "commit_committer_name": committer_info.get("name"),
                    "commit_committer_email": committer_info.get("email"),
                    "commit_committer_date": committer_info.get("date"),
                    "message": commit.get("message"),
                    "url": item.get("html_url"),
                    "comments": commit.get("comment_count"),
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df["commit_author_date"] = self._to_datetime(df["commit_author_date"])
        df["commit_committer_date"] = self._to_datetime(df["commit_committer_date"])
        df = df.drop_duplicates(subset=["sha"])
        df = df.fillna(value={
            "author_login": "",
            "committer_login": "",
            "message": "",
        })

        return df

    def clean_contributors(self, owner: str, repo: str) -> pd.DataFrame:
        """Clean raw contributor JSON and return a DataFrame."""
        file_name = f"{owner}_{repo}_contributors.json"
        raw_data = self.load_json(file_name)

        if not isinstance(raw_data, list):
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        if df.empty:
            return df

        columns = ["login", "id", "contributions", "type", "site_admin"]
        available = [col for col in columns if col in df.columns]
        df = df[available].drop_duplicates(subset=["login"])
        df = df.fillna({"type": "", "site_admin": False})

        return df

    def clean_issues(self, owner: str, repo: str) -> pd.DataFrame:
        """Clean raw issue JSON and return a DataFrame."""
        file_name = f"{owner}_{repo}_issues.json"
        raw_data = self.load_json(file_name)

        if not isinstance(raw_data, list):
            return pd.DataFrame()

        records: List[Dict[str, Any]] = []
        for item in raw_data:
            user = item.get("user") or {}
            assignee = item.get("assignee") or {}
            pull_request = item.get("pull_request") or {}
            records.append(
                {
                    "issue_id": item.get("id"),
                    "issue_number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "comments": item.get("comments"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "closed_at": item.get("closed_at"),
                    "user_login": user.get("login"),
                    "user_id": user.get("id"),
                    "assignee_login": assignee.get("login"),
                    "assignee_id": assignee.get("id"),
                    "is_pull_request": bool(pull_request),
                    "pull_request_merged_at": pull_request.get("merged_at"),
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df["created_at"] = self._to_datetime(df["created_at"])
        df["updated_at"] = self._to_datetime(df["updated_at"])
        df["closed_at"] = self._to_datetime(df["closed_at"])
        df["pull_request_merged_at"] = self._to_datetime(df["pull_request_merged_at"])
        df = df.drop_duplicates(subset=["issue_id"])
        df = df.fillna({"title": "", "state": "", "comments": 0})
        if "pull_request_merged_at" not in df.columns:
            df["pull_request_merged_at"] = pd.NaT

        return df

    def save_cleaned_repository(self, owner: str, repo: str) -> Path:
        """Clean and save repository data."""
        df = self.clean_repository(owner, repo)
        return self._save_dataframe(f"{owner}_{repo}_repository.csv", df)

    def save_cleaned_commits(self, owner: str, repo: str) -> Path:
        """Clean and save commits data."""
        df = self.clean_commits(owner, repo)
        return self._save_dataframe(f"{owner}_{repo}_commits.csv", df)

    def save_cleaned_contributors(self, owner: str, repo: str) -> Path:
        """Clean and save contributors data."""
        df = self.clean_contributors(owner, repo)
        return self._save_dataframe(f"{owner}_{repo}_contributors.csv", df)

    def save_cleaned_issues(self, owner: str, repo: str) -> Path:
        """Clean and save issues data."""
        df = self.clean_issues(owner, repo)
        return self._save_dataframe(f"{owner}_{repo}_issues.csv", df)

    def clean_languages(self, owner: str, repo: str) -> pd.DataFrame:
        """Clean raw language JSON and return a DataFrame."""
        file_name = f"{owner}_{repo}_languages.json"
        raw_data = self.load_json(file_name)

        if not isinstance(raw_data, dict):
            return pd.DataFrame()

        records = [
            {"language": key, "bytes": int(value or 0)}
            for key, value in raw_data.items()
        ]

        df = pd.DataFrame(records)
        if df.empty:
            return df

        return df.sort_values("bytes", ascending=False).reset_index(drop=True)

    def save_cleaned_languages(self, owner: str, repo: str) -> Path:
        """Clean and save languages data."""
        df = self.clean_languages(owner, repo)
        return self._save_dataframe(f"{owner}_{repo}_languages.csv", df)
