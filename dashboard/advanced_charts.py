"""Advanced Plotly charts for engineering analytics."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .charts import BLUE, GREEN, GRID, ORANGE, PAPER_BG, PLOT_BG, TEXT, empty_chart


def _placeholder_figure(title: str, message: str) -> go.Figure:
    return empty_chart(title, message)


def _daily_counts(df: pd.DataFrame, date_column: str, count_name: str) -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return pd.DataFrame(columns=["date", count_name])

    summary = df.copy()
    summary["date"] = pd.to_datetime(summary[date_column], errors="coerce").dt.normalize()
    summary = summary.dropna(subset=["date"])
    if summary.empty:
        return pd.DataFrame(columns=["date", count_name])
    return summary.groupby("date").size().reset_index(name=count_name)


def contribution_heatmap(commits_df: pd.DataFrame) -> go.Figure:
    """Render a weekly contribution-style heatmap from commit history."""
    if commits_df.empty or "commit_author_date" not in commits_df.columns:
        return _placeholder_figure(
            "Commit Contribution Heatmap",
            "No commit history is available to render the heatmap.",
        )

    df = commits_df.copy()
    df["date"] = pd.to_datetime(df["commit_author_date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return _placeholder_figure(
            "Commit Contribution Heatmap",
            "No valid commit dates were found in the dataset.",
        )

    df["week_label"] = df["date"].dt.strftime("%Y-%U")
    df["weekday"] = df["date"].dt.weekday


def contribution_heatmap(commits_df: pd.DataFrame) -> go.Figure:
    """Render a weekly contribution-style heatmap from commit history."""
    if commits_df.empty or "commit_author_date" not in commits_df.columns:
        return _placeholder_figure(
            "Commit Contribution Heatmap",
            "No commit history is available to render the heatmap.",
        )

    df = commits_df.copy()
    df["date"] = pd.to_datetime(df["commit_author_date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return _placeholder_figure(
            "Commit Contribution Heatmap",
            "No valid commit dates were found in the dataset.",
        )

    df["week_label"] = df["date"].dt.strftime("%Y-%U")
    df["weekday"] = df["date"].dt.weekday
    df = df.groupby(["week_label", "weekday"]).size().reset_index(name="commits")
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    df["weekday_name"] = df["weekday"].apply(
        lambda value: weekday_names[value] if 0 <= value < len(weekday_names) else str(value)
    )

    pivot = df.pivot(index="weekday_name", columns="week_label", values="commits").fillna(0)
    weekday_order = [name for name in weekday_names if name in pivot.index]
    pivot = pivot.reindex(weekday_order)
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Blues",
            hovertemplate="Week %{x}<br>%{y}: %{z} commits<extra></extra>",
        )
    )
    fig.update_layout(
        title="Commit Contribution Heatmap",
        xaxis_title="Week",
        yaxis_title="Day",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=24, r=18, t=40, b=24),
    )
    fig.update_xaxes(gridcolor=GRID, color="#C9D1D9")
    fig.update_yaxes(gridcolor=GRID, color="#C9D1D9")
    return fig


def leaderboard_chart(contributors_df: pd.DataFrame) -> go.Figure:
    """Render a contributor leaderboard chart."""
    if contributors_df.empty or "login" not in contributors_df.columns:
        return _placeholder_figure(
            "Top Contributors Leaderboard",
            "No contributors data is available for this repository.",
        )

    df = contributors_df.copy()
    if "contributions" in df.columns:
        df["contributions"] = pd.to_numeric(df["contributions"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("contributions", ascending=False).head(10)
    if df.empty:
        return _placeholder_figure(
            "Top Contributors Leaderboard",
            "No contributor activity was detected in the selected period.",
        )

    fig = px.bar(
        df,
        x="contributions",
        y="login",
        orientation="h",
        color="contributions",
        color_continuous_scale="Blues",
        labels={"login": "Contributor", "contributions": "Contributions"},
    )
    fig.update_layout(
        title="Top Contributors Leaderboard",
        xaxis_title="Contributions",
        yaxis_title="Contributor",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=24, r=18, t=40, b=24),
        coloraxis_showscale=False,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9", rangemode="tozero")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9", autorange="reversed")
    return fig


def activity_timeline(commits_df: pd.DataFrame, issues_df: pd.DataFrame | None = None) -> go.Figure:
    """Render a repository activity timeline from commits and issue events."""
    issues_df = issues_df if issues_df is not None else pd.DataFrame()
    commits_summary = _daily_counts(commits_df, "commit_author_date", "commits")
    opened_summary = _daily_counts(issues_df, "created_at", "opened_issues")
    closed_summary = _daily_counts(issues_df, "closed_at", "closed_issues")

    if commits_summary.empty and opened_summary.empty and closed_summary.empty:
        return _placeholder_figure(
            "Repository Activity",
            "No repository activity data is available.",
        )

    merged = None
    for frame in (commits_summary, opened_summary, closed_summary):
        if frame.empty:
            continue
        merged = frame if merged is None else merged.merge(frame, on="date", how="outer")
    activity = merged.fillna(0).sort_values("date")

    fig = go.Figure()
    if "commits" in activity.columns:
        fig.add_trace(
            go.Scatter(
                x=activity["date"],
                y=activity["commits"],
                mode="lines",
                stackgroup="activity",
                name="Commits",
                line=dict(color=BLUE),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y} commits<extra></extra>",
            )
        )
    if "opened_issues" in activity.columns:
        fig.add_trace(
            go.Scatter(
                x=activity["date"],
                y=activity["opened_issues"],
                mode="lines",
                stackgroup="activity",
                name="Opened issues",
                line=dict(color=ORANGE),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y} opened issues<extra></extra>",
            )
        )
    if "closed_issues" in activity.columns:
        fig.add_trace(
            go.Scatter(
                x=activity["date"],
                y=activity["closed_issues"],
                mode="lines",
                stackgroup="activity",
                name="Closed issues",
                line=dict(color=GREEN),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y} closed issues<extra></extra>",
            )
        )
    fig.update_layout(
        title="Repository Activity",
        xaxis_title="Date",
        yaxis_title="Activity events",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        hovermode="x unified",
        margin=dict(l=24, r=18, t=40, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9", rangemode="tozero")
    return fig


def health_score_trend(health_history: pd.DataFrame) -> go.Figure:
    """Render a health score trend chart."""
    if health_history.empty or "date" not in health_history.columns:
        return _placeholder_figure(
            "Health Score Trend",
            "Historical health score data is unavailable.",
        )

    fig = px.line(
        health_history,
        x="date",
        y="health_score",
        markers=True,
        labels={"date": "Date", "health_score": "Health Score"},
    )
    fig.update_traces(line=dict(color=BLUE), marker=dict(color=BLUE))
    fig.update_layout(
        title="Health Score Trend",
        xaxis_title="Date",
        yaxis_title="Health Score",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=24, r=18, t=40, b=24),
        yaxis=dict(range=[0, 105]),
    )
    fig.update_xaxes(gridcolor=GRID, color="#C9D1D9")
    fig.update_yaxes(gridcolor=GRID, color="#C9D1D9")
    return fig
