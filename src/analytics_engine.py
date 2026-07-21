"""Analytics engine for repository health metrics."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd


class AnalyticsError(Exception):
    """Exception raised when analytics calculations fail."""


class AnalyticsEngine:
    """Calculate analytics from cleaned GitHub datasets."""

    def __init__(
        self,
        repository_df: Optional[pd.DataFrame] = None,
        commits_df: Optional[pd.DataFrame] = None,
        contributors_df: Optional[pd.DataFrame] = None,
        issues_df: Optional[pd.DataFrame] = None,
        languages_df: Optional[pd.DataFrame] = None,
    ) -> None:
        self.repository_df = repository_df
        self.commits_df = commits_df
        self.contributors_df = contributors_df
        self.issues_df = issues_df
        self.languages_df = languages_df

    @staticmethod
    def _validate_df(df: Optional[pd.DataFrame], name: str) -> pd.DataFrame:
        if df is None:
            raise AnalyticsError(f"{name} DataFrame is required")
        if df.empty:
            raise AnalyticsError(f"{name} DataFrame is empty")
        return df.copy()

    @staticmethod
    def _days_between(start: pd.Timestamp, end: pd.Timestamp) -> int:
        duration = end - start
        return max(int(duration.total_seconds() // 86400), 1)

    def repository_summary(self, repository_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Return summary metrics for the repository."""
        df = self._validate_df(repository_df or self.repository_df, "Repository")
        row = df.iloc[0]
        created_at = pd.to_datetime(row["created_at"], utc=True)
        age_days = (pd.Timestamp.now(tz="UTC") - created_at).days

        return {
            "repository_name": row.get("repository_name"),
            "full_name": row.get("full_name"),
            "owner_login": row.get("owner_login"),
            "stars": int(row.get("stars", 0)),
            "forks": int(row.get("forks", 0)),
            "watchers": int(row.get("watchers", 0)),
            "open_issues": int(row.get("open_issues", 0)),
            "language": row.get("language"),
            "default_branch": row.get("default_branch"),
            "age_days": int(age_days),
            "created_at": created_at.isoformat(),
        }

    def commit_statistics(self, commits_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Return commit analytics from cleaned commits."""
        df = self._validate_df(commits_df or self.commits_df, "Commits")
        df = df.copy()
        df["commit_author_date"] = pd.to_datetime(df["commit_author_date"], utc=True, errors="coerce")

        if df["commit_author_date"].isna().all():
            raise AnalyticsError("Commit dates are missing or invalid")

        first_date = df["commit_author_date"].min()
        last_date = df["commit_author_date"].max()
        total_commits = int(len(df))
        unique_committers = int(df["author_login"].nunique(dropna=True))
        commits_per_contributor = (
            df.groupby("author_login").size().rename("commits").to_dict()
        )
        average_commits_per_day = total_commits / self._days_between(first_date, last_date)

        return {
            "total_commits": total_commits,
            "unique_committers": unique_committers,
            "commits_per_contributor": commits_per_contributor,
            "first_commit_date": first_date.isoformat(),
            "last_commit_date": last_date.isoformat(),
            "average_commits_per_day": round(average_commits_per_day, 2),
        }

    def contributor_statistics(self, contributors_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Return contributor analytics from cleaned contributor data."""
        df = self._validate_df(contributors_df or self.contributors_df, "Contributors")
        df = df.copy()
        df["contributions"] = pd.to_numeric(df["contributions"], errors="coerce").fillna(0).astype(int)

        total_contributors = int(df["login"].nunique(dropna=True))
        total_contributions = int(df["contributions"].sum())
        average_contributions = float(df["contributions"].mean())
        top_contributor = df.sort_values("contributions", ascending=False).iloc[0].to_dict()

        return {
            "total_contributors": total_contributors,
            "total_contributions": total_contributions,
            "average_contributions": round(average_contributions, 2),
            "top_contributor": {
                "login": top_contributor.get("login"),
                "contributions": int(top_contributor.get("contributions", 0)),
            },
        }

    def issue_statistics(self, issues_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Return issue analytics from cleaned issue data."""
        df = self._validate_df(issues_df or self.issues_df, "Issues")
        df = df.copy()
        df["state"] = df["state"].fillna("unknown").astype(str).str.lower()
        if "is_pull_request" in df.columns:
            df = df[df["is_pull_request"] != True]

        total_issues = int(len(df))
        open_issues = int((df["state"] == "open").sum())
        closed_issues = int((df["state"] == "closed").sum())
        issue_close_rate = round(closed_issues / total_issues * 100, 2) if total_issues else 0.0
        average_comments = float(df["comments"].fillna(0).mean()) if total_issues else 0.0

        return {
            "total_issues": total_issues,
            "open_issues": open_issues,
            "closed_issues": closed_issues,
            "issue_close_rate": issue_close_rate,
            "average_comments": round(average_comments, 2),
        }

    def pull_request_statistics(self, issues_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Return pull request analytics from cleaned issue data."""
        df = self._validate_df(issues_df or self.issues_df, "Issues")
        df = df.copy()
        if "is_pull_request" not in df.columns:
            return {
                "total_pull_requests": 0,
                "open_pull_requests": 0,
                "closed_pull_requests": 0,
                "merged_pull_requests": 0,
            }

        pr_df = df[df["is_pull_request"] == True].copy()
        if pr_df.empty:
            return {
                "total_pull_requests": 0,
                "open_pull_requests": 0,
                "closed_pull_requests": 0,
                "merged_pull_requests": 0,
            }

        pr_df["state"] = pr_df["state"].fillna("unknown").astype(str).str.lower()
        merged_prs = 0
        if "pull_request_merged_at" in pr_df.columns:
            merged_prs = int(pd.to_datetime(pr_df["pull_request_merged_at"], errors="coerce").notna().sum())
        elif "closed_at" in pr_df.columns:
            merged_prs = int((pr_df["state"] == "closed").sum())

        return {
            "total_pull_requests": int(len(pr_df)),
            "open_pull_requests": int((pr_df["state"] == "open").sum()),
            "closed_pull_requests": int((pr_df["state"] == "closed").sum()),
            "merged_pull_requests": merged_prs,
        }

    def language_statistics(self, languages_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Return language distribution from cleaned data."""
        df = languages_df if languages_df is not None else self.languages_df
        if df is None:
            raise AnalyticsError("Languages DataFrame is required")
        df = df.copy()
        if "language" not in df.columns or "bytes" not in df.columns:
            raise AnalyticsError("Languages DataFrame must contain 'language' and 'bytes' columns")

        df["bytes"] = pd.to_numeric(df["bytes"], errors="coerce").fillna(0).astype(int)
        total_bytes = df["bytes"].sum()
        df["percentage"] = df["bytes"] / total_bytes * 100 if total_bytes else 0.0
        return df.sort_values("bytes", ascending=False).reset_index(drop=True)

    def activity_summary(self) -> Dict[str, Any]:
        """Return a summary of repository activity across all loaded datasets."""
        summary: Dict[str, Any] = {}
        if self.repository_df is not None and not self.repository_df.empty:
            summary["repository_summary"] = self.repository_summary()
        if self.commits_df is not None and not self.commits_df.empty:
            summary["commit_statistics"] = self.commit_statistics()
        if self.contributors_df is not None and not self.contributors_df.empty:
            summary["contributor_statistics"] = self.contributor_statistics()
        if self.issues_df is not None and not self.issues_df.empty:
            summary["issue_statistics"] = self.issue_statistics()
        if self.languages_df is not None and not self.languages_df.empty:
            summary["language_statistics"] = self.language_statistics()
        return summary
