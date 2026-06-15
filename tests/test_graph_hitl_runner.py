"""Tests for LangGraph sync HITL helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pipeline.graph_hitl_runner import (
    REPRODUCE_HITL_INTERRUPT_AFTER,
    graph_is_interrupted,
    render_interrupt_content,
)


class GraphHitlRunnerTests(unittest.TestCase):
    def test_interrupt_nodes_cover_research_and_planner(self) -> None:
        self.assertIn("research_understanding", REPRODUCE_HITL_INTERRUPT_AFTER)
        self.assertIn("reproduction_planner", REPRODUCE_HITL_INTERRUPT_AFTER)

    def test_render_interrupt_content_for_research(self) -> None:
        content = render_interrupt_content(
            {"paper_info": "Summary", "method_info": "Method"},
            "research_understanding",
        )
        self.assertIn("Summary", content)
        self.assertIn("Method", content)

    def test_graph_is_interrupted_reads_snapshot(self) -> None:
        graph = MagicMock()
        graph.get_state.return_value = MagicMock(next=("reproduction_planner",))
        self.assertTrue(graph_is_interrupted(graph, "thread-1"))


if __name__ == "__main__":
    unittest.main()
