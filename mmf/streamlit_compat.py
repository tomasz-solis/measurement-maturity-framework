"""Compatibility helpers for Streamlit API differences across versions.

The app supports a pinned Streamlit runtime from ``requirements.txt``. Full-width
layout is requested differently across versions: ``use_container_width=True`` is
the stable flag on the pinned runtime, while the ``width="stretch"`` token only
appears on much newer Streamlit. Crucially, on the pinned runtime ``width`` also
exists but is an integer (pixels), so it rejects the string ``"stretch"`` -- a
mere "does the parameter exist?" check is not enough. These helpers therefore
prefer ``use_container_width`` and only fall back to ``width="stretch"`` when
``use_container_width`` is unavailable.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional

import streamlit as st


def _supports_param(func: Callable[..., Any], name: str) -> bool:
    """Return True when a callable exposes a parameter in its signature."""
    try:
        return name in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def render_dataframe(data: Any, *, hide_index: bool = True) -> None:
    """Render a dataframe using the widest layout supported by the runtime."""
    kwargs: dict[str, Any] = {}

    if hide_index and _supports_param(st.dataframe, "hide_index"):
        kwargs["hide_index"] = True

    if _supports_param(st.dataframe, "use_container_width"):
        kwargs["use_container_width"] = True
    elif _supports_param(st.dataframe, "width"):
        kwargs["width"] = "stretch"

    st.dataframe(data, **kwargs)


def render_download_button(
    *,
    label: str,
    data: bytes,
    file_name: str,
    mime: str,
    key: Optional[str] = None,
) -> bool:
    """Render a download button with the best supported full-width option.

    Pass a unique ``key`` when the same label/data may appear more than once on a
    page; Streamlit otherwise raises StreamlitDuplicateElementId.
    """
    kwargs: dict[str, Any] = {}

    if key is not None:
        kwargs["key"] = key
    if _supports_param(st.download_button, "use_container_width"):
        kwargs["use_container_width"] = True
    elif _supports_param(st.download_button, "width"):
        kwargs["width"] = "stretch"

    return bool(
        st.download_button(
            label=label,
            data=data,
            file_name=file_name,
            mime=mime,
            **kwargs,
        )
    )
