"""Plotly chart functions for the Streamlit dashboard."""

import pandas as pd
import plotly.graph_objects as go


PAPER_BG = "#161B22"
PLOT_BG = "#0D1117"
TEXT = "#F0F6FC"
MUTED = "#8B949E"
GRID = "#30363D"
BLUE = "#58A6FF"
GREEN = "#3FB950"
ORANGE = "#D29922"
RED = "#F85149"


def empty_chart(title: str, message: str) -> go.Figure:
    """Return a consistent empty-state chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color=MUTED, size=14),
    )
    fig.update_layout(
        title=title,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        margin=dict(l=24, r=16, t=40, b=24),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _style_timeseries(fig: go.Figure, title: str, x_title: str, y_title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        hovermode="x unified",
        margin=dict(l=24, r=16, t=40, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9", rangemode="tozero")
    return fig


def commit_trend_chart(data: pd.DataFrame) -> go.Figure:
    """Return a commit activity timeline chart."""
    if data.empty or not {"date", "commits"}.issubset(data.columns):
        return empty_chart(
            "Commit Timeline",
            "No commit activity is available for this repository.",
        )

    data = data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["commits"] = pd.to_numeric(data["commits"], errors="coerce").fillna(0).astype(int)
    data = data.dropna(subset=["date"]).sort_values("date")
    if data.empty or data["commits"].sum() == 0:
        return empty_chart(
            "Commit Timeline",
            "No valid commit dates were found in the GitHub data.",
        )

    fig = go.Figure(
        go.Scatter(
            x=data["date"],
            y=data["commits"],
            mode="lines+markers",
            name="Commits",
            marker=dict(color=BLUE, size=6),
            line=dict(shape="spline", smoothing=1.2, color=BLUE),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y} commits<extra></extra>",
        )
    )
    return _style_timeseries(fig, "Commit Timeline", "Date", "Commits")


def issue_timeline_chart(data: pd.DataFrame) -> go.Figure:
    """Return an issue opened/closed timeline chart."""
    expected = {"date", "opened", "closed"}
    if data.empty or not expected.issubset(data.columns):
        return empty_chart(
            "Issue Timeline",
            "No issue activity is available for this repository.",
        )

    df = data.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ("opened", "closed"):
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["date"]).sort_values("date")
    if df.empty or (df["opened"].sum() + df["closed"].sum()) == 0:
        return empty_chart(
            "Issue Timeline",
            "No opened or closed issue dates were found in the GitHub data.",
        )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["opened"],
            mode="lines+markers",
            name="Opened",
            line=dict(color=ORANGE, shape="spline", smoothing=1.1),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y} opened issues<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["closed"],
            mode="lines+markers",
            name="Closed",
            line=dict(color=GREEN, shape="spline", smoothing=1.1),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y} closed issues<extra></extra>",
        )
    )
    return _style_timeseries(fig, "Issue Timeline", "Date", "Issues")


def contributor_chart(data: pd.DataFrame) -> go.Figure:
    """Return a contributors bar chart."""
    if data.empty or not {"contributor", "contributions"}.issubset(data.columns):
        return empty_chart(
            "Contributor Leaderboard",
            "No contributor data is available for this repository.",
        )

    data = data.copy()
    data["contributions"] = pd.to_numeric(data["contributions"], errors="coerce").fillna(0).astype(int)
    data = data.sort_values("contributions", ascending=True).tail(10)
    if data.empty or data["contributions"].sum() == 0:
        return empty_chart(
            "Contributor Leaderboard",
            "No contributor activity was detected in the GitHub data.",
        )

    fig = go.Figure(
        go.Bar(
            x=data["contributions"],
            y=data["contributor"],
            orientation="h",
            marker_color=BLUE,
            marker_line_color=PLOT_BG,
            marker_line_width=1,
            hovertemplate="%{y}<br>%{x} contributions<extra></extra>",
        )
    )
    fig.update_layout(
        title="Contributor Leaderboard",
        xaxis_title="Contributions",
        yaxis_title="Contributor",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font_color=TEXT,
        margin=dict(l=22, r=16, t=40, b=30),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9", rangemode="tozero")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, color="#C9D1D9")
    return fig


def issue_chart(data: pd.DataFrame) -> go.Figure:
    """Return an issue status pie chart."""
    if data.empty or not {"state", "count"}.issubset(data.columns):
        return empty_chart(
            "Issue Status Breakdown",
            "No issue status data is available for this repository.",
        )

    data = data.copy()
    data["count"] = pd.to_numeric(data["count"], errors="coerce").fillna(0).astype(int)
    data = data[data["count"] > 0]
    if data.empty:
        return empty_chart(
            "Issue Status Breakdown",
            "No issue status counts were found in the GitHub data.",
        )

    fig = go.Figure(
        go.Pie(
            labels=data["state"],
            values=data["count"],
            hole=0.4,
            marker=dict(line=dict(color=PLOT_BG, width=1)),
            textinfo="label+percent",
            textfont=dict(color=TEXT),
            hovertemplate="%{label}<br>%{value} issues (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        title="Issue Status Breakdown",
        paper_bgcolor=PAPER_BG,
        font_color=TEXT,
        margin=dict(l=16, r=16, t=40, b=16),
    )
    return fig


def language_chart(data: pd.DataFrame) -> go.Figure:
    """Return a language distribution donut chart."""
    if data.empty or not {"language", "bytes"}.issubset(data.columns):
        return empty_chart(
            "Language Distribution",
            "No language breakdown is available for this repository.",
        )

    data = data.copy()
    data["bytes"] = pd.to_numeric(data["bytes"], errors="coerce").fillna(0).astype(int)
    data = data[data["bytes"] > 0].sort_values("bytes", ascending=False)
    if data.empty:
        return empty_chart(
            "Language Distribution",
            "No language byte counts were returned by GitHub.",
        )

    fig = go.Figure(
        go.Pie(
            labels=data["language"],
            values=data["bytes"],
            hole=0.55,
            marker=dict(line=dict(color=PLOT_BG, width=1)),
            textinfo="label+percent",
            textfont=dict(color=TEXT),
            hovertemplate="%{label}<br>%{value:,} bytes (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        title="Language Distribution",
        paper_bgcolor=PAPER_BG,
        font_color=TEXT,
        margin=dict(l=16, r=16, t=40, b=16),
    )
    return fig


def health_score_gauge(score: float) -> go.Figure:
    """Return a repository health gauge chart."""
    display_score = score if isinstance(score, (int, float)) else 0.0
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=display_score,
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#C9D1D9"},
                "bar": {"color": BLUE},
                "bgcolor": PLOT_BG,
                "steps": [
                    {"range": [0, 40], "color": RED},
                    {"range": [40, 70], "color": ORANGE},
                    {"range": [70, 100], "color": GREEN},
                ],
            },
            number={"suffix": "%", "font": {"color": TEXT}},
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        title="Repository Health Score",
        paper_bgcolor=PAPER_BG,
        font_color=TEXT,
        margin=dict(l=16, r=16, t=40, b=16),
    )
    return fig
