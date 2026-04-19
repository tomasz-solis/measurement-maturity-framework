"""Tests for sidebar example discovery and rendering."""

from pathlib import Path

from mmf import sidebar


def _write_text(path: Path, text: str) -> None:
    """Write a small UTF-8 fixture file for sidebar tests."""
    path.write_text(text, encoding="utf-8")


class TestSidebarExamples:
    """Keep the sidebar focused on repo examples instead of templates."""

    def test_load_sidebar_examples_returns_known_examples_first(
        self, monkeypatch, tmp_path
    ):
        """Known example packs should lead the list in a stable, useful order."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()

        _write_text(
            examples_dir / "spreadsheet_pipeline_pack.yaml", "pack: spreadsheet"
        )
        _write_text(examples_dir / "generic_product_metric_pack.yaml", "pack: generic")
        _write_text(examples_dir / "mixed_maturity_pack.yaml", "pack: mixed")
        _write_text(examples_dir / "z_custom_pack.yaml", "pack: custom")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        _write_text(templates_dir / "metric_template.yaml", "id: template")

        monkeypatch.setattr(sidebar, "repo_root", lambda: tmp_path)

        examples = sidebar.load_sidebar_examples()

        assert [example.file_name for example in examples] == [
            "generic_product_metric_pack.yaml",
            "mixed_maturity_pack.yaml",
            "spreadsheet_pipeline_pack.yaml",
            "z_custom_pack.yaml",
        ]
        assert [example.label for example in examples[:3]] == [
            "Generic product example",
            "Mixed maturity example",
            "Spreadsheet pipeline example",
        ]

    def test_render_sidebar_examples_renders_only_example_downloads(self, monkeypatch):
        """The sidebar should render one download button per example pack."""
        examples = [
            sidebar.SidebarExample(
                label="Generic product example",
                file_name="generic_product_metric_pack.yaml",
                content=b"pack: generic",
                description="A full reference pack.",
            ),
            sidebar.SidebarExample(
                label="Mixed maturity example",
                file_name="mixed_maturity_pack.yaml",
                content=b"pack: mixed",
                description="A pack with one weaker metric.",
            ),
        ]

        subheaders: list[str] = []
        buttons: list[dict[str, object]] = []
        markdown_calls: list[str] = []

        def fake_markdown(body: str, **kwargs: object) -> None:
            """Capture sidebar markdown blocks so the copy can be asserted."""
            markdown_calls.append(body)

        monkeypatch.setattr(sidebar.st, "markdown", fake_markdown)
        monkeypatch.setattr(sidebar.st, "subheader", subheaders.append)

        def fake_download_button(
            *, label: str, data: bytes, file_name: str, mime: str
        ) -> bool:
            """Record example download button calls for inspection."""
            buttons.append(
                {
                    "label": label,
                    "data": data,
                    "file_name": file_name,
                    "mime": mime,
                }
            )
            return False

        monkeypatch.setattr(sidebar, "render_download_button", fake_download_button)

        sidebar.render_sidebar_examples(examples)

        assert subheaders == ["Example Packs"]
        assert [button["label"] for button in buttons] == [
            "Download Generic product example",
            "Download Mixed maturity example",
        ]
        assert all(button["mime"] == "text/yaml" for button in buttons)
        assert all("template" not in str(button["label"]).lower() for button in buttons)
        rendered_markup = "\n".join(markdown_calls)
        assert 'class="mmf-sidebar-note"' in rendered_markup
        assert "Download one of the repo examples" in rendered_markup
        assert 'class="mmf-sidebar-example-copy"' in rendered_markup
