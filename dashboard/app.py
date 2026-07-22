"""Streamlit dashboard entry point."""

from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import logging
import re
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

from dashboard.exports import export_to_csv, export_to_json, export_to_pdf
from dashboard.insights import generate_engineering_insights
from dashboard.layout import render_dashboard
from dashboard.sidebar import render_sidebar
from src.analytics_engine import AnalyticsEngine, AnalyticsError
from src.data_cleaner import DataCleaner, DataCleaningError
from src.data_storage import DataStorage, DataStorageError
from src.github_client import (
    GitHubClient,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubPrivateRepositoryError,
    GitHubRateLimitError,
)
from src.health_score import RepositoryHealthScore, HealthScoreError

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
REPOSITORY_SUFFIX = "_repository.csv"
COMMITS_SUFFIX = "_commits.csv"
CONTRIBUTORS_SUFFIX = "_contributors.csv"
ISSUES_SUFFIX = "_issues.csv"
LANGUAGES_SUFFIX = "_languages.csv"


def _configure_page() -> None:
    """Configure the Streamlit page metadata."""
    st.set_page_config(
        page_title="Repository Health Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ============================================================
           CSS VARIABLES — Design Tokens
        ============================================================ */
        :root {
            --bg-color: #0D1117;
            --panel-color: #161B22;
            --card-color: #1C2128;
            --border-color: #30363D;
            --accent-color: #58A6FF;
            --success-color: #3FB950;
            --warning-color: #D29922;
            --danger-color: #F85149;
            --text-color: #E6EDF3;
            --text-muted: #8B949E;
            --font-stack: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 24px;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.25);
            --shadow-lg: 0 8px 32px rgba(0,0,0,0.35);
            --shadow-glow: 0 0 16px rgba(88,166,255,0.2);
            --transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* ============================================================
           BASE PAGE
        ============================================================ */
        html, body, .stApp {
            background-color: var(--bg-color) !important;
            color: var(--text-color) !important;
            font-family: var(--font-stack) !important;
            -webkit-font-smoothing: antialiased;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-stack) !important;
            font-weight: 700;
            letter-spacing: -0.025em;
        }

        .block-container {
            padding: 28px 40px 60px !important;
            max-width: 1560px !important;
        }

        /* ============================================================
           CUSTOM SCROLLBAR
        ============================================================ */
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-track { background: var(--bg-color); }
        ::-webkit-scrollbar-thumb { background: #30363D; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }

        /* ============================================================
           SIDEBAR
        ============================================================ */
        [data-testid="stSidebar"] {
            background-color: var(--panel-color) !important;
            border-right: 1px solid var(--border-color) !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding: 20px 18px 32px !important;
        }
        div[data-testid="stSidebarUserContent"] {
            padding-top: 0.5rem;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }
        .sidebar-brand-icon {
            width: 34px;
            height: 34px;
            background: var(--accent-color);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }
        .sidebar-title {
            color: var(--text-color);
            font-size: 1.1rem;
            margin: 0;
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .sidebar-tagline {
            color: var(--text-muted);
            font-size: 0.78rem;
            line-height: 1.45;
            margin: 0 0 0 44px;
        }
        .sidebar-section-header {
            margin: 18px 0 8px;
            color: var(--text-muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .sidebar-divider {
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 14px 0;
        }
        .dashboard-sidebar-note {
            color: var(--text-muted);
            font-size: 0.8rem;
            line-height: 1.5;
        }

        /* Example repo pills */
        .example-repos {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 8px;
        }
        .example-repo-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            background: rgba(88,166,255,0.06);
            border: 1px solid rgba(88,166,255,0.12);
            border-radius: 6px;
            color: var(--accent-color);
            font-size: 0.78rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            text-decoration: none;
        }
        .example-repo-pill:hover {
            background: rgba(88,166,255,0.12);
            border-color: rgba(88,166,255,0.3);
        }

        /* ============================================================
           BUTTONS
        ============================================================ */
        .stButton > button, .stDownloadButton > button {
            background: linear-gradient(180deg, #21262D 0%, #171B21 100%) !important;
            color: var(--accent-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--radius-sm) !important;
            padding: 9px 18px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            font-family: var(--font-stack) !important;
            transition: var(--transition) !important;
            width: 100% !important;
            height: auto !important;
            letter-spacing: -0.01em !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: var(--accent-color) !important;
            color: #FFFFFF !important;
            box-shadow: var(--shadow-glow) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button:active, .stDownloadButton > button:active {
            transform: translateY(0) !important;
        }

        /* Primary / analyze button */
        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(180deg, #2E5FA3 0%, #1F6FEB 100%) !important;
            color: #FFFFFF !important;
            border-color: rgba(255,255,255,0.1) !important;
        }
        .stButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            box-shadow: 0 0 20px rgba(31,111,235,0.4) !important;
            border-color: var(--accent-color) !important;
        }

        /* ============================================================
           INPUTS
        ============================================================ */
        .stTextInput > div > div > input {
            background-color: var(--card-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-color) !important;
            padding: 10px 14px !important;
            font-size: 0.88rem !important;
            font-family: var(--font-stack) !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stTextInput > div > div > input::placeholder {
            color: var(--text-muted) !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--accent-color) !important;
            box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
            outline: none !important;
        }
        .stTextInput label {
            color: var(--text-muted) !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
        }

        /* ============================================================
           SELECTBOX
        ============================================================ */
        div[data-baseweb="select"] > div {
            background-color: var(--card-color) !important;
            border-color: var(--border-color) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-color) !important;
            font-size: 0.88rem !important;
        }
        div[data-baseweb="select"] > div:hover {
            border-color: var(--accent-color) !important;
        }
        div[data-baseweb="popover"] {
            background-color: var(--card-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--radius-md) !important;
        }

        /* ============================================================
           ANALYSIS PROGRESS TRACKER
        ============================================================ */
        .progress-container {
            background: var(--card-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            margin-top: 12px;
        }
        .stage-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 0;
            border-bottom: 1px solid rgba(48,54,61,0.4);
        }
        .stage-row:last-child { border-bottom: none; }
        .stage-name {
            font-size: 0.82rem;
            color: var(--text-muted);
            font-weight: 500;
        }
        .stage-row--running .stage-name { color: var(--accent-color); font-weight: 600; }
        .stage-row--success .stage-name { color: var(--text-color); }
        .stage-row--failed .stage-name { color: var(--danger-color); font-weight: 600; }
        .stage-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 0.72rem;
            font-weight: 700;
            flex-shrink: 0;
        }
        .stage-badge--pending {
            background: rgba(139,148,158,0.1);
            color: var(--text-muted);
            border: 1px solid rgba(139,148,158,0.2);
        }
        .stage-badge--running {
            background: rgba(88,166,255,0.15);
            color: var(--accent-color);
            border: 1px solid rgba(88,166,255,0.3);
            animation: pulse 1.5s infinite ease-in-out;
        }
        .stage-badge--success {
            background: rgba(63,185,80,0.15);
            color: var(--success-color);
            border: 1px solid rgba(63,185,80,0.3);
        }
        .stage-badge--failed {
            background: rgba(248,81,73,0.15);
            color: var(--danger-color);
            border: 1px solid rgba(248,81,73,0.3);
        }
        @keyframes pulse {
            0%,100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.1); opacity: 1; }
        }

        /* ============================================================
           DASHBOARD HEADER
        ============================================================ */
        .dashboard-header {
            background: linear-gradient(135deg, var(--panel-color) 0%, #1a2033 100%);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px 32px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 20px;
            margin-bottom: 28px;
            box-shadow: var(--shadow-md);
            position: relative;
            overflow: hidden;
        }
        .dashboard-header::before {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 3px; height: 100%;
            background: linear-gradient(180deg, var(--accent-color) 0%, #1f6feb 100%);
        }
        .dashboard-header-left { flex: 1; min-width: 0; }
        .dashboard-eyebrow {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--accent-color);
            font-weight: 700;
            margin-bottom: 6px;
            display: block;
        }
        .dashboard-title {
            margin: 0 0 8px;
            font-size: 1.8rem;
            letter-spacing: -0.03em;
            color: #FFFFFF;
            font-weight: 800;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .dashboard-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .repo-chip {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid;
            white-space: nowrap;
        }
        .repo-chip--default {
            background: rgba(88,166,255,0.08);
            border-color: rgba(88,166,255,0.2);
            color: var(--accent-color);
        }
        .repo-chip--success {
            background: rgba(63,185,80,0.08);
            border-color: rgba(63,185,80,0.25);
            color: var(--success-color);
        }
        .repo-chip--warning {
            background: rgba(210,153,34,0.08);
            border-color: rgba(210,153,34,0.25);
            color: var(--warning-color);
        }
        .repo-chip--danger {
            background: rgba(248,81,73,0.08);
            border-color: rgba(248,81,73,0.25);
            color: var(--danger-color);
        }
        .dashboard-header-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 10px;
            flex-shrink: 0;
        }
        .health-badge {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            font-weight: 800;
            border: 2px solid;
        }
        .health-badge__score {
            font-size: 1.4rem;
            line-height: 1;
            letter-spacing: -0.03em;
        }
        .health-badge__label {
            font-size: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            opacity: 0.8;
        }
        .health-badge--A, .health-badge--S {
            background: rgba(63,185,80,0.1);
            border-color: rgba(63,185,80,0.4);
            color: var(--success-color);
            box-shadow: 0 0 20px rgba(63,185,80,0.15);
        }
        .health-badge--B {
            background: rgba(88,166,255,0.1);
            border-color: rgba(88,166,255,0.35);
            color: var(--accent-color);
            box-shadow: 0 0 20px rgba(88,166,255,0.12);
        }
        .health-badge--C {
            background: rgba(210,153,34,0.1);
            border-color: rgba(210,153,34,0.3);
            color: var(--warning-color);
            box-shadow: 0 0 20px rgba(210,153,34,0.1);
        }
        .health-badge--D, .health-badge--F {
            background: rgba(248,81,73,0.1);
            border-color: rgba(248,81,73,0.3);
            color: var(--danger-color);
            box-shadow: 0 0 20px rgba(248,81,73,0.1);
        }

        /* ============================================================
           SECTION TITLES
        ============================================================ */
        .section-title {
            margin: 36px 0 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        .section-title h2 {
            margin: 0;
            color: #FFFFFF;
            font-size: 1.35rem;
            letter-spacing: -0.02em;
            font-weight: 700;
        }
        .section-title p {
            margin: 5px 0 0;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* ============================================================
           KPI CARDS
        ============================================================ */
        .kpi-card {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 20px 22px;
            box-shadow: var(--shadow-sm);
            color: var(--text-color);
            margin-bottom: 16px;
            min-height: 130px;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }
        .kpi-card::after {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(135deg, rgba(88,166,255,0.04) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }
        .kpi-card:hover {
            background: var(--card-color);
            border-color: var(--accent-color);
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg), var(--shadow-glow);
        }
        .kpi-card:hover::after { opacity: 1; }

        /* Color variants */
        .kpi-card--success { border-top: 2px solid var(--success-color); }
        .kpi-card--success:hover { border-color: var(--success-color); box-shadow: var(--shadow-lg), 0 0 16px rgba(63,185,80,0.2); }
        .kpi-card--success .kpi-card__icon { background: rgba(63,185,80,0.08); border-color: rgba(63,185,80,0.2); color: var(--success-color); }
        .kpi-card--warning { border-top: 2px solid var(--warning-color); }
        .kpi-card--warning:hover { border-color: var(--warning-color); box-shadow: var(--shadow-lg), 0 0 16px rgba(210,153,34,0.2); }
        .kpi-card--warning .kpi-card__icon { background: rgba(210,153,34,0.08); border-color: rgba(210,153,34,0.2); color: var(--warning-color); }
        .kpi-card--danger { border-top: 2px solid var(--danger-color); }
        .kpi-card--danger:hover { border-color: var(--danger-color); box-shadow: var(--shadow-lg), 0 0 16px rgba(248,81,73,0.2); }
        .kpi-card--danger .kpi-card__icon { background: rgba(248,81,73,0.08); border-color: rgba(248,81,73,0.2); color: var(--danger-color); }
        .kpi-card--accent { border-top: 2px solid var(--accent-color); }

        .kpi-card__top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .kpi-card__icon {
            align-items: center;
            background: rgba(88,166,255,0.06);
            border: 1px solid rgba(88,166,255,0.14);
            border-radius: 9px;
            color: var(--accent-color);
            display: inline-flex;
            font-size: 15px;
            height: 34px;
            width: 34px;
            justify-content: center;
            flex-shrink: 0;
        }
        .kpi-card__label {
            font-size: 0.7rem;
            color: var(--text-muted);
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        .kpi-card__value {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 6px;
            line-height: 1.1;
            color: #FFFFFF;
            letter-spacing: -0.03em;
        }
        .kpi-card__bottom {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }
        .kpi-card__subtitle {
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }
        .kpi-card__trend {
            font-size: 0.76rem;
            color: var(--success-color);
            font-weight: 700;
            flex-shrink: 0;
        }

        /* ============================================================
           SUMMARY CARDS
        ============================================================ */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }
        .summary-card {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 20px;
            color: var(--text-color);
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }
        .summary-card:hover {
            background: var(--card-color);
            border-color: var(--accent-color);
            transform: translateY(-2px);
        }
        .summary-card h3 {
            margin: 0 0 8px;
            color: #FFFFFF;
            font-size: 0.95rem;
            font-weight: 700;
        }
        .summary-card p {
            margin: 0;
            color: var(--text-muted);
            font-size: 0.88rem;
            line-height: 1.5;
        }

        /* ============================================================
           CHART CONTAINERS
        ============================================================ */
        .chart-card {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 4px 4px 0;
            box-shadow: var(--shadow-sm);
            margin-bottom: 16px;
            transition: var(--transition);
            overflow: hidden;
        }
        .chart-card:hover {
            border-color: rgba(88,166,255,0.25);
            box-shadow: var(--shadow-md);
        }

        /* ============================================================
           FOOTER
        ============================================================ */
        .dashboard-footer {
            padding: 36px 0 20px;
            color: var(--text-muted);
            font-size: 0.82rem;
            text-align: center;
            border-top: 1px solid var(--border-color);
            margin-top: 56px;
        }

        /* ============================================================
           METRIC BOX
        ============================================================ */
        .metric-box {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 18px 20px;
            margin-bottom: 14px;
            transition: var(--transition);
            min-height: 96px;
            box-shadow: var(--shadow-sm);
        }
        .metric-box:hover {
            background: var(--card-color);
            border-color: var(--accent-color);
            transform: translateY(-2px);
        }
        .metric-box__label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: 0.09em;
        }
        .metric-box__value {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 5px;
            color: #FFFFFF;
            letter-spacing: -0.02em;
        }
        .metric-box__description {
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* ============================================================
           REPOSITORY OVERVIEW
        ============================================================ */
        .repository-overview {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 22px 26px;
            margin-bottom: 28px;
            box-shadow: var(--shadow-md);
        }
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        .overview-item {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            transition: var(--transition);
        }
        .overview-item:hover {
            border-color: var(--accent-color);
            box-shadow: var(--shadow-sm);
        }
        .overview-item__label {
            display: block;
            color: var(--text-muted);
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .overview-item__value {
            display: block;
            color: var(--text-color);
            font-size: 0.9rem;
            line-height: 1.45;
            overflow-wrap: anywhere;
            font-weight: 600;
        }
        .overview-item__value a {
            color: var(--accent-color);
            text-decoration: none;
        }
        .overview-item__value a:hover {
            color: #FFFFFF;
            text-decoration: underline;
        }

        /* ============================================================
           REPOSITORY INTELLIGENCE
        ============================================================ */
        .repository-intelligence {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 26px 30px;
            margin-bottom: 28px;
            box-shadow: var(--shadow-md);
        }
        .intelligence-hero {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 22px;
        }
        .intelligence-eyebrow {
            color: var(--text-muted);
            display: block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            margin-bottom: 6px;
            text-transform: uppercase;
        }
        .intelligence-score {
            color: #FFFFFF;
            font-size: 3.8rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: -0.04em;
        }
        .intelligence-hero p {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin: 8px 0 0;
        }
        .intelligence-grade {
            align-items: center;
            background: rgba(88,166,255,0.08);
            border: 2px solid rgba(88,166,255,0.25);
            border-radius: 50%;
            color: var(--accent-color);
            display: flex;
            font-size: 2rem;
            font-weight: 800;
            justify-content: center;
            height: 84px;
            width: 84px;
            box-shadow: 0 0 24px rgba(88,166,255,0.15);
            flex-shrink: 0;
        }
        .intelligence-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 14px;
            margin-bottom: 22px;
        }
        .intelligence-score-card {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 16px;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }
        .intelligence-score-card:hover {
            border-color: var(--accent-color);
            transform: translateY(-2px);
            box-shadow: var(--shadow-sm);
        }
        .intelligence-score-card span {
            color: var(--text-muted);
            display: block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .intelligence-score-card strong {
            color: #FFFFFF;
            display: block;
            font-size: 1.9rem;
            line-height: 1;
            margin-bottom: 10px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }
        .intelligence-score-card small {
            color: var(--text-muted);
            display: block;
            font-size: 0.78rem;
            line-height: 1.4;
        }
        .score-bar {
            height: 3px;
            border-radius: 2px;
            background: var(--border-color);
            margin-top: 10px;
            overflow: hidden;
        }
        .score-bar__fill {
            height: 100%;
            border-radius: 2px;
            background: linear-gradient(90deg, var(--accent-color), #79c0ff);
            transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .intelligence-explanation {
            border-top: 1px solid var(--border-color);
            color: var(--text-color);
            font-size: 0.9rem;
            line-height: 1.65;
            margin: 0;
            padding-top: 18px;
        }

        /* ============================================================
           ENGINEERING INSIGHTS
        ============================================================ */
        .engineering-insights-section, .engineering-recommendations-section {
            margin-bottom: 28px;
        }
        .engineering-insights-grid, .engineering-actions-grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
        }
        .engineering-card {
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-left: 3px solid var(--accent-color);
            border-radius: var(--radius-lg);
            color: var(--text-color);
            min-height: 150px;
            padding: 20px 22px;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
            position: relative;
        }
        .engineering-card:hover {
            background: var(--card-color);
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }
        .engineering-card__top {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 14px;
        }
        .engineering-card__icon {
            align-items: center;
            background: rgba(88,166,255,0.08);
            border: 1px solid rgba(88,166,255,0.18);
            border-radius: 8px;
            color: var(--accent-color);
            display: inline-flex;
            font-size: 0.95rem;
            height: 30px;
            width: 30px;
            justify-content: center;
        }
        .engineering-card__severity {
            border: 1px solid var(--border-color);
            border-radius: 20px;
            color: var(--text-muted);
            font-size: 0.67rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            padding: 3px 9px;
            text-transform: uppercase;
        }
        .engineering-card h3 {
            color: #FFFFFF;
            font-size: 1rem;
            line-height: 1.4;
            margin: 0 0 8px;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .engineering-card p {
            color: var(--text-muted);
            font-size: 0.86rem;
            line-height: 1.55;
            margin: 0;
        }
        .engineering-card--good { border-left-color: var(--success-color); }
        .engineering-card--good .engineering-card__icon { background: rgba(63,185,80,0.08); border-color: rgba(63,185,80,0.2); color: var(--success-color); }
        .engineering-card--good .engineering-card__severity { border-color: rgba(63,185,80,0.3); color: var(--success-color); }
        .engineering-card--warning { border-left-color: var(--warning-color); }
        .engineering-card--warning .engineering-card__icon { background: rgba(210,153,34,0.08); border-color: rgba(210,153,34,0.2); color: var(--warning-color); }
        .engineering-card--warning .engineering-card__severity { border-color: rgba(210,153,34,0.3); color: var(--warning-color); }
        .engineering-card--critical { border-left-color: var(--danger-color); }
        .engineering-card--critical .engineering-card__icon { background: rgba(248,81,73,0.08); border-color: rgba(248,81,73,0.2); color: var(--danger-color); }
        .engineering-card--critical .engineering-card__severity { border-color: rgba(248,81,73,0.3); color: var(--danger-color); }

        /* ============================================================
           WELCOME / ONBOARDING PANEL
        ============================================================ */
        .welcome-panel {
            background: radial-gradient(ellipse at top, #1a2033 0%, var(--bg-color) 70%);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-xl);
            padding: 56px 48px 48px;
            color: var(--text-color);
            max-width: 880px;
            margin: 48px auto;
            text-align: center;
            box-shadow: var(--shadow-lg);
            position: relative;
            overflow: hidden;
        }
        .welcome-panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 3px;
            background: linear-gradient(90deg, var(--accent-color), var(--success-color), var(--warning-color));
        }
        .welcome-icon {
            font-size: 3.5rem;
            margin-bottom: 20px;
            display: block;
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%,100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
        }
        .welcome-panel h2 {
            font-size: 2rem;
            font-weight: 800;
            margin: 0 0 10px;
            color: #FFFFFF;
            letter-spacing: -0.04em;
        }
        .welcome-subtitle {
            font-size: 1rem;
            color: var(--text-muted);
            margin: 0 auto 36px;
            line-height: 1.6;
            max-width: 600px;
        }
        .welcome-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 36px;
            text-align: left;
        }
        .feature-item {
            background: rgba(28,33,40,0.7);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 20px;
            transition: var(--transition);
        }
        .feature-item:hover {
            transform: translateY(-4px);
            border-color: var(--accent-color);
            box-shadow: 0 8px 24px rgba(88,166,255,0.12);
        }
        .feature-icon {
            font-size: 1.4rem;
            display: block;
            margin-bottom: 12px;
        }
        .feature-item strong {
            display: block;
            color: #FFFFFF;
            font-size: 0.95rem;
            margin-bottom: 6px;
            font-weight: 700;
        }
        .feature-item span {
            color: var(--text-muted);
            font-size: 0.83rem;
            line-height: 1.5;
        }
        .welcome-instruction {
            background: rgba(88,166,255,0.05);
            border: 1px solid rgba(88,166,255,0.15);
            border-radius: var(--radius-md);
            padding: 14px 22px;
            font-size: 0.9rem;
            color: var(--accent-color);
            display: inline-block;
            max-width: 100%;
            font-weight: 500;
        }

        /* ============================================================
           STREAMLIT OVERRIDES — misc
        ============================================================ */
        .stAlert > div {
            border-radius: var(--radius-md) !important;
            font-family: var(--font-stack) !important;
        }
        div[data-testid="stSpinner"] > div {
            border-top-color: var(--accent-color) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _discover_repositories() -> List[str]:
    """Discover repository options from processed repository CSV files."""
    if not PROCESSED_DIR.exists():
        logger.warning("_discover_repositories: PROCESSED_DIR %s does not exist", PROCESSED_DIR)
        return []

    repositories: List[str] = []
    for path in sorted(PROCESSED_DIR.glob(f"*{REPOSITORY_SUFFIX}")):
        try:
            prefix = path.name[:-len(REPOSITORY_SUFFIX)]
            df = pd.read_csv(path, nrows=1)
            full_name = df.loc[0, "full_name"] if "full_name" in df.columns else None
            if isinstance(full_name, str) and full_name.strip():
                candidate_prefix = _format_repository_file_prefix(full_name)
                if (PROCESSED_DIR / f"{candidate_prefix}{REPOSITORY_SUFFIX}").exists():
                    repositories.append(full_name)
                    continue
            repo_name = prefix.replace("_", "/", 1)
            repositories.append(repo_name)
        except Exception as exc:
            logger.warning("_discover_repositories: failed to read %s: %s", path, exc)
            continue
    return repositories


def _parse_github_repository_url(repository_url: str) -> Tuple[str, str]:
    """Validate a GitHub repository URL and return owner/repo."""
    if not repository_url or not repository_url.strip():
        raise ValueError("Repository URL must not be empty.")

    normalized_url = repository_url.strip()
    if not re.match(r"^https?://", normalized_url, re.IGNORECASE):
        normalized_url = f"https://{normalized_url}"

    parsed = urlparse(normalized_url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Please enter a valid GitHub repository URL.")

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        raise ValueError("GitHub URL must include owner and repository name.")

    owner = path_parts[0].strip()
    repo = path_parts[1].strip().removesuffix(".git")
    if not owner or not repo:
        raise ValueError("GitHub URL must include owner and repository name.")

    return owner, repo


def _format_repository_file_prefix(repository: str) -> str:
    return repository.replace("/", "_")


def _load_dataframe(file_name: str, parse_dates: Optional[List[str]] = None) -> pd.DataFrame:
    """Load a processed CSV file into a DataFrame."""
    file_path = PROCESSED_DIR / file_name
    if not file_path.exists():
        logger.warning("_load_dataframe: file does not exist: %s", file_path)
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path, parse_dates=parse_dates or [])
    except Exception as exc:
        logger.error("_load_dataframe: failed to parse CSV %s: %s", file_path, exc)
        return pd.DataFrame()


def _file_timestamps(repository: str) -> Tuple[float, ...]:
    """Return modification timestamps for repository-related processed files."""
    prefix = _format_repository_file_prefix(repository)
    files = [
        PROCESSED_DIR / f"{prefix}{suffix}"
        for suffix in (
            REPOSITORY_SUFFIX,
            COMMITS_SUFFIX,
            CONTRIBUTORS_SUFFIX,
            ISSUES_SUFFIX,
            LANGUAGES_SUFFIX,
        )
    ]
    return tuple(path.stat().st_mtime if path.exists() else 0.0 for path in files)


def _render_stage_progress(
    stage_container: st.delta_generator.DeltaGenerator,
    stage_statuses: Dict[str, str],
) -> None:
    """Render progress indicator for each stage in the sidebar."""
    html_lines = []
    for stage, status in stage_statuses.items():
        if status == "pending":
            badge_class = "stage-badge--pending"
            badge_text = "·"
        elif status == "running":
            badge_class = "stage-badge--running"
            badge_text = "◌"
        elif status == "success":
            badge_class = "stage-badge--success"
            badge_text = "✓"
        else:
            badge_class = "stage-badge--failed"
            badge_text = "✗"

        html_lines.append(
            f"<div class='stage-row stage-row--{status}'>"
            f"<span class='stage-badge {badge_class}'>{badge_text}</span>"
            f"<span class='stage-name'>{escape(stage)}</span>"
            f"</div>"
        )

    container_html = f"<div class='progress-container'>{''.join(html_lines)}</div>"
    stage_container.markdown(container_html, unsafe_allow_html=True)


def _update_stage_status(
    stage_statuses: Dict[str, str],
    current_stage: str,
    status: str,
) -> None:
    stage_statuses[current_stage] = status


def _build_stage_statuses() -> Dict[str, str]:
    """Create the ordered stage status map for the analysis workflow."""
    return {
        "Validating repository": "pending",
        "Fetching repository metadata": "pending",
        "Fetching commits": "pending",
        "Fetching contributors": "pending",
        "Fetching issues": "pending",
        "Fetching languages": "pending",
        "Saving raw data": "pending",
        "Cleaning data": "pending",
        "Running analytics": "pending",
        "Calculating repository health": "pending",
        "Updating dashboard": "pending",
    }


def _reset_stage_statuses(stage_container: st.delta_generator.DeltaGenerator, stage: str, status: str) -> None:
    """Reset the sidebar progress states to reflect an error condition."""
    stage_statuses = _build_stage_statuses()
    stage_statuses[stage] = status
    _render_stage_progress(stage_container, stage_statuses)


def _fetch_github_data(
    owner: str,
    repo: str,
    advance: Optional[Any] = None,
) -> Tuple[Any, Any, Any, Any, Any]:
    """Fetch repository data from the GitHub client using the existing modules."""
    client = GitHubClient()

    if advance is not None:
        advance("Fetching repository metadata", "running")
    repository = client.get_repository(owner, repo)
    if advance is not None:
        advance("Fetching repository metadata", "success")

    if advance is not None:
        advance("Fetching commits", "running")
    commits = client.get_commits(owner, repo)
    if advance is not None:
        advance("Fetching commits", "success")

    if advance is not None:
        advance("Fetching contributors", "running")
    contributors = client.get_contributors(owner, repo)
    if advance is not None:
        advance("Fetching contributors", "success")

    if advance is not None:
        advance("Fetching issues", "running")
    issues = client.get_issues(owner, repo)
    if advance is not None:
        advance("Fetching issues", "success")

    if advance is not None:
        advance("Fetching languages", "running")
    languages = client.get_languages(owner, repo)
    if advance is not None:
        advance("Fetching languages", "success")

    return repository, commits, contributors, issues, languages


def _save_raw_data(
    owner: str,
    repo: str,
    repository: Any,
    commits: Any,
    contributors: Any,
    issues: Any,
    languages: Any,
) -> None:
    storage = DataStorage()
    storage.save_repository(owner, repo, repository)
    storage.save_commits(owner, repo, commits)
    storage.save_contributors(owner, repo, contributors)
    storage.save_issues(owner, repo, issues)
    storage.save_languages(owner, repo, languages)


def _clean_repository_data(owner: str, repo: str) -> None:
    cleaner = DataCleaner()
    cleaner.save_cleaned_repository(owner, repo)
    cleaner.save_cleaned_commits(owner, repo)
    cleaner.save_cleaned_contributors(owner, repo)
    cleaner.save_cleaned_issues(owner, repo)
    cleaner.save_cleaned_languages(owner, repo)


def _load_repository_data(repository: str, timestamps: Tuple[float, ...] = ()) -> Dict[str, pd.DataFrame]:
    """Load processed DataFrames for the selected repository."""
    prefix = _format_repository_file_prefix(repository)
    return {
        "repository_df": _load_dataframe(f"{prefix}{REPOSITORY_SUFFIX}", parse_dates=["created_at", "updated_at", "pushed_at"]),
        "commits_df": _load_dataframe(f"{prefix}{COMMITS_SUFFIX}", parse_dates=["commit_author_date", "commit_committer_date"]),
        "contributors_df": _load_dataframe(f"{prefix}{CONTRIBUTORS_SUFFIX}"),
        "issues_df": _load_dataframe(f"{prefix}{ISSUES_SUFFIX}", parse_dates=["created_at", "updated_at", "closed_at"]),
        "languages_df": _load_dataframe(f"{prefix}{LANGUAGES_SUFFIX}"),
    }


def _build_metrics(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Build dashboard KPI metrics from analytics engine outputs."""
    engine = AnalyticsEngine(
        repository_df=data["repository_df"],
        commits_df=data["commits_df"],
        contributors_df=data["contributors_df"],
        issues_df=data["issues_df"],
        languages_df=data["languages_df"],
    )

    metrics: Dict[str, Any] = {
        "total_commits": 0,
        "total_contributors": 0,
        "total_issues": 0,
        "open_issues": 0,
        "closed_issues": 0,
        "open_pull_requests": 0,
        "merged_pull_requests": 0,
        "issue_close_rate": 0.0,
        "average_comments": 0.0,
        "total_contributions": 0,
        "top_contributor": "Unknown",
        "top_contributor_commits": 0,
        "repository_age_days": 0,
        "stars": 0,
        "forks": 0,
        "watchers": 0,
        "health_score": 0.0,
        "health_grade": "Pending",
        "repository_health": 0.0,
        "maintenance_score": 0.0,
        "community_score": 0.0,
        "popularity_score": 0.0,
        "overall_grade": "Pending",
        "health_label": "Pending",
        "score_explanation": "Repository intelligence is unavailable until repository analytics are loaded.",
        "primary_language": "Unknown",
        "days_since_last_commit": 0,
        "recent_commits_30_days": 0,
        "previous_commits_30_days": 0,
        "commit_activity_change_pct": 0.0,
        "top_contributor_share": 0.0,
        "total_pull_requests": 0,
        "pull_request_backlog_ratio": 0.0,
        "issue_backlog_ratio": 0.0,
        "language_count": 0,
        "has_description": False,
        "has_license": False,
    }

    try:
        repo_summary = engine.repository_summary()
        metrics["repository_age_days"] = int(repo_summary.get("age_days", 0))
        metrics["primary_language"] = repo_summary.get("language") or "Unknown"
        metrics["stars"] = int(repo_summary.get("stars", 0))
        metrics["forks"] = int(repo_summary.get("forks", 0))
        metrics["watchers"] = int(repo_summary.get("watchers", 0))
    except AnalyticsError:
        pass

    repository_df = data["repository_df"]
    if not repository_df.empty:
        repo_row = repository_df.iloc[0]
        description = repo_row.get("description")
        license_value = repo_row.get("license")
        metrics["has_description"] = isinstance(description, str) and bool(description.strip())
        metrics["has_license"] = isinstance(license_value, str) and bool(license_value.strip())

    try:
        commit_stats = engine.commit_statistics()
        metrics["total_commits"] = int(commit_stats.get("total_commits", 0))
    except AnalyticsError:
        metrics["total_commits"] = 0

    commits_df = data["commits_df"]
    if not commits_df.empty and "commit_author_date" in commits_df.columns:
        commit_dates = pd.to_datetime(commits_df["commit_author_date"], errors="coerce", utc=True).dropna()
        if not commit_dates.empty:
            latest_commit = commit_dates.max()
            metrics["days_since_last_commit"] = max(
                int((pd.Timestamp.now(tz="UTC") - latest_commit).days),
                0,
            )
            recent_start = latest_commit - pd.Timedelta(days=30)
            previous_start = latest_commit - pd.Timedelta(days=60)
            recent_commits = int((commit_dates >= recent_start).sum())
            previous_commits = int(((commit_dates >= previous_start) & (commit_dates < recent_start)).sum())
            metrics["recent_commits_30_days"] = recent_commits
            metrics["previous_commits_30_days"] = previous_commits
            if previous_commits:
                metrics["commit_activity_change_pct"] = round(
                    (recent_commits - previous_commits) / previous_commits * 100,
                    2,
                )
            elif recent_commits:
                metrics["commit_activity_change_pct"] = 100.0

    try:
        contributor_stats = engine.contributor_statistics()
        metrics["total_contributors"] = int(contributor_stats.get("total_contributors", 0))
        metrics["total_contributions"] = int(contributor_stats.get("total_contributions", 0))
        top_contributor = contributor_stats.get("top_contributor", {}) or {}
        metrics["top_contributor"] = top_contributor.get("login") or "Unknown"
        metrics["top_contributor_commits"] = int(top_contributor.get("contributions", 0))
        if metrics["total_contributions"]:
            metrics["top_contributor_share"] = round(
                metrics["top_contributor_commits"] / metrics["total_contributions"] * 100,
                2,
            )
    except AnalyticsError:
        metrics["total_contributors"] = 0
        metrics["total_contributions"] = 0
        metrics["top_contributor"] = "Unknown"
        metrics["top_contributor_commits"] = 0

    try:
        issue_stats = engine.issue_statistics()
        metrics["open_issues"] = int(issue_stats.get("open_issues", 0))
        metrics["closed_issues"] = int(issue_stats.get("closed_issues", 0))
        metrics["total_issues"] = int(issue_stats.get("total_issues", 0))
        metrics["issue_close_rate"] = float(issue_stats.get("issue_close_rate", 0.0))
        metrics["average_comments"] = float(issue_stats.get("average_comments", 0.0))
        if metrics["total_issues"]:
            metrics["issue_backlog_ratio"] = round(
                metrics["open_issues"] / metrics["total_issues"] * 100,
                2,
            )
    except AnalyticsError:
        metrics["open_issues"] = 0
        metrics["closed_issues"] = 0
        metrics["total_issues"] = 0
        metrics["issue_close_rate"] = 0.0
        metrics["average_comments"] = 0.0

    try:
        pull_request_stats = engine.pull_request_statistics()
        metrics["total_pull_requests"] = int(pull_request_stats.get("total_pull_requests", 0))
        metrics["open_pull_requests"] = int(pull_request_stats.get("open_pull_requests", 0))
        metrics["merged_pull_requests"] = int(pull_request_stats.get("merged_pull_requests", 0))
        if metrics["total_pull_requests"]:
            metrics["pull_request_backlog_ratio"] = round(
                metrics["open_pull_requests"] / metrics["total_pull_requests"] * 100,
                2,
            )
    except AnalyticsError:
        metrics["total_pull_requests"] = 0
        metrics["open_pull_requests"] = 0
        metrics["merged_pull_requests"] = 0

    languages_df = data["languages_df"]
    if not languages_df.empty and "language" in languages_df.columns:
        metrics["language_count"] = int(languages_df["language"].nunique(dropna=True))

    try:
        health_score = RepositoryHealthScore(engine).calculate_health_score()
        metrics["health_score"] = round(float(health_score.get("score", 0.0)), 2)
        metrics["health_grade"] = health_score.get("grade", "Pending")
        metrics["repository_health"] = round(float(health_score.get("repository_health", 0.0)), 2)
        metrics["maintenance_score"] = round(float(health_score.get("maintenance_score", 0.0)), 2)
        metrics["community_score"] = round(float(health_score.get("community_score", 0.0)), 2)
        metrics["popularity_score"] = round(float(health_score.get("popularity_score", 0.0)), 2)
        metrics["overall_grade"] = health_score.get("overall_grade", metrics["health_grade"])
        metrics["health_label"] = health_score.get("health_label", "Pending")
        metrics["score_explanation"] = health_score.get("summary", metrics["score_explanation"])
    except (HealthScoreError, AnalyticsError):
        metrics["health_score"] = 0.0
        metrics["health_grade"] = "Pending"
        metrics["overall_grade"] = "Pending"

    return metrics


def _get_repository_value(row: pd.Series, key: str, default: Any = "Not available") -> Any:
    """Return a display-safe repository metadata value from a repository row."""
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return value


def _format_count(value: Any) -> str:
    if pd.isna(value):
        return "Not available"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _format_date(value: Any) -> str:
    timestamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return "Not available"
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _repository_age_days(value: Any) -> str:
    created_at = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(created_at):
        return "Not available"
    return f"{max((pd.Timestamp.now(tz='UTC') - created_at).days, 0):,} days"


def _format_repository_size(value: Any) -> str:
    if pd.isna(value):
        return "Not available"
    try:
        size_kb = int(value)
    except (TypeError, ValueError):
        return str(value)
    if size_kb >= 1024:
        return f"{size_kb / 1024:.1f} MB"
    return f"{size_kb:,} KB"


def _build_repository_overview(repository_df: pd.DataFrame) -> Dict[str, str]:
    """Build the Repository Overview section from live GitHub repository metadata."""
    if repository_df.empty:
        return {}

    row = repository_df.iloc[0]
    return {
        "Repository Name": str(_get_repository_value(row, "repository_name")),
        "Owner": str(_get_repository_value(row, "owner_login")),
        "Description": str(_get_repository_value(row, "description", "No description provided")),
        "Repository URL": str(_get_repository_value(row, "repository_url")),
        "Primary Language": str(_get_repository_value(row, "language")),
        "Stars": _format_count(_get_repository_value(row, "stars")),
        "Forks": _format_count(_get_repository_value(row, "forks")),
        "Watchers": _format_count(_get_repository_value(row, "watchers")),
        "Open Issues": _format_count(_get_repository_value(row, "open_issues")),
        "License": str(_get_repository_value(row, "license", "No license detected")),
        "Default Branch": str(_get_repository_value(row, "default_branch")),
        "Repository Age": _repository_age_days(_get_repository_value(row, "created_at")),
        "Created Date": _format_date(_get_repository_value(row, "created_at")),
        "Last Updated": _format_date(_get_repository_value(row, "updated_at")),
        "Last Push Date": _format_date(_get_repository_value(row, "pushed_at")),
        "Repository Visibility": str(_get_repository_value(row, "visibility")).title(),
        "Repository Size": _format_repository_size(_get_repository_value(row, "size")),
    }


def _build_health_history(commits_df: pd.DataFrame, current_score: Any) -> pd.DataFrame:
    """Build a lightweight health score trend from weekly commit activity."""
    if commits_df.empty or "commit_author_date" not in commits_df.columns:
        return pd.DataFrame()

    df = commits_df.copy()
    df["commit_author_date"] = pd.to_datetime(df["commit_author_date"], errors="coerce", utc=True).dt.tz_convert(None)
    df = df.dropna(subset=["commit_author_date"])
    if df.empty:
        return pd.DataFrame()

    df["week_label"] = df["commit_author_date"].dt.to_period("W").apply(lambda value: value.start_time.strftime("%Y-%m-%d"))
    weekly = df.groupby("week_label")["commit_author_date"].size().reset_index(name="commits").sort_values("week_label")
    max_commits = weekly["commits"].max() if not weekly.empty else 0
    normalized_score = float(current_score) if isinstance(current_score, (int, float)) else 0.0
    weekly["health_score"] = weekly["commits"].apply(
        lambda commits: round((commits / max_commits) * normalized_score if max_commits else 0.0, 2)
    )
    weekly["date"] = pd.to_datetime(weekly["week_label"], errors="coerce").dt.strftime("%Y-%m-%d")
    return weekly[["date", "health_score"]]


def _build_issue_timeline(issues_df: pd.DataFrame) -> pd.DataFrame:
    """Build daily opened and closed issue counts for the issue timeline."""
    if issues_df.empty:
        return pd.DataFrame({"date": [], "opened": [], "closed": []})

    frames: List[pd.DataFrame] = []
    if "created_at" in issues_df.columns:
        opened = issues_df.copy()
        opened["date"] = pd.to_datetime(opened["created_at"], errors="coerce").dt.normalize()
        opened = opened.dropna(subset=["date"])
        if not opened.empty:
            frames.append(opened.groupby("date").size().reset_index(name="opened"))

    if "closed_at" in issues_df.columns:
        closed = issues_df.copy()
        closed["date"] = pd.to_datetime(closed["closed_at"], errors="coerce").dt.normalize()
        closed = closed.dropna(subset=["date"])
        if not closed.empty:
            frames.append(closed.groupby("date").size().reset_index(name="closed"))

    if not frames:
        return pd.DataFrame({"date": [], "opened": [], "closed": []})

    timeline = frames[0]
    for frame in frames[1:]:
        timeline = timeline.merge(frame, on="date", how="outer")
    for column in ("opened", "closed"):
        if column not in timeline.columns:
            timeline[column] = 0
        timeline[column] = timeline[column].fillna(0).astype(int)

    timeline = timeline.sort_values("date")
    timeline["date"] = timeline["date"].dt.strftime("%Y-%m-%d")
    return timeline[["date", "opened", "closed"]]


def _build_chart_data(data: Dict[str, pd.DataFrame], metrics: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Build chart data frames for the dashboard charts."""
    commits_df = data["commits_df"].copy()
    chart_data: Dict[str, pd.DataFrame] = {}

    if not commits_df.empty and "commit_author_date" in commits_df.columns:
        commits_df["date"] = pd.to_datetime(commits_df["commit_author_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        commits_summary = (
            commits_df.groupby("date")
            .size()
            .reset_index(name="commits")
            .sort_values("date")
        )
        chart_data["commits"] = commits_summary
    else:
        chart_data["commits"] = pd.DataFrame({"date": [], "commits": []})

    contributors_df = data["contributors_df"].copy()
    if not contributors_df.empty and "login" in contributors_df.columns and "contributions" in contributors_df.columns:
        chart_data["contributors"] = (
            contributors_df.sort_values("contributions", ascending=False)
            .head(10)
            [["login", "contributions"]]
            .rename(columns={"login": "contributor"})
        )
    else:
        chart_data["contributors"] = pd.DataFrame({"contributor": [], "contributions": []})

    issues_df = data["issues_df"].copy()
    if not issues_df.empty and "state" in issues_df.columns:
        chart_data["issues"] = (
            issues_df["state"].fillna("Unknown")
            .str.title()
            .value_counts()
            .reset_index(name="count")
            .rename(columns={"index": "state"})
        )
    else:
        chart_data["issues"] = pd.DataFrame({"state": [], "count": []})
    chart_data["issue_timeline"] = _build_issue_timeline(issues_df)

    languages_df = data["languages_df"].copy()
    if not languages_df.empty and "language" in languages_df.columns and "bytes" in languages_df.columns:
        chart_data["languages"] = languages_df.sort_values("bytes", ascending=False)
    else:
        chart_data["languages"] = pd.DataFrame({"language": [], "bytes": []})

    chart_data["raw_commits"] = commits_df
    chart_data["raw_contributors"] = contributors_df
    chart_data["raw_issues"] = issues_df
    chart_data["health_history"] = _build_health_history(commits_df, metrics.get("health_score", 0))

    return chart_data


def _render_export_controls(metrics: Dict[str, Any], chart_data: Dict[str, pd.DataFrame]) -> None:
    """Render export buttons in the sidebar for analytics assets."""
    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>📤 Export Analytics</h4>",
        unsafe_allow_html=True,
    )

    csv_bytes = export_to_csv(metrics, chart_data)
    json_bytes = export_to_json(metrics, chart_data)
    try:
        pdf_bytes = export_to_pdf(metrics, chart_data, "repository_analytics.pdf")
    except ImportError:
        pdf_bytes = None

    st.sidebar.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="repository_analytics.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="⬇ Download JSON",
        data=json_bytes,
        file_name="repository_analytics.json",
        mime="application/json",
    )

    if pdf_bytes is not None:
        st.sidebar.download_button(
            label="⬇ Download PDF",
            data=pdf_bytes,
            file_name="repository_analytics.pdf",
            mime="application/pdf",
        )
    else:
        st.sidebar.caption("Install reportlab to enable PDF export.")


def _load_processed_data(repository: str) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    timeline = _file_timestamps(repository)
    repository_data = _load_repository_data(repository, timeline)
    metrics = _build_metrics(repository_data)
    return repository_data, metrics


def _render_dashboard_for_repository(repository: str) -> None:
    repository_data, metrics = _load_processed_data(repository)
    if repository_data["repository_df"].empty:
        logger.warning("_render_dashboard_for_repository: repository_df is empty for %s", repository)
        st.warning(
            f"⚠️ Processed data for repository '{repository}' could not be loaded or is empty. "
            "Please analyze the repository using the sidebar or select a different repository."
        )
        return
    repository_overview = _build_repository_overview(repository_data["repository_df"])
    chart_data = _build_chart_data(repository_data, metrics)
    dashboard_insights = generate_engineering_insights(metrics)
    _render_export_controls(metrics, chart_data)
    render_dashboard(metrics, chart_data, dashboard_insights, repository_overview)


def _analyze_repository(repository_url: str, stage_container: st.delta_generator.DeltaGenerator) -> str:
    stage_statuses = _build_stage_statuses()

    def advance(stage: str, status: str) -> None:
        _update_stage_status(stage_statuses, stage, status)
        _render_stage_progress(stage_container, stage_statuses)

    advance("Validating repository", "running")
    owner, repo = _parse_github_repository_url(repository_url)
    advance("Validating repository", "success")

    advance("Fetching repository metadata", "running")
    repository, commits, contributors, issues, languages = _fetch_github_data(owner, repo, advance)
    advance("Fetching repository metadata", "success")

    advance("Saving raw data", "running")
    _save_raw_data(owner, repo, repository, commits, contributors, issues, languages)
    advance("Saving raw data", "success")

    advance("Cleaning data", "running")
    _clean_repository_data(owner, repo)
    advance("Cleaning data", "success")

    advance("Running analytics", "running")
    repository_data = _load_repository_data(f"{owner}/{repo}", _file_timestamps(f"{owner}/{repo}"))
    _build_metrics(repository_data)
    advance("Running analytics", "success")

    advance("Calculating repository health", "running")
    try:
        engine = AnalyticsEngine(
            repository_df=repository_data["repository_df"],
            commits_df=repository_data["commits_df"],
            contributors_df=repository_data["contributors_df"],
            issues_df=repository_data["issues_df"],
            languages_df=repository_data["languages_df"],
        )
        RepositoryHealthScore(engine).calculate_health_score()
    except (HealthScoreError, AnalyticsError) as exc:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "_analyze_repository: health score calculation failed for %s/%s: %s",
            owner, repo, exc,
        )
    advance("Calculating repository health", "success")

    advance("Updating dashboard", "running")
    advance("Updating dashboard", "success")

    return f"{owner}/{repo}"


def main() -> None:
    """Dashboard entry point for Streamlit."""
    _configure_page()

    discovered_repos = _discover_repositories()

    # Automatically select the first repository on initial load if repositories exist
    if "selected_repository" not in st.session_state and discovered_repos:
        st.session_state["selected_repository"] = sorted(discovered_repos)[0]

    repository_url, analyze_button, selected_repo = render_sidebar(discovered_repos)
    stage_container = st.sidebar.container()

    # Sync selectbox change to session state and trigger rerun
    if selected_repo != st.session_state.get("selected_repository", ""):
        st.session_state["selected_repository"] = selected_repo
        st.rerun()

    selected_repository = st.session_state.get("selected_repository", "")

    if analyze_button:
        try:
            selected_repository = _analyze_repository(repository_url, stage_container)
            st.session_state["selected_repository"] = selected_repository

            st.cache_data.clear()
            st.success(f"✓ Analysis complete for {selected_repository}.")
            st.rerun()

        except ValueError as exc:
            logger.warning("Validation failed for repository URL '%s': %s", repository_url, exc)
            _reset_stage_statuses(stage_container, "Validating repository", "failed")
            st.error(str(exc))
            selected_repository = ""
            st.session_state["selected_repository"] = ""

        except GitHubNotFoundError as exc:
            logger.warning("Repository not found on GitHub for URL '%s': %s", repository_url, exc)
            _reset_stage_statuses(stage_container, "Validating repository", "failed")
            st.error("Repository not found on GitHub. Please verify the URL.")
            selected_repository = ""
            st.session_state["selected_repository"] = ""

        except GitHubRateLimitError as exc:
            logger.error("GitHub API rate limit reached: %s", exc)
            _reset_stage_statuses(stage_container, "Fetching repository metadata", "failed")
            st.error("GitHub API rate limit reached. Please wait and try again.")
            selected_repository = ""
            st.session_state["selected_repository"] = ""

        except GitHubPrivateRepositoryError as exc:
            logger.warning("Private or inaccessible repository: %s", exc)
            _reset_stage_statuses(stage_container, "Fetching repository metadata", "failed")
            st.error("Unable to access repository. It may be private or require different credentials.")
            selected_repository = ""
            st.session_state["selected_repository"] = ""

        except GitHubAPIError as exc:
            logger.error("GitHub API error: %s", exc)
            _reset_stage_statuses(stage_container, "Fetching repository metadata", "failed")
            st.error(f"GitHub API error: {exc}")
            selected_repository = ""
            st.session_state["selected_repository"] = ""

        except (DataStorageError, DataCleaningError, AnalyticsError, HealthScoreError) as exc:
            logger.error("Repository analysis failed: %s", exc)
            _reset_stage_statuses(stage_container, "Running analytics", "failed")
            st.error(f"Repository analysis failed: {exc}")
            selected_repository = ""
            st.session_state["selected_repository"] = ""

    if selected_repository:
        with st.spinner("Loading analytics…"):
            try:
                _render_dashboard_for_repository(selected_repository)
            except Exception as exc:
                logger.error("Unable to render dashboard for %s: %s", selected_repository, exc, exc_info=True)
                st.error(f"Unable to render dashboard: {exc}")
    else:
        st.markdown(
            """
            <div class="welcome-panel">
                <div class="welcome-icon">📊</div>
                <h2>Welcome to RepoHealth Analyzer</h2>
                <p class="welcome-subtitle">
                    Comprehensive engineering intelligence and health scores for GitHub repositories.
                    No repository data has been loaded yet.
                </p>
                <div class="welcome-instruction">
                    👈 Paste a public GitHub repository URL in the sidebar (e.g., <code>https://github.com/owner/repo</code>) and click <strong>🚀 Analyze Repository</strong> to generate insights.
                </div>
                <div class="welcome-features" style="margin-top: 36px;">
                    <div class="feature-item">
                        <span class="feature-icon">📈</span>
                        <strong>Commit Activity</strong>
                        <span>Track velocity, commit frequency, and daily contribution trends.</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">👥</span>
                        <strong>Contributor Health</strong>
                        <span>Analyze contributor distribution, community churn, and top committer shares.</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">⚡</span>
                        <strong>Issue & PR Dynamics</strong>
                        <span>Monitor issue close rates, resolution speed, and open PR backlogs.</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">🛡️</span>
                        <strong>Health Scoring</strong>
                        <span>Compute an overarching 0-100 repository health score and letter grade.</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

if __name__ == "__main__":
    main()