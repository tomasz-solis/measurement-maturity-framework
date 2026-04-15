"""Tests for Streamlit compatibility helpers."""

from mmf import streamlit_compat


class TestStreamlitCompat:
    """Ensure UI helpers adapt to older and newer Streamlit signatures."""

    def test_render_download_button_prefers_width_when_supported(self, monkeypatch):
        """Newer Streamlit versions should receive the width argument."""
        calls: list[dict[str, object]] = []

        def fake_download_button(
            *,
            label: str,
            data: bytes,
            file_name: str,
            mime: str,
            width: str,
        ) -> bool:
            calls.append(
                {
                    "label": label,
                    "data": data,
                    "file_name": file_name,
                    "mime": mime,
                    "width": width,
                }
            )
            return True

        monkeypatch.setattr(
            streamlit_compat.st, "download_button", fake_download_button
        )

        clicked = streamlit_compat.render_download_button(
            label="Download",
            data=b"hello",
            file_name="pack.yaml",
            mime="text/yaml",
        )

        assert clicked is True
        assert calls == [
            {
                "label": "Download",
                "data": b"hello",
                "file_name": "pack.yaml",
                "mime": "text/yaml",
                "width": "stretch",
            }
        ]

    def test_render_download_button_falls_back_to_container_width(self, monkeypatch):
        """Older runtimes should use use_container_width when width is unavailable."""
        calls: list[dict[str, object]] = []

        def fake_download_button(
            *,
            label: str,
            data: bytes,
            file_name: str,
            mime: str,
            use_container_width: bool,
        ) -> bool:
            calls.append(
                {
                    "label": label,
                    "data": data,
                    "file_name": file_name,
                    "mime": mime,
                    "use_container_width": use_container_width,
                }
            )
            return False

        monkeypatch.setattr(
            streamlit_compat.st, "download_button", fake_download_button
        )

        clicked = streamlit_compat.render_download_button(
            label="Download",
            data=b"hello",
            file_name="pack.yaml",
            mime="text/yaml",
        )

        assert clicked is False
        assert calls == [
            {
                "label": "Download",
                "data": b"hello",
                "file_name": "pack.yaml",
                "mime": "text/yaml",
                "use_container_width": True,
            }
        ]

    def test_render_dataframe_falls_back_to_container_width(self, monkeypatch):
        """Older runtimes should use use_container_width for dataframe rendering."""
        calls: list[dict[str, object]] = []

        def fake_dataframe(
            data: object, *, hide_index: bool, use_container_width: bool
        ) -> None:
            calls.append(
                {
                    "data": data,
                    "hide_index": hide_index,
                    "use_container_width": use_container_width,
                }
            )

        monkeypatch.setattr(streamlit_compat.st, "dataframe", fake_dataframe)

        streamlit_compat.render_dataframe([{"metric": "m1"}], hide_index=True)

        assert calls == [
            {
                "data": [{"metric": "m1"}],
                "hide_index": True,
                "use_container_width": True,
            }
        ]
