from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from schemas.reproduction_schema import (
    GeneratedCodeFile,
    ImplementationBundle,
    ResourceLink,
)
from tools.code_writer import materialize_implementation


SAFE_DOWNLOAD_SCRIPT = '''"""Download reviewed resources."""

import argparse
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("dry run")
        return
    with urlopen("https://example.com/data.zip") as response:
        print(response.status)


if __name__ == "__main__":
    main()
'''


class CodeWriterTests(unittest.TestCase):
    def test_materializes_safe_implementation_bundle(self) -> None:
        bundle = ImplementationBundle(
            project_name="demo",
            summary="A runnable demo.",
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="Documentation",
                    content="# Demo\n",
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="Entry point",
                    content="print('ok')\n",
                ),
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = materialize_implementation(bundle, temp_dir)
            root = Path(str(result["repo_path"]))
            self.assertEqual((root / "main.py").read_text(encoding="utf-8"), "print('ok')\n")
            self.assertTrue((root / "CODE_AGENT_MANIFEST.json").is_file())

    def test_rejects_unsafe_path(self) -> None:
        bundle = ImplementationBundle(
            summary="Unsafe",
            files=[
                GeneratedCodeFile(
                    path="../outside.py",
                    purpose="Unsafe",
                    content="print('unsafe')\n",
                )
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Unsafe generated file path"):
                materialize_implementation(bundle, temp_dir)

    def test_rejects_invalid_python_syntax_before_writing(self) -> None:
        bundle = ImplementationBundle(
            summary="Invalid",
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="Invalid entry point",
                    content="def broken(\n",
                )
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "invalid syntax"):
                materialize_implementation(bundle, temp_dir)
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_materializes_reviewed_dry_run_download_script(self) -> None:
        bundle = ImplementationBundle(
            summary="Downloader",
            data_resources=[
                ResourceLink(
                    name="data.zip",
                    url="https://example.com/data.zip",
                    destination="data/data.zip",
                    evidence="README: Download dataset",
                )
            ],
            files=[
                GeneratedCodeFile(
                    path="scripts/download_data.py",
                    purpose="Download reviewed data",
                    content=SAFE_DOWNLOAD_SCRIPT,
                )
            ],
            data_download_command="python scripts/download_data.py --execute",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = materialize_implementation(bundle, temp_dir)
            root = Path(str(result["repo_path"]))

            self.assertTrue((root / "scripts" / "download_data.py").is_file())
            self.assertEqual(result["data_resources"][0]["url"], "https://example.com/data.zip")

    def test_rejects_download_script_url_not_in_data_resources(self) -> None:
        bundle = ImplementationBundle(
            summary="Downloader",
            data_resources=[
                ResourceLink(
                    url="https://example.com/approved.zip",
                    destination="data/approved.zip",
                )
            ],
            files=[
                GeneratedCodeFile(
                    path="scripts/download_data.py",
                    purpose="Download unapproved data",
                    content=SAFE_DOWNLOAD_SCRIPT,
                )
            ],
            data_download_command="python scripts/download_data.py --execute",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "URLs must exactly match"):
                materialize_implementation(bundle, temp_dir)

    def test_rejects_download_script_without_evidence_backed_resources(self) -> None:
        bundle = ImplementationBundle(
            summary="Downloader",
            files=[
                GeneratedCodeFile(
                    path="scripts/download_data.py",
                    purpose="Download unapproved data",
                    content=SAFE_DOWNLOAD_SCRIPT,
                )
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "URLs must exactly match"):
                materialize_implementation(bundle, temp_dir)

    def test_rejects_unsafe_download_behavior(self) -> None:
        unsafe_script = SAFE_DOWNLOAD_SCRIPT.replace(
            'print("dry run")',
            'eval("print(1)")',
        )
        bundle = ImplementationBundle(
            summary="Downloader",
            data_resources=[
                ResourceLink(
                    url="https://example.com/data.zip",
                    destination="data/data.zip",
                )
            ],
            files=[
                GeneratedCodeFile(
                    path="scripts/download_data.py",
                    purpose="Unsafe downloader",
                    content=unsafe_script,
                )
            ],
            data_download_command="python scripts/download_data.py --execute",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "unsafe behavior"):
                materialize_implementation(bundle, temp_dir)
