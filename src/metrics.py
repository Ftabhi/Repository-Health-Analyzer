"""Definition of metrics to evaluate repository health."""

def compute_activity_score(commits_count: int, contributors: int) -> float:
    """Compute a simple activity score."""
    if contributors <= 0:
        return 0.0
    return commits_count / contributors
