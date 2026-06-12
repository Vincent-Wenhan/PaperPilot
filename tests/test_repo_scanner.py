"""Tests for repository scanner."""
from __future__ import annotations

import os
import unittest
import tempfile
from pathlib import Path

from tools.repo_scanner import scan_repo, scan_repo_detailed


class TestRepoScanner(unittest.TestCase):
    """Test repository scanning logic."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create sample repo files
        (self.root / "README.md").write_text("# Test Repo")
        (self.root / "requirements.txt").write_text("torch>=2.0")
        (self.root / "train.py").write_text("def main(): pass")
        (self.root / "config.yaml").write_text("data: test")
        (self.root / "notebooks").mkdir()
        (self.root / "notebooks" / "demo.ipynb").write_text("{}")
        # A file that should be skipped
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "cache.py").write_text("")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scanner_finds_important_files(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("README.md", result["important_files"])
        self.assertIn("requirements.txt", result["important_files"])

    def test_scanner_detects_entrypoints(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("train.py", result["possible_entrypoints"])

    def test_scanner_detects_descriptive_entrypoint_names(self) -> None:
        (self.root / "train_lpwm.py").write_text("def main(): pass")
        (self.root / "generate_video_prediction.py").write_text("def main(): pass")
        result = scan_repo(str(self.root))
        self.assertIn("train_lpwm.py", result["possible_entrypoints"])
        self.assertIn("generate_video_prediction.py", result["possible_entrypoints"])

    def test_scanner_skips_pycache(self) -> None:
        result = scan_repo(str(self.root))
        all_files = result["important_files"]
        self.assertNotIn("__pycache__/cache.py", all_files)

    def test_scanner_detects_config_files(self) -> None:
        result = scan_repo(str(self.root))
        self.assertTrue(
            any("config.yaml" in f for f in result["config_files"]),
        )

    def test_scanner_detects_important_directories(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("notebooks", result["important_directories"])

    def test_scanner_extracts_evidence_backed_resource_links(self) -> None:
        (self.root / "README.md").write_text(
            "# Test Repo\nDownload the dataset from https://example.com/data.zip"
        )
        result = scan_repo(str(self.root))

        self.assertEqual(len(result["resource_links"]), 1)
        self.assertEqual(result["resource_links"][0]["url"], "https://example.com/data.zip")
        self.assertEqual(result["resource_links"][0]["source"], "repository README")

    def test_scanner_extracts_resource_links_from_docs(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs" / "checkpoints.md").write_text(
            "Download pretrained weights from https://example.com/model.ckpt"
        )
        result = scan_repo(str(self.root))

        self.assertEqual(len(result["resource_links"]), 1)
        self.assertEqual(result["resource_links"][0]["url"], "https://example.com/model.ckpt")
        self.assertEqual(
            result["resource_links"][0]["source"],
            "repository docs/checkpoints.md",
        )

    def test_scanner_raises_on_nonexistent_dir(self) -> None:
        with self.assertRaises(NotADirectoryError):
            scan_repo("/nonexistent/path/12345")


class TestRepoScannerDetailed(unittest.TestCase):
    """Test structured evidence scanning."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "train.py").write_text("import torch\nimport argparse\ndef main(): pass")
        (self.root / "inference.py").write_text("from torch import nn\ndef predict(): pass")
        (self.root / "README.md").write_text("# Repo\nUses ImageNet dataset")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detects_pytorch_framework(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertEqual(result["detected_framework"], "pytorch")

    def test_detects_argparse_config(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertIn("argparse", result["config_systems"])

    def test_detects_training_and_inference_code(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertTrue(result["has_training_code"])
        self.assertTrue(result["has_inference_code"])

    def test_detects_cuda_risk_signal(self) -> None:
        os.makedirs(self.root / "cuda", exist_ok=True)
        (self.root / "cuda" / "custom_kernel.cu").write_text("__global__ void kernel() {}")
        result = scan_repo_detailed(str(self.root))
        risk_signals = result["risk_signals"]
        self.assertIn("cuda_extension", risk_signals)

    def test_detects_no_checkpoint_risk(self) -> None:
        temp_dir2 = tempfile.TemporaryDirectory()
        root2 = Path(temp_dir2.name)
        (root2 / "train.py").write_text("import torch")
        (root2 / "README.md").write_text("# A Simple Repo\nThis is a demo project with basic setup.")
        result = scan_repo_detailed(str(root2))
        self.assertIn("no_checkpoint_link", result["risk_signals"])
        temp_dir2.cleanup()

    def test_repo_name_from_path(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertEqual(result["repo_name"], self.root.name)

    def test_detects_unknown_framework(self) -> None:
        temp_dir3 = tempfile.TemporaryDirectory()
        root3 = Path(temp_dir3.name)
        (root3 / "main.py").write_text("print('hello')")
        result = scan_repo_detailed(str(root3))
        self.assertEqual(result["detected_framework"], "unknown")
        temp_dir3.cleanup()

    def test_includes_notes(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertTrue(len(result["notes"]) > 0)
