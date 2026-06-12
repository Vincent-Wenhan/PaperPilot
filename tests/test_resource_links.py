"""Tests for deterministic evidence-backed resource link extraction."""

from __future__ import annotations

import unittest

from tools.resource_links import extract_resource_links


class ResourceLinkTests(unittest.TestCase):
    def test_extracts_https_dataset_link_with_nearby_evidence(self) -> None:
        links = extract_resource_links(
            "[Page 7] Download the training dataset from "
            "https://example.com/releases/data.zip before training.",
            "paper PDF",
        )

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, "https://example.com/releases/data.zip")
        self.assertEqual(links[0].resource_type, "dataset")
        self.assertEqual(links[0].destination, "data/data.zip")
        self.assertIn("[Page 7]", links[0].evidence)

    def test_extracts_checkpoint_link_into_checkpoint_directory(self) -> None:
        links = extract_resource_links(
            "Pretrained weights: https://example.com/models/lpwm.ckpt",
            "repository README",
        )

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].resource_type, "checkpoint")
        self.assertEqual(links[0].destination, "checkpoints/lpwm.ckpt")

    def test_ignores_unrelated_or_insecure_links(self) -> None:
        links = extract_resource_links(
            "Project page: https://example.com/paper. "
            "Download dataset from http://example.com/data.zip.",
            "paper PDF",
        )

        self.assertEqual(links, [])


if __name__ == "__main__":
    unittest.main()
