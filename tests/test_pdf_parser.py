"""Tests for PDF parser."""
from __future__ import annotations

import unittest

from tools.pdf_parser import parse_pdf


class TestPdfParser(unittest.TestCase):
    """Test PDF parsing error handling."""

    def test_nonexistent_file_raises_error(self) -> None:
        with self.assertRaises((FileNotFoundError, OSError)):
            parse_pdf("/nonexistent/paper.pdf")
