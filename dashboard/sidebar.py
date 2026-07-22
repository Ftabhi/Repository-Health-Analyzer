"""Sidebar controls for the Streamlit dashboard."""

from typing import List, Tuple

import streamlit as st

_QUICK_EXAMPLES = [
    ("microsoft/vscode", "https://github.com/microsoft/vscode"),
    ("facebook/react", "https://github.com/facebook/react"),
    ("torvalds/linux", "https://github.com/torvalds/linux"),
    ("streamlit/streamlit", "https://github.com/streamlit/streamlit"),
    ("tensorflow/tensorflow", "https://github.com/tensorflow/tensorflow"),
    ("pytorch/pytorch", "https://github.com/pytorch/pytorch"),
    ("django/django", "https://github.com/django/django"),
    ("pallets/flask", "https://github.com/pallets/flask"),
    ("fastapi/fastapi", "https://github.com/fastapi/fastapi"),
    ("microsoft/typescript", "https://github.com/microsoft/typescript"),
    ("kubernetes/kubernetes", "https://github.com/kubernetes/kubernetes"),
    ("apache/spark", "https://github.com/apache/spark"),
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
    default_idx = options.index(current_selected) if current_selected in options else 0

    if current_selected in options:
        st.session_state["sidebar_repo_selectbox"] = current_selected

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

    analyze_button = st.sidebar.button(
        "🚀 Analyze Repository", key="analyze_repository", type="primary"
    )

    # ── Quick Examples ─────────────────────────────────────────────────────────
    st.sidebar.markdown(
        "<h4 class='sidebar-section-header'>⚡ Quick Examples</h4>",
        unsafe_allow_html=True,
    )

    clicked_example_url = None
    cols = st.sidebar.columns(2)
    for idx, (name, url) in enumerate(_QUICK_EXAMPLES):
        col = cols[idx % 2]
        if col.button(
            f"⬡ {name}",
            key=f"btn_example_{idx}",
            use_container_width=True,
            help=f"Analyze {name}",
        ):
            clicked_example_url = url

    if clicked_example_url:
        repository_url = clicked_example_url
        analyze_button = True
        st.session_state["repository_url_input"] = clicked_example_url

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
