"""Repository health scoring based on analytics outputs."""
import logging
from math import log10
from typing import Any, Dict, Optional

import pandas as pd

from src.analytics_engine import AnalyticsEngine, AnalyticsError

logger = logging.getLogger(__name__)


class HealthScoreError(Exception):
    """Exception raised when repository health scoring fails."""


class RepositoryHealthScore:
    """Calculate repository health score from analytics outputs."""

    WEIGHTS = {
        "commit_activity": 0.25,
        "contributor_activity": 0.20,
        "issue_resolution": 0.20,
        "pull_request_success": 0.15,
        "repository_growth": 0.10,
        "community_engagement": 0.10,
    }

    def __init__(self, analytics_engine: AnalyticsEngine) -> None:
        self.analytics_engine = analytics_engine

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _grade(score: float) -> str:
        """Return the legacy descriptive grade label for compatibility."""
        if score >= 90:
            return "Excellent"
        if score >= 80:
            return "Very Healthy"
        if score >= 70:
            return "Healthy"
        if score >= 60:
            return "Fair"
        if score >= 40:
            return "Needs Attention"
        return "Critical"

    @staticmethod
    def _letter_grade(score: float) -> str:
        if score >= 95:
            return "A+"
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 55:
            return "C"
        return "D"

    @staticmethod
    def _safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
        return numerator / denominator if denominator else default

    def commit_score(self) -> float:
        """Score commit activity on a 0-100 scale. Returns 0.0 when no commit data is available."""
        try:
            commit_stats = self.analytics_engine.commit_statistics()
        except AnalyticsError as exc:
            logger.debug(
                "health_score.commit_score: no commit data available (%s). Returning 0.0.",
                exc,
            )
            return 0.0

        average_commits = float(commit_stats.get("average_commits_per_day", 0.0))
        commit_activity = min(100.0, average_commits * 25.0)
        return self._clamp(commit_activity)

    def contributor_score(self) -> float:
        """Score contributor activity on a 0-100 scale. Returns 0.0 when no contributor data is available."""
        try:
            contributor_stats = self.analytics_engine.contributor_statistics()
        except AnalyticsError as exc:
            logger.debug(
                "health_score.contributor_score: no contributor data available (%s). Returning 0.0.",
                exc,
            )
            return 0.0

        total_contributors = float(contributor_stats.get("total_contributors", 0))
        average_contributions = float(contributor_stats.get("average_contributions", 0.0))
        contributor_activity = (
            min(50.0, total_contributors * 2.5)
            + min(50.0, average_contributions * 5.0)
        )
        return self._clamp(contributor_activity)

    def issue_score(self) -> float:
        """Score issue resolution on a 0-100 scale.

        Repositories with no issues (disabled or zero) receive a neutral score of 50.0
        rather than failing — having no issues is not a negative signal.
        """
        try:
            issue_stats = self.analytics_engine.issue_statistics()
        except AnalyticsError as exc:
            logger.debug(
                "health_score.issue_score: no issue data available (%s). "
                "Returning neutral score of 50.0 (no issues is not a negative signal).",
                exc,
            )
            return 50.0

        close_rate = float(issue_stats.get("issue_close_rate", 0.0))
        open_issues = float(issue_stats.get("open_issues", 0))
        total_issues = float(issue_stats.get("total_issues", 0))
        if total_issues == 0:
            # No issues at all — neutral score
            return 50.0
        open_issue_penalty = self._safe_division(open_issues, total_issues) * 50.0
        issue_activity = self._clamp(close_rate * 0.8 + (100.0 - open_issue_penalty) * 0.2)
        return issue_activity

    def pull_request_score(self) -> float:
        """Score pull request activity and success on a 0-100 scale."""
        issues_df = self.analytics_engine.issues_df
        if issues_df is None or issues_df.empty:
            return 50.0

        pr_df = issues_df[issues_df["is_pull_request"] == True]
        if pr_df.empty:
            return 50.0

        closed_prs = int(pr_df[pr_df["state"].str.lower() == "closed"].shape[0])
        total_prs = int(pr_df.shape[0])
        pr_success_rate = self._safe_division(closed_prs, total_prs) * 100.0
        return self._clamp(pr_success_rate)

    def repository_growth_score(self) -> float:
        """Score repository growth based on stars, forks and commit velocity."""
        try:
            repo_summary = self.analytics_engine.repository_summary()
        except AnalyticsError as exc:
            logger.debug(
                "health_score.repository_growth_score: no repository data available (%s). Returning 0.0.",
                exc,
            )
            return 0.0

        stars = float(repo_summary.get("stars", 0) or 0)
        forks = float(repo_summary.get("forks", 0) or 0)

        # Commit velocity is optional — use 0 if commits are unavailable
        commits_per_day = 0.0
        try:
            commit_stats = self.analytics_engine.commit_statistics()
            commits_per_day = float(commit_stats.get("average_commits_per_day", 0.0))
        except AnalyticsError:
            pass

        growth_score = (
            min(50.0, min(stars / 20.0, 50.0))
            + min(30.0, min(forks / 10.0, 30.0))
            + min(20.0, commits_per_day * 5.0)
        )
        return self._clamp(growth_score)

    def community_score(self) -> float:
        """Score community engagement based on contributors, watchers and issue interaction.

        Each sub-signal degrades gracefully to 0 when data is unavailable.
        """
        total_contributors = 0.0
        try:
            contributor_stats = self.analytics_engine.contributor_statistics()
            total_contributors = float(contributor_stats.get("total_contributors", 0) or 0)
        except AnalyticsError as exc:
            logger.debug(
                "health_score.community_score: contributor data unavailable (%s). Using 0.", exc
            )

        watchers = 0.0
        try:
            repo_summary = self.analytics_engine.repository_summary()
            watchers = float(repo_summary.get("watchers", 0) or 0)
        except AnalyticsError as exc:
            logger.debug(
                "health_score.community_score: repository data unavailable (%s). Using 0.", exc
            )

        average_comments = 0.0
        try:
            issue_stats = self.analytics_engine.issue_statistics()
            average_comments = float(issue_stats.get("average_comments", 0.0) or 0.0)
        except AnalyticsError as exc:
            logger.debug(
                "health_score.community_score: issue data unavailable (%s). Using 0.", exc
            )

        return self._clamp(
            min(40.0, total_contributors * 4.0)
            + min(40.0, min(watchers / 50.0, 40.0))
            + min(20.0, average_comments * 4.0)
        )

    def recent_maintenance_score(self) -> float:
        """Score recent maintenance from latest commits, pushes, and recent commit volume."""
        commits_df = self.analytics_engine.commits_df
        repository_df = self.analytics_engine.repository_df
        reference_time = pd.Timestamp.now(tz="UTC")
        latest_signal: Optional[pd.Timestamp] = None
        recent_commits = 0

        if commits_df is not None and not commits_df.empty and "commit_author_date" in commits_df.columns:
            dates = pd.to_datetime(commits_df["commit_author_date"], errors="coerce", utc=True).dropna()
            if not dates.empty:
                latest_signal = dates.max()
                reference_time = max(reference_time, latest_signal)
                recent_commits = int((dates >= reference_time - pd.Timedelta(days=30)).sum())

        if repository_df is not None and not repository_df.empty and "pushed_at" in repository_df.columns:
            pushed_at = pd.to_datetime(repository_df.iloc[0].get("pushed_at"), errors="coerce", utc=True)
            if pd.notna(pushed_at):
                latest_signal = pushed_at if latest_signal is None else max(latest_signal, pushed_at)
                reference_time = max(reference_time, pushed_at)

        if latest_signal is None:
            return 0.0

        days_since_activity = max((reference_time - latest_signal).days, 0)
        if days_since_activity <= 7:
            recency_score = 60.0
        elif days_since_activity <= 30:
            recency_score = 45.0
        elif days_since_activity <= 90:
            recency_score = 25.0
        elif days_since_activity <= 180:
            recency_score = 12.0
        else:
            recency_score = 0.0

        volume_score = min(40.0, recent_commits * 2.0)
        return self._clamp(recency_score + volume_score)

    def maintenance_score(self) -> float:
        """Score project maintenance from recency, commits, issue resolution, and PR flow."""
        return self._clamp(
            self.recent_maintenance_score() * 0.35
            + self.commit_score() * 0.25
            + self.issue_score() * 0.25
            + self.pull_request_score() * 0.15
        )

    def popularity_score(self) -> float:
        """Score repository popularity from stars, forks, and watchers. Returns 0.0 when data is unavailable."""
        try:
            repo_summary = self.analytics_engine.repository_summary()
        except AnalyticsError as exc:
            logger.debug(
                "health_score.popularity_score: no repository data available (%s). Returning 0.0.",
                exc,
            )
            return 0.0

        stars = max(float(repo_summary.get("stars", 0) or 0), 0.0)
        forks = max(float(repo_summary.get("forks", 0) or 0), 0.0)
        watchers = max(float(repo_summary.get("watchers", 0) or 0), 0.0)
        return self._clamp(
            min(50.0, log10(stars + 1.0) / 6.0 * 50.0)
            + min(30.0, log10(forks + 1.0) / 5.5 * 30.0)
            + min(20.0, log10(watchers + 1.0) / 6.0 * 20.0)
        )

    def repository_health_score(self) -> float:
        """Score core repository health from activity, resolution, diversity, and age."""
        age_score = 50.0
        try:
            repo_summary = self.analytics_engine.repository_summary()
            age_days = max(float(repo_summary.get("age_days", 0) or 0), 0.0)
            age_score = min(100.0, age_days / 365.0 * 25.0 + 75.0) if age_days else 50.0
        except AnalyticsError as exc:
            logger.debug(
                "health_score.repository_health_score: no repository data available (%s). "
                "Using default age_score=50.0.",
                exc,
            )

        return self._clamp(
            self.commit_score() * 0.30
            + self.contributor_score() * 0.25
            + self.issue_score() * 0.25
            + self.recent_maintenance_score() * 0.10
            + age_score * 0.10
        )

    def _build_explanation(
        self,
        intelligence_breakdown: Dict[str, float],
        overall_score: float,
    ) -> str:
        strongest_key = max(intelligence_breakdown, key=intelligence_breakdown.get)
        weakest_key = min(intelligence_breakdown, key=intelligence_breakdown.get)
        labels = {
            "repository_health": "repository health",
            "maintenance": "maintenance",
            "community": "community",
            "popularity": "popularity",
        }

        try:
            repo_summary = self.analytics_engine.repository_summary()
            stars = int(repo_summary.get("stars", 0) or 0)
            age_days = int(repo_summary.get("age_days", 0) or 0)
        except AnalyticsError:
            repo_summary = {}
            stars = 0
            age_days = 0

        total_commits = 0
        try:
            commit_stats = self.analytics_engine.commit_statistics()
            total_commits = int(commit_stats.get("total_commits", 0) or 0)
        except AnalyticsError:
            pass

        total_contributors = 0
        try:
            contributor_stats = self.analytics_engine.contributor_statistics()
            total_contributors = int(contributor_stats.get("total_contributors", 0) or 0)
        except AnalyticsError:
            pass

        issue_close_rate = 0.0
        try:
            issue_stats = self.analytics_engine.issue_statistics()
            issue_close_rate = float(issue_stats.get("issue_close_rate", 0.0) or 0.0)
        except AnalyticsError:
            pass

        return (
            f"The repository scored {overall_score:.1f} because {labels[strongest_key]} is strongest "
            f"({intelligence_breakdown[strongest_key]:.1f}/100), while {labels[weakest_key]} is the main limiter "
            f"({intelligence_breakdown[weakest_key]:.1f}/100). The calculation reflects "
            f"{total_commits:,} recent fetched commits, "
            f"{total_contributors:,} contributors, "
            f"{issue_close_rate:.1f}% issue closure, "
            f"{stars:,} stars, and "
            f"{age_days:,} days of repository history."
        )

    def calculate_health_score(self) -> Dict[str, Any]:
        """Calculate the final repository health score and breakdown."""
        breakdown = {
            "commit_activity": round(self.commit_score(), 2),
            "contributor_activity": round(self.contributor_score(), 2),
            "issue_resolution": round(self.issue_score(), 2),
            "pull_request_success": round(self.pull_request_score(), 2),
            "repository_growth": round(self.repository_growth_score(), 2),
            "community_engagement": round(self.community_score(), 2),
        }

        legacy_total_score = sum(
            breakdown[key] * weight for key, weight in self.WEIGHTS.items()
        )
        legacy_score = round(self._clamp(legacy_total_score), 2)

        intelligence_breakdown = {
            "repository_health": round(self.repository_health_score(), 2),
            "maintenance": round(self.maintenance_score(), 2),
            "community": round(self.community_score(), 2),
            "popularity": round(self.popularity_score(), 2),
        }
        overall_score = round(
            self._clamp(
                intelligence_breakdown["repository_health"] * 0.35
                + intelligence_breakdown["maintenance"] * 0.30
                + intelligence_breakdown["community"] * 0.20
                + intelligence_breakdown["popularity"] * 0.15
            ),
            2,
        )
        grade = self._letter_grade(overall_score)
        summary = self._build_explanation(intelligence_breakdown, overall_score)

        return {
            "score": overall_score,
            "grade": grade,
            "health_label": self._grade(legacy_score),
            "summary": summary,
            "metric_breakdown": breakdown,
            "legacy_health_score": legacy_score,
            "repository_health": intelligence_breakdown["repository_health"],
            "maintenance_score": intelligence_breakdown["maintenance"],
            "community_score": intelligence_breakdown["community"],
            "popularity_score": intelligence_breakdown["popularity"],
            "overall_grade": grade,
            "intelligence_breakdown": intelligence_breakdown,
        }
