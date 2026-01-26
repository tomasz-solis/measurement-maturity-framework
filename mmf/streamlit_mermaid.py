# mmf/streamlit_mermaid.py
from __future__ import annotations

import html

import streamlit.components.v1 as components


def render_mermaid(mermaid_code: str, *, height: int = 760) -> None:
    """
    Render Mermaid as an actual diagram (not a code block).

    - Deterministic
    - No external Python deps
    - Uses Mermaid via CDN
    """
    code = html.escape(mermaid_code)

    html_payload = f"""
    <div class="mmf-mermaid">
      <pre class="mermaid">{code}</pre>
    </div>

    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{
        startOnLoad: true,
        theme: "neutral",
        securityLevel: "loose",
        flowchart: {{
          curve: "basis",
          htmlLabels: true
        }}
      }});
    </script>
    """

    components.html(html_payload, height=height, scrolling=True)
