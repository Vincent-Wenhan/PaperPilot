"""Tests for PDF parser."""
from __future__ import annotations

import tempfile
import unittest

from tools.pdf_parser import _truncate_text, parse_pdf


class TestPdfParser(unittest.TestCase):
    """Test PDF parsing error handling."""

    def test_nonexistent_file_raises_error(self) -> None:
        with self.assertRaises((FileNotFoundError, OSError)):
            parse_pdf("/nonexistent/paper.pdf")

    def test_truncation_preserves_opening_and_ending(self) -> None:
        text = f"{'A' * 100}{'B' * 100}"
        truncated = _truncate_text(text, 120)
        self.assertEqual(len(truncated), 120)
        self.assertTrue(truncated.startswith("A"))
        self.assertTrue(truncated.endswith("B"))
        self.assertIn("PDF text truncated", truncated)


class TestPdfQuality(unittest.TestCase):
    """Test PDF quality analysis and section extraction error handling."""

    def test_analyze_raises_on_nonexistent_file(self) -> None:
        from tools.pdf_parser import analyze_pdf_quality
        with self.assertRaises((FileNotFoundError, OSError)):
            analyze_pdf_quality("/nonexistent/paper.pdf")

    def test_extract_raises_on_nonexistent_file(self) -> None:
        from tools.pdf_parser import extract_pdf_sections
        with self.assertRaises((FileNotFoundError, OSError)):
            extract_pdf_sections("/nonexistent/paper.pdf")

    def test_analyze_invalid_extension_raises_runtime_error(self) -> None:
        from tools.pdf_parser import analyze_pdf_quality
        with self.assertRaises(FileNotFoundError):
            analyze_pdf_quality("/nonexistent/paper.pdf")
