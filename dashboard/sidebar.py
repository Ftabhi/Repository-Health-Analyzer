"""Sidebar controls for the Streamlit dashboard."""

from typing import List, Tuple

import streamlit as st
import streamlit.components.v1 as components

_QUICK_EXAMPLES = [
    ("microsoft/vscode", "https://github.com/microsoft/vscode"),
    ("facebook/react", "https://github.com/facebook/react"),
    ("torvalds/linux", "https://github.com/torvalds/linux"),
    ("streamlit/streamlit", "https://github.com/streamlit/streamlit"),
    ("openai/openai-python", "https://github.com/openai/openai-python"),
    ("fastapi/fastapi", "https://github.com/fastapi/fastapi"),
    ("pallets/flask", "https://github.com/pallets/flask"),
    ("django/django", "https://github.com/django/django"),
    ("tensorflow/tensorflow", "https://github.com/tensorflow/tensorflow"),
    ("pytorch/pytorch", "https://github.com/pytorch/pytorch"),
]


def render_clipboard_quick_examples(examples: List[Tuple[str, str]]) -> None:
    """Render an isolated custom Streamlit component for clipboard copying of example URLs."""
    rows_html = []
    for name, url in examples:
        rows_html.append(f"""
        <div class="row">
            <span class="repo-name" title="{url}">{name}</span>
            <button class="copy-btn" onclick="copyUrl('{url}', this)" title="Copy {url}">📋</button>
        </div>
        """)

    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                background-color: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                color: #c9d1d9;
                padding: 0 2px;
            }}
            .container {{
                display: flex;
                flex-direction: column;
                gap: 6px;
            }}
            .row {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: rgba(22, 27, 34, 0.7);
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                transition: all 0.2s ease;
            }}
            .row:hover {{
                border-color: #58a6ff;
                background: rgba(33, 38, 45, 0.9);
            }}
            .repo-name {{
                font-size: 0.82rem;
                font-weight: 500;
                color: #c9d1d9;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .copy-btn {{
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 0.9rem;
                cursor: pointer;
                padding: 2px 6px;
                border-radius: 4px;
                transition: all 0.2s ease;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }}
            .copy-btn:hover {{
                color: #58a6ff;
                background: rgba(88, 166, 255, 0.12);
                transform: scale(1.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {"".join(rows_html)}
        </div>
        <script>
            function copyUrl(url, btn) {{
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(url).then(function() {{
                        showFeedback(btn);
                    }}).catch(function() {{
                        fallbackCopy(url, btn);
                    }});
                }} else {{
                    fallbackCopy(url, btn);
                }}
            }}
            function fallbackCopy(url, btn) {{
                var ta = document.createElement("textarea");
                ta.value = url;
                ta.style.position = "fixed";
                ta.style.left = "-9999px";
                document.body.appendChild(ta);
                ta.select();
                try {{
                    document.execCommand("copy");
                    showFeedback(btn);
                }} catch(e) {{}}
                document.body.removeChild(ta);
            }}
            function showFeedback(btn) {{
                var orig = btn.innerText;
                btn.innerText = "✓";
                btn.style.color = "#3fb950";
                setTimeout(function() {{
                    btn.innerText = orig;
                    btn.style.color = "";
                }}, 1500);
            }}
        </script>
    </body>
    </html>
    """

    height = len(examples) * 34 + 8
    components.html(component_html, height=height, scrolling=False)


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

    with st.sidebar:
        render_clipboard_quick_examples(_QUICK_EXAMPLES)

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
