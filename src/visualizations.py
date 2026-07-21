"""Visualization helpers for reports and dashboard."""
import matplotlib.pyplot as plt


def plot_commits_over_time(df, date_col="date"):
    """Return a matplotlib Figure of commits over time."""
    fig, ax = plt.subplots()
    df.groupby(date_col).size().plot(ax=ax)
    ax.set_title("Commits over time")
    return fig
