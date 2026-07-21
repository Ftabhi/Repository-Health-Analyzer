"""Reusable Streamlit components for the dashboard."""

from html import escape
from typing import Any

import streamlit as st


def _kpi_icon(label: str) -> str:
    icons = {
        "Total Commits": "&#128200;",
        "Total Contributors": "&#128101;",
        "Open Issues": "&#9679;",
        "Closed Issues": "&#10003;",
        "Open Pull Requests": "&#8644;",
        "Merged Pull Requests": "&#10022;",
        "Repository Age": "&#9201;",
        "Stars": "&#9733;",
        "Forks": "&#9282;",
        "Watchers": "&#128065;",
        "Health Score": "&#9829;",
    }
    return icons.get(label, "&#9671;")


def render_section_title(title: str, subtitle: str) -> None:
    """Render a section title with subtitle text."""
    st.markdown(
        f"""
        <div class='section-title'>
            <div>
                <h2>{escape(str(title))}</h2>
                <p>{escape(str(subtitle))}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: Any, subtitle: str, trend: str = "", variant: str = "") -> None:
    """Render a premium KPI card with icon, title, value, subtitle, optional trend, and color variant.

    Args:
        label:   Card title / metric name.
        value:   Primary display value.
        subtitle: Secondary description line.
        trend:   Optional trend text shown bottom-right (e.g. "↑ 12%").
        variant: Optional CSS modifier class suffix: '', 'success', 'warning', 'danger', 'accent'.
    """
    icon = _kpi_icon(label)
    variant_class = f" kpi-card--{escape(variant)}" if variant else ""
    trend_markup = f"<span class='kpi-card__trend'>{escape(str(trend))}</span>" if trend else ""
    st.markdown(
        f"""
        <div class='kpi-card{variant_class}'>
            <div class='kpi-card__top'>
                <span class='kpi-card__icon'>{icon}</span>
                <span class='kpi-card__label'>{escape(str(label))}</span>
            </div>
            <div class='kpi-card__value'>{escape(str(value))}</div>
            <div class='kpi-card__bottom'>
                <span class='kpi-card__subtitle'>{escape(str(subtitle))}</span>
                {trend_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_box(label: str, value: Any, description: str) -> None:
    """Render a compact metric box with a description."""
    st.markdown(
        f"""
        <div class='metric-box'>
            <div class='metric-box__label'>{escape(str(label))}</div>
            <div class='metric-box__value'>{escape(str(value))}</div>
            <div class='metric-box__description'>{escape(str(description))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
