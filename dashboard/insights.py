"""Generate deterministic engineering insights and recommendations."""

from typing import Any, Dict, List


InsightItem = Dict[str, str]


def _number(metrics: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = metrics.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(metrics: Dict[str, Any], key: str, default: str = "Unknown") -> str:
    value = metrics.get(key)
    return str(value) if value not in (None, "") else default


def _add_unique(items: List[InsightItem], seen: set[str], item: InsightItem) -> None:
    key = item["title"].strip().lower()
    if key not in seen:
        items.append(item)
        seen.add(key)


def _item(severity: str, icon: str, title: str, explanation: str) -> InsightItem:
    return {
        "severity": severity,
        "icon": icon,
        "title": title,
        "explanation": explanation,
    }


def generate_engineering_insights(metrics: Dict[str, Any]) -> Dict[str, List[InsightItem]]:
    """Generate rule-based decision-support insights from repository metrics."""
    insights: List[InsightItem] = []
    recommendations: List[InsightItem] = []
    seen_insights: set[str] = set()
    seen_recommendations: set[str] = set()

    health_score = _number(metrics, "health_score")
    maintenance_score = _number(metrics, "maintenance_score")
    community_score = _number(metrics, "community_score")
    popularity_score = _number(metrics, "popularity_score")
    repository_health = _number(metrics, "repository_health")
    total_contributors = int(_number(metrics, "total_contributors"))
    open_issues = int(_number(metrics, "open_issues"))
    total_issues = int(_number(metrics, "total_issues"))
    issue_close_rate = _number(metrics, "issue_close_rate")
    average_comments = _number(metrics, "average_comments")
    open_pull_requests = int(_number(metrics, "open_pull_requests"))
    total_pull_requests = int(_number(metrics, "total_pull_requests"))
    recent_commits = int(_number(metrics, "recent_commits_30_days"))
    previous_commits = int(_number(metrics, "previous_commits_30_days"))
    activity_change = _number(metrics, "commit_activity_change_pct")
    days_since_last_commit = int(_number(metrics, "days_since_last_commit"))
    top_contributor_share = _number(metrics, "top_contributor_share")
    language_count = int(_number(metrics, "language_count"))
    repository_age_days = int(_number(metrics, "repository_age_days"))
    stars = int(_number(metrics, "stars"))
    forks = int(_number(metrics, "forks"))
    has_description = bool(metrics.get("has_description"))
    has_license = bool(metrics.get("has_license"))
    primary_language = _text(metrics, "primary_language")

    if health_score >= 85 and repository_health >= 80:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#10003;",
                "Repository is healthy and actively evolving",
                f"Overall score is {health_score:.1f}/100 with repository health at {repository_health:.1f}/100.",
            ),
        )
    elif health_score >= 70:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Info",
                "&#9432;",
                "Repository is stable with targeted improvement areas",
                f"Overall score is {health_score:.1f}/100; maintenance is {maintenance_score:.1f}/100 and issue closure is {issue_close_rate:.1f}%.",
            ),
        )
    else:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Warning",
                "&#9888;",
                "Repository health needs leadership attention",
                f"Overall score is {health_score:.1f}/100, with maintenance at {maintenance_score:.1f}/100.",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Improve maintenance activity",
                f"Raise maintenance above 70/100 by scheduling triage, merges, and release work; it is currently {maintenance_score:.1f}/100.",
            ),
        )

    if maintenance_score >= 80 and days_since_last_commit <= 14:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#10003;",
                "Repository is actively maintained",
                f"The latest fetched commit is {days_since_last_commit} days old and maintenance is {maintenance_score:.1f}/100.",
            ),
        )
    elif maintenance_score < 55 or days_since_last_commit > 45:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Critical" if maintenance_score < 50 else "Warning",
                "&#9888;",
                "Recent maintenance activity is low",
                f"Maintenance is {maintenance_score:.1f}/100 and the latest fetched commit is {days_since_last_commit} days old.",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Critical" if maintenance_score < 50 else "Warning",
                "&#8594;",
                "Increase release cadence",
                f"Use smaller maintenance batches to lift the {maintenance_score:.1f}/100 maintenance score and reduce the {days_since_last_commit}-day activity gap.",
            ),
        )

    if previous_commits > 0 and activity_change <= -35:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Warning",
                "&#9660;",
                "Repository activity has slowed recently",
                f"Recent 30-day commits fell to {recent_commits} from {previous_commits}, a {abs(activity_change):.1f}% decrease.",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Review delivery cadence",
                f"Investigate the drop from {previous_commits} to {recent_commits} commits across the compared 30-day windows.",
            ),
        )
    elif previous_commits == 0 and recent_commits > 0:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#9650;",
                "Recent commit activity is high",
                f"The latest 30-day window contains {recent_commits} commits in the fetched activity sample.",
            ),
        )
    elif recent_commits >= previous_commits and recent_commits > 0:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#9650;",
                "Commit activity is holding steady",
                f"The latest 30-day window has {recent_commits} commits versus {previous_commits} in the prior window.",
            ),
        )

    if total_contributors >= 50 and top_contributor_share <= 15:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#10003;",
                "Contributor diversity is excellent",
                f"{total_contributors} contributors are represented and the top contributor owns {top_contributor_share:.1f}% of recorded contributions.",
            ),
        )
    elif top_contributor_share >= 35:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Critical",
                "&#9888;",
                "Repository depends heavily on a small contributor group",
                f"The top contributor owns {top_contributor_share:.1f}% of recorded contributions across {total_contributors} contributors.",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Critical",
                "&#8594;",
                "Increase contributor diversity",
                f"Reduce the {top_contributor_share:.1f}% top-contributor concentration through mentoring, issue routing, and reviewer rotation.",
            ),
        )
    elif top_contributor_share >= 20:
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Encourage more contributors",
                f"The top contributor handles {top_contributor_share:.1f}% of contributions; spread ownership across more maintainers.",
            ),
        )

    issue_backlog_ratio = (open_issues / total_issues * 100.0) if total_issues else 0.0
    if total_issues and issue_backlog_ratio >= 60:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Critical",
                "&#9888;",
                "Issue backlog is increasing",
                f"{open_issues} of {total_issues} issues are open ({issue_backlog_ratio:.1f}%), and closure rate is {issue_close_rate:.1f}%.",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Critical",
                "&#8594;",
                "Reduce long-open issues",
                f"Prioritize triage for the {open_issues} open issues and target a closure rate above 70%.",
            ),
        )
    elif total_issues and issue_backlog_ratio <= 25 and issue_close_rate >= 75:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#10003;",
                "Issue resolution is operating well",
                f"Only {open_issues} of {total_issues} issues are open and the closure rate is {issue_close_rate:.1f}%.",
            ),
        )

    pr_backlog_ratio = (open_pull_requests / total_pull_requests * 100.0) if total_pull_requests else 0.0
    if total_pull_requests and pr_backlog_ratio >= 35:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Warning",
                "&#9888;",
                "Pull request backlog needs review",
                f"{open_pull_requests} of {total_pull_requests} pull requests are open ({pr_backlog_ratio:.1f}%).",
            ),
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Review stale pull requests",
                f"Work down the {open_pull_requests} open pull requests to improve merge flow.",
            ),
        )

    if community_score >= 85 and average_comments >= 1.5:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#10003;",
                "Community engagement is strong",
                f"Community score is {community_score:.1f}/100 with {average_comments:.1f} average comments per issue.",
            ),
        )
    elif community_score < 60:
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Increase community participation",
                f"Improve the {community_score:.1f}/100 community score with clearer contribution paths and issue discussion prompts.",
            ),
        )

    if popularity_score >= 85:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#9733;",
                "Repository popularity is exceptionally high",
                f"Popularity is {popularity_score:.1f}/100 with {stars:,} stars and {forks:,} forks.",
            ),
        )
        if open_issues:
            _add_unique(
                recommendations,
                seen_recommendations,
                _item(
                    "Info",
                    "&#8594;",
                    "Scale community triage",
                    f"Use labels, templates, and maintainer rotations to manage {open_issues} open issues across a {stars:,}-star audience.",
                ),
            )
    elif popularity_score >= 70:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Info",
                "&#9733;",
                "Repository popularity is strong",
                f"Popularity is {popularity_score:.1f}/100 with {stars:,} stars and {forks:,} forks.",
            ),
        )
        if open_issues:
            _add_unique(
                recommendations,
                seen_recommendations,
                _item(
                    "Info",
                    "&#8594;",
                    "Increase community participation",
                    f"Convert the {popularity_score:.1f}/100 popularity signal into more issue triage help for {open_issues} open issues.",
                ),
            )

    if has_description and has_license and primary_language != "Unknown":
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#128196;",
                "Documentation quality indicators are good",
                f"Repository metadata includes a description, license, and primary language ({primary_language}).",
            ),
        )
    else:
        missing = ", ".join(
            label
            for label, available in (
                ("description", has_description),
                ("license", has_license),
                ("primary language", primary_language != "Unknown"),
            )
            if not available
        )
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Info",
                "&#8594;",
                "Improve documentation metadata",
                f"Add missing repository metadata for {missing} to strengthen discovery and onboarding.",
            ),
        )

    if repository_age_days >= 1825:
        _add_unique(
            insights,
            seen_insights,
            _item(
                "Good",
                "&#9201;",
                "Repository maturity is high",
                f"The repository has {repository_age_days:,} days of history and {language_count} detected languages.",
            ),
        )

    if issue_close_rate < 50 and total_issues:
        _add_unique(
            recommendations,
            seen_recommendations,
            _item(
                "Warning",
                "&#8594;",
                "Reduce issue response time",
                f"Improve the {issue_close_rate:.1f}% issue closure rate with regular triage and ownership assignment.",
            ),
        )

    return {
        "insights": insights[:8],
        "recommendations": recommendations[:6],
    }
