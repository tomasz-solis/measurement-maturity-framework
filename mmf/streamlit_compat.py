"""Compatibility helpers for Streamlit API differences across versions.

The app currently supports a pinned Streamlit runtime from ``requirements.txt``.
Some newer keyword arguments, like ``width="stretch"``, are not available in
older versions. These helpers keep the UI code readable while selecting the
best-supported parameter set at runtime.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

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

    if _supports_param(st.dataframe, "width"):
        kwargs["width"] = "stretch"
    elif _supports_param(st.dataframe, "use_container_width"):
        kwargs["use_container_width"] = True

    st.dataframe(data, **kwargs)


def render_download_button(
    *,
    label: str,
    data: bytes,
    file_name: str,
    mime: str,
) -> bool:
    """Render a download button with the best supported full-width option."""
    kwargs: dict[str, Any] = {}

    if _supports_param(st.download_button, "width"):
        kwargs["width"] = "stretch"
    elif _supports_param(st.download_button, "use_container_width"):
        kwargs["use_container_width"] = True

    return bool(
        st.download_button(
            label=label,
            data=data,
            file_name=file_name,
            mime=mime,
            **kwargs,
        )
    )
