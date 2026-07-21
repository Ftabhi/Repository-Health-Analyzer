import importlib
import json

import pandas as pd
import pytest

from dashboard.app import (
    _build_chart_data,
    _build_metrics,
    _build_repository_overview,
    _load_repository_data,
    _parse_github_repository_url,
)
from dashboard.advanced_charts import activity_timeline
from dashboard.charts import commit_trend_chart, contributor_chart, issue_timeline_chart, language_chart
from dashboard.insights import generate_engineering_insights
from dashboard.layout import _build_kpi_cards
from src import config
from src.data_cleaner import DataCleaner
from src.github_client import GitHubClient


def test_parse_valid_github_repository_url() -> None:
    owner, repo = _parse_github_repository_url("https://github.com/microsoft/vscode")
    assert (owner, repo) == ("microsoft", "vscode")


def test_parse_invalid_github_repository_url() -> None:
    with pytest.raises(ValueError):
        _parse_github_repository_url("https://example.com/microsoft/vscode")


def test_config_allows_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    reloaded = importlib.reload(config)
    assert isinstance(reloaded.GITHUB_TOKEN, str)


def test_github_client_handles_empty_paginated_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        ok = True
        headers = {}
        text = ""

        def json(self):
            return []

    def fake_request(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("src.github_client.requests.request", fake_request)
    client = GitHubClient()

    assert client.get_contributors("owner", "repo") == []


def test_github_client_follows_paginated_results(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        type(
            "Response",
            (),
            {
                "ok": True,
                "headers": {"Link": '<https://api.github.com/repos/owner/repo/issues?page=2>; rel="next">'},
                "text": "",
                "json": lambda self: [{"id": 1}],
            },
        )(),
        type(
            "Response",
            (),
            {
                "ok": True,
                "headers": {},
                "text": "",
                "json": lambda self: [{"id": 2}],
            },
        )(),
    ]

    def fake_request(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr("src.github_client.requests.request", fake_request)
    client = GitHubClient()

    assert client.get_issues("owner", "repo") == [{"id": 1}, {"id": 2}]


def test_build_metrics_uses_numeric_defaults_for_empty_data() -> None:
    """Repositories with no data at all should still produce metrics without crashing.

    With empty DataFrames:
    - commit_score = 0.0    (no commits)
    - contributor_score = 0.0  (no contributors)
    - issue_score = 50.0   (neutral: no issues is not a negative signal)
    - pull_request_score = 50.0 (neutral: no PRs)
    - community_score = 0.0  (no sub-signals)
    - popularity_score = 0.0  (no repo data)
    These produce a small but non-zero overall score (~12.x).
    """
    empty_data = {
        "repository_df": pd.DataFrame(),
        "commits_df": pd.DataFrame(),
        "contributors_df": pd.DataFrame(),
        "issues_df": pd.DataFrame(),
        "languages_df": pd.DataFrame(),
    }

    metrics = _build_metrics(empty_data)

    assert metrics["total_commits"] == 0
    # health_score is non-zero because issue_score = 50.0 (neutral: no issues is not a failure)
    assert 0.0 <= metrics["health_score"] <= 100.0
    assert 0.0 <= metrics["repository_health"] <= 100.0
    assert 0.0 <= metrics["maintenance_score"] <= 100.0
    assert metrics["community_score"] == 0.0
    assert metrics["popularity_score"] == 0.0
    # With no repo data the grade is still a valid letter grade or Pending
    assert metrics["overall_grade"] in {"A+", "A", "B", "C", "D", "Pending"}
    assert metrics["primary_language"] == "Unknown"


@pytest.mark.parametrize(
    "repository",
    [
        "microsoft/vscode",
        "facebook/react",
        "pallets/flask",
        "streamlit/streamlit",
        "tensorflow/tensorflow",
    ],
)
def test_core_chart_data_uses_selected_repository_rows(repository: str) -> None:
    repository_data = _load_repository_data(repository)
    metrics = _build_metrics(repository_data)
    chart_data = _build_chart_data(repository_data, metrics)

    assert not repository_data["repository_df"].empty
    assert not chart_data["commits"].empty
    assert not chart_data["contributors"].empty
    assert not chart_data["languages"].empty
    assert set(chart_data["issue_timeline"].columns) == {"date", "opened", "closed"}
    assert chart_data["raw_issues"].equals(repository_data["issues_df"])


def test_core_charts_render_empty_states_without_fake_slices() -> None:
    empty_commits = pd.DataFrame({"date": [], "commits": []})
    empty_issues = pd.DataFrame({"date": [], "opened": [], "closed": []})
    empty_languages = pd.DataFrame({"language": [], "bytes": []})
    empty_contributors = pd.DataFrame({"contributor": [], "contributions": []})

    figures = [
        commit_trend_chart(empty_commits),
        issue_timeline_chart(empty_issues),
        language_chart(empty_languages),
        contributor_chart(empty_contributors),
        activity_timeline(pd.DataFrame(), pd.DataFrame()),
    ]

    assert all(figure.layout.annotations for figure in figures)
    assert all(len(figure.data) == 0 for figure in figures)


def test_core_charts_include_meaningful_hover_templates() -> None:
    commit_fig = commit_trend_chart(pd.DataFrame({"date": ["2026-07-16"], "commits": [3]}))
    issue_fig = issue_timeline_chart(pd.DataFrame({"date": ["2026-07-16"], "opened": [2], "closed": [1]}))
    language_fig = language_chart(pd.DataFrame({"language": ["Python"], "bytes": [1200]}))
    contributor_fig = contributor_chart(pd.DataFrame({"contributor": ["octocat"], "contributions": [42]}))
    activity_fig = activity_timeline(
        pd.DataFrame({"commit_author_date": ["2026-07-16T00:00:00Z"]}),
        pd.DataFrame({"created_at": ["2026-07-16T00:00:00Z"], "closed_at": ["2026-07-17T00:00:00Z"]}),
    )

    assert "commits" in commit_fig.data[0].hovertemplate
    assert "opened issues" in issue_fig.data[0].hovertemplate
    assert "bytes" in language_fig.data[0].hovertemplate
    assert "contributions" in contributor_fig.data[0].hovertemplate
    assert {trace.name for trace in activity_fig.data} == {"Commits", "Opened issues", "Closed issues"}


def test_repository_intelligence_scores_are_data_driven_per_repository() -> None:
    repositories = [
        "microsoft/vscode",
        "facebook/react",
        "streamlit/streamlit",
        "pallets/flask",
        "tensorflow/tensorflow",
    ]
    results = {}

    for repository in repositories:
        metrics = _build_metrics(_load_repository_data(repository))
        results[repository] = metrics

        assert 0 <= metrics["health_score"] <= 100
        assert 0 <= metrics["repository_health"] <= 100
        assert 0 <= metrics["maintenance_score"] <= 100
        assert 0 <= metrics["community_score"] <= 100
        assert 0 <= metrics["popularity_score"] <= 100
        assert metrics["overall_grade"] in {"A+", "A", "B", "C", "D"}
        assert metrics["health_grade"] == metrics["overall_grade"]
        assert metrics["health_label"] != "Pending"
        assert str(metrics["score_explanation"]).startswith("The repository scored")

    rounded_scores = {round(metrics["health_score"], 2) for metrics in results.values()}
    assert len(rounded_scores) == len(repositories)
    assert results["streamlit/streamlit"]["health_score"] != results["pallets/flask"]["health_score"]


def test_engineering_insights_are_structured_unique_and_data_driven() -> None:
    repositories = [
        "microsoft/vscode",
        "facebook/react",
        "streamlit/streamlit",
        "pallets/flask",
        "tensorflow/tensorflow",
    ]
    fingerprints = set()

    for repository in repositories:
        metrics = _build_metrics(_load_repository_data(repository))
        output = generate_engineering_insights(metrics)
        insights = output["insights"]
        recommendations = output["recommendations"]

        assert insights
        assert recommendations
        assert all(isinstance(item, dict) for item in insights)
        assert all(isinstance(item, dict) for item in recommendations)

        for item in insights + recommendations:
            assert item["severity"] in {"Info", "Good", "Warning", "Critical"}
            assert item["icon"]
            assert item["title"]
            assert item["explanation"]
            assert "placeholder" not in item["explanation"].lower()
            assert "N/A" not in item["explanation"]

        insight_titles = [item["title"] for item in insights]
        recommendation_titles = [item["title"] for item in recommendations]
        assert len(insight_titles) == len(set(insight_titles))
        assert len(recommendation_titles) == len(set(recommendation_titles))

        fingerprint = (
            tuple(item["title"] for item in insights),
            tuple(item["title"] for item in recommendations),
        )
        fingerprints.add(fingerprint)

    assert len(fingerprints) == len(repositories)


def test_engineering_insights_react_to_specific_repository_conditions() -> None:
    vscode_output = generate_engineering_insights(_build_metrics(_load_repository_data("microsoft/vscode")))
    flask_output = generate_engineering_insights(_build_metrics(_load_repository_data("pallets/flask")))
    streamlit_output = generate_engineering_insights(_build_metrics(_load_repository_data("streamlit/streamlit")))

    vscode_titles = {item["title"] for item in vscode_output["recommendations"]}
    flask_titles = {item["title"] for item in flask_output["recommendations"]}
    streamlit_titles = {item["title"] for item in streamlit_output["insights"]}

    assert "Reduce long-open issues" in vscode_titles
    assert "Increase release cadence" in flask_titles
    assert "Repository is healthy and actively evolving" in streamlit_titles


def test_build_kpi_cards_use_real_repository_metrics() -> None:
    repository_data = _load_repository_data("microsoft/vscode")
    metrics = _build_metrics(repository_data)

    cards = _build_kpi_cards(metrics)
    card_map = {label: value for label, value, description, trend, variant in cards}

    assert card_map["Total Commits"] == "300"
    assert card_map["Total Contributors"] == "200"
    assert card_map["Open Issues"] == "128"
    assert card_map["Health Score"].endswith("%")
    assert all(not trend for _, _, _, trend, _ in cards)
    assert "Pending" not in card_map["Health Score"]
    assert "N/A" not in card_map["Health Score"]


def test_build_kpi_cards_refresh_when_metrics_change() -> None:
    metrics_a = {
        "total_commits": 100,
        "total_contributors": 20,
        "open_issues": 10,
        "closed_issues": 5,
        "open_pull_requests": 3,
        "merged_pull_requests": 1,
        "repository_age_days": 365,
        "stars": 1000,
        "forks": 200,
        "watchers": 500,
        "health_score": 72.4,
        "health_grade": "Healthy",
    }
    metrics_b = {
        "total_commits": 250,
        "total_contributors": 40,
        "open_issues": 25,
        "closed_issues": 20,
        "open_pull_requests": 8,
        "merged_pull_requests": 6,
        "repository_age_days": 730,
        "stars": 4000,
        "forks": 900,
        "watchers": 1500,
        "health_score": 93.1,
        "health_grade": "Excellent",
    }

    cards_a = _build_kpi_cards(metrics_a)
    cards_b = _build_kpi_cards(metrics_b)
    card_map_a = {label: value for label, value, description, trend, variant in cards_a}
    card_map_b = {label: value for label, value, description, trend, variant in cards_b}

    assert card_map_a["Total Commits"] != card_map_b["Total Commits"]
    assert card_map_a["Stars"] != card_map_b["Stars"]
    assert card_map_a["Health Score"] != card_map_b["Health Score"]


def test_data_cleaner_preserves_repository_overview_metadata(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    payload = {
        "id": 1,
        "name": "vscode",
        "full_name": "microsoft/vscode",
        "owner": {"login": "microsoft", "id": 6154722},
        "description": "Visual Studio Code",
        "html_url": "https://github.com/microsoft/vscode",
        "stargazers_count": 170000,
        "forks_count": 32000,
        "watchers_count": 170000,
        "open_issues_count": 5000,
        "language": "TypeScript",
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "created_at": "2015-09-03T20:23:38Z",
        "updated_at": "2026-07-16T10:00:00Z",
        "pushed_at": "2026-07-16T11:00:00Z",
        "visibility": "public",
        "size": 900000,
        "default_branch": "main",
    }
    (raw_dir / "microsoft_vscode_repository.json").write_text(json.dumps(payload), encoding="utf-8")

    cleaner = DataCleaner(raw_dir=raw_dir, processed_dir=processed_dir)
    repository_df = cleaner.clean_repository("microsoft", "vscode")
    overview = _build_repository_overview(repository_df)

    assert overview["Repository Name"] == "vscode"
    assert overview["Owner"] == "microsoft"
    assert overview["Description"] == "Visual Studio Code"
    assert overview["Repository URL"] == "https://github.com/microsoft/vscode"
    assert overview["Primary Language"] == "TypeScript"
    assert overview["Stars"] == "170,000"
    assert overview["Forks"] == "32,000"
    assert overview["Watchers"] == "170,000"
    assert overview["Open Issues"] == "5,000"
    assert overview["License"] == "MIT"
    assert overview["Default Branch"] == "main"
    assert overview["Repository Age"].endswith(" days")
    assert overview["Created Date"] == "2015-09-03 20:23 UTC"
    assert overview["Last Updated"] == "2026-07-16 10:00 UTC"
    assert overview["Last Push Date"] == "2026-07-16 11:00 UTC"
    assert overview["Repository Visibility"] == "Public"
    assert overview["Repository Size"] == "878.9 MB"


# ---------------------------------------------------------------------------
# Regression tests: sparse repositories (zero issues, zero commits, etc.)
# ---------------------------------------------------------------------------


def test_issue_score_returns_neutral_when_no_issues() -> None:
    """issue_score must return 50.0 (neutral) when no issue data is available.

    Regression: previously raised HealthScoreError("Unable to calculate issue score")
    for repositories with disabled issues or zero issues fetched.
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine(issues_df=pd.DataFrame())
    scorer = RepositoryHealthScore(engine)
    assert scorer.issue_score() == 50.0


def test_commit_score_returns_zero_when_no_commits() -> None:
    """commit_score must return 0.0 (not raise) when no commit data is available.

    Regression: previously raised HealthScoreError("Unable to calculate commit score").
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine(commits_df=pd.DataFrame())
    scorer = RepositoryHealthScore(engine)
    assert scorer.commit_score() == 0.0


def test_contributor_score_returns_zero_when_no_contributors() -> None:
    """contributor_score must return 0.0 (not raise) when no contributor data is available.

    Regression: previously raised HealthScoreError("Unable to calculate contributor score").
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine(contributors_df=pd.DataFrame())
    scorer = RepositoryHealthScore(engine)
    assert scorer.contributor_score() == 0.0


def test_community_score_returns_zero_when_all_data_missing() -> None:
    """community_score must return 0.0 when no sub-signals are available.

    Regression: previously raised HealthScoreError("Unable to calculate community score").
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine()  # all DataFrames are None
    scorer = RepositoryHealthScore(engine)
    assert scorer.community_score() == 0.0


def test_popularity_score_returns_zero_when_no_repo_data() -> None:
    """popularity_score must return 0.0 when no repository data is available.

    Regression: previously raised HealthScoreError("Unable to calculate popularity score").
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine(repository_df=pd.DataFrame())
    scorer = RepositoryHealthScore(engine)
    assert scorer.popularity_score() == 0.0


def test_calculate_health_score_succeeds_with_all_empty_data() -> None:
    """calculate_health_score must never raise even when all DataFrames are empty.

    Regression: previously raised HealthScoreError("Unable to calculate issue score")
    for repositories with no issues, which caused 'Repository analysis failed' in the dashboard.
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    engine = AnalyticsEngine(
        repository_df=pd.DataFrame(),
        commits_df=pd.DataFrame(),
        contributors_df=pd.DataFrame(),
        issues_df=pd.DataFrame(),
        languages_df=pd.DataFrame(),
    )
    result = RepositoryHealthScore(engine).calculate_health_score()

    assert isinstance(result, dict)
    assert 0.0 <= result["score"] <= 100.0
    assert result["grade"] in {"A+", "A", "B", "C", "D"}
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_calculate_health_score_succeeds_with_only_repo_data() -> None:
    """A repository with metadata but no commits/issues/contributors must still score.

    This covers repos that exist on GitHub but have zero activity (e.g., newly created,
    or repos with issues disabled).
    """
    from src.analytics_engine import AnalyticsEngine
    from src.health_score import RepositoryHealthScore

    repo_df = pd.DataFrame([{
        "repository_id": 1,
        "repository_name": "my-repo",
        "full_name": "owner/my-repo",
        "owner_login": "owner",
        "stars": 5,
        "forks": 1,
        "watchers": 3,
        "open_issues": 0,
        "language": "Python",
        "created_at": pd.Timestamp("2023-01-01", tz="UTC"),
        "updated_at": pd.Timestamp("2023-06-01", tz="UTC"),
        "pushed_at": pd.Timestamp("2023-06-01", tz="UTC"),
    }])

    engine = AnalyticsEngine(
        repository_df=repo_df,
        commits_df=pd.DataFrame(),
        contributors_df=pd.DataFrame(),
        issues_df=pd.DataFrame(),
        languages_df=pd.DataFrame(),
    )
    result = RepositoryHealthScore(engine).calculate_health_score()

    assert isinstance(result, dict)
    assert 0.0 <= result["score"] <= 100.0
    # Stars/forks/watchers should contribute to a non-zero popularity score
    assert result["popularity_score"] > 0.0
    assert result["grade"] in {"A+", "A", "B", "C", "D"}
    assert result["summary"].startswith("The repository scored")


def test_main_session_state_updates_after_analysis(monkeypatch) -> None:
    """Verify that st.session_state is updated to select the new repo on success.

    And that it cleans up/resets selectbox key on failures.
    """
    import streamlit as st
    from dashboard.app import main

    # Mock st.session_state
    session_state = {"repository_url_input": "https://github.com/pallets/flask"}
    monkeypatch.setattr(st, "session_state", session_state)

    # Mock st.sidebar and its container methods to avoid ScriptRunContext errors
    class MockContainer:
        def markdown(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass
        def download_button(self, *args, **kwargs): pass

    class MockSidebar:
        def container(self):
            return MockContainer()
        def markdown(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass
        def download_button(self, *args, **kwargs): pass

    monkeypatch.setattr(st, "sidebar", MockSidebar())
    monkeypatch.setattr(st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: None)

    class MockSpinner:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    monkeypatch.setattr(st, "spinner", lambda *args, **kwargs: MockSpinner())

    # Mock helper functions in app.py to simulate UI logic
    monkeypatch.setattr("dashboard.app._configure_page", lambda: None)
    monkeypatch.setattr("dashboard.app._discover_repositories", lambda: ["pallets/flask"])
    monkeypatch.setattr("dashboard.app._render_dashboard_for_repository", lambda repo: None)

    # First case: Successful analysis
    def mock_render_sidebar_success(discovered_repos):
        # User entered pallets/flask and clicked analyze
        return "https://github.com/pallets/flask", True, ""

    monkeypatch.setattr("dashboard.app.render_sidebar", mock_render_sidebar_success)
    monkeypatch.setattr("dashboard.app._analyze_repository", lambda url, container: "pallets/flask")
    monkeypatch.setattr("dashboard.app.st.cache_data", type("CacheData", (), {"clear": lambda self=None: None})())

    rerun_called = False
    def mock_rerun():
        nonlocal rerun_called
        rerun_called = True

    monkeypatch.setattr(st, "rerun", mock_rerun)

    main()

    assert rerun_called is True
    assert session_state.get("selected_repository") == "pallets/flask"
    assert session_state.get("sidebar_repo_selectbox") == "pallets/flask"
    assert session_state.get("repository_url_input") == ""

    # Second case: Analysis fails
    def mock_render_sidebar_fail(discovered_repos):
        return "https://github.com/invalid/repo", True, "pallets/flask"

    monkeypatch.setattr("dashboard.app.render_sidebar", mock_render_sidebar_fail)
    
    def mock_analyze_fail(url, container):
        raise ValueError("Invalid URL")

    monkeypatch.setattr("dashboard.app._analyze_repository", mock_analyze_fail)

    rerun_called = False
    main()

    # Should clear selectbox selection state and selected_repository on failure
    assert session_state.get("selected_repository") == ""
    assert session_state.get("sidebar_repo_selectbox") == ""
