"""Sidebar controls for the Streamlit dashboard."""

from typing import List, Tuple

import streamlit as st

from .theme import SIDEBAR_COLOR, TEXT_COLOR, SECONDARY_COLOR, PRIMARY_COLOR

_QUICK_EXAMPLES = [
    ("microsoft/vscode", "https://github.com/microsoft/vscode"),
    ("facebook/react", "https://github.com/facebook/react"),
    ("torvalds/linux", "https://github.com/torvalds/linux"),
]


def render_sidebar(discovered_repos: List[str]) -> Tuple[str, bool, str]:
    """Render repository input, analyze button, and filter controls."""

    # ── Brand Header ──────────────────────────────────────────────────────────
    st.sidebar.markdown(
        """
        <div class='sidebar-brand'>
            <div class='sidebar-brand-icon'>📊</div>
            <span class='sidebar-title'>RepoHealth</span>
        </div>
        <p class='sidebar-tagline'>Premium engineering analytics for GitHub repositories.</p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

    # ── Switch Repository ──────────────────────────────────────────────────────
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>🗂 Switch Repository</h4>",
        unsafe_allow_html=True,
    )
    current_selected = st.session_state.get("selected_repository", "")

    options = [""] + sorted(discovered_repos)
    default_idx = 0
    if current_selected in options:
        default_idx = options.index(current_selected)
    elif len(options) > 1:
        default_idx = 1
        st.session_state["selected_repository"] = options[1]

    selected_repo = st.sidebar.selectbox(
        "Select an analyzed repository",
        options=options,
        index=default_idx,
        format_func=lambda x: "Select repository…" if x == "" else x,
        key="sidebar_repo_selectbox",
        label_visibility="collapsed",
    )

    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

    # ── Analyze New Repository ─────────────────────────────────────────────────
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>🔍 Analyze New Repository</h4>",
        unsafe_allow_html=True,
    )
    repository_url = st.sidebar.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/owner/repo",
        key="repository_url_input",
        label_visibility="collapsed",
    )

    analyze_button = st.sidebar.button("🚀 Analyze Repository", key="analyze_repository")

    # ── Quick Examples ─────────────────────────────────────────────────────────
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>⚡ Quick Examples</h4>",
        unsafe_allow_html=True,
    )
    pills_html = "<div class='example-repos'>"
    for name, url in _QUICK_EXAMPLES:
        pills_html += (
            f"<span class='example-repo-pill' title='{url}'>⬡ {name}</span>"
        )
    pills_html += "</div>"
    st.sidebar.markdown(pills_html, unsafe_allow_html=True)

    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────────
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>⚙ Filters</h4>",
        unsafe_allow_html=True,
    )
    st.sidebar.checkbox("Show closed issues", value=True)
    st.sidebar.checkbox("Show pull requests", value=True)
    st.sidebar.checkbox("Show top contributors only", value=False)

    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<p class='dashboard-sidebar-note'>Analyze any public GitHub repository and explore real-time engineering signals.</p>",
        unsafe_allow_html=True,
    )

    return repository_url, analyze_button, selected_repo
