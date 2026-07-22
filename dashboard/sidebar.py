"""Sidebar controls for the Streamlit dashboard."""

from typing import List, Tuple

import streamlit as st

_QUICK_EXAMPLES = [
    "https://github.com/microsoft/vscode",
    "https://github.com/facebook/react",
    "https://github.com/torvalds/linux",
    "https://github.com/streamlit/streamlit",
    "https://github.com/openai/openai-python",
    "https://github.com/pallets/flask",
    "https://github.com/fastapi/fastapi",
    "https://github.com/django/django",
    "https://github.com/tensorflow/tensorflow",
    "https://github.com/pytorch/pytorch",
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

    rows_html = """
    <script>
    if (typeof window.copyRepoUrl === 'undefined') {
        window.copyRepoUrl = function(btn, text) {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(function() {
                    showCopiedStatus(btn);
                }).catch(function() {
                    fallbackCopyUrl(btn, text);
                });
            } else {
                fallbackCopyUrl(btn, text);
            }
        };
        window.fallbackCopyUrl = function(btn, text) {
            var dummy = document.createElement("textarea");
            document.body.appendChild(dummy);
            dummy.value = text;
            dummy.select();
            document.execCommand("copy");
            document.body.removeChild(dummy);
            showCopiedStatus(btn);
        };
        window.showCopiedStatus = function(btn) {
            var origText = btn.innerHTML;
            btn.innerHTML = "✓ Copied!";
            btn.classList.add("copied");
            setTimeout(function() {
                btn.innerHTML = origText;
                btn.classList.remove("copied");
            }, 1500);
        };
    }
    </script>
    <div class="example-rows-container">
    """

    for url in _QUICK_EXAMPLES:
        rows_html += f"""
        <div class="example-row">
            <span class="example-row-url" title="{url}">📋 {url}</span>
            <button class="copy-btn" onclick="copyRepoUrl(this, '{url}')">📄 Copy</button>
        </div>
        """

    rows_html += "</div>"
    st.sidebar.markdown(rows_html, unsafe_allow_html=True)

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
