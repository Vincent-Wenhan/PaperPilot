from __future__ import annotations

import unittest

from runtime.tool_executor import ToolExecutor
from runtime.tool_registry import ToolRegistry, build_default_registry
from schemas.tool_schema import ToolCall, ToolSpec


class ToolRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = 0

        def sample(value: int) -> dict[str, int]:
            self.calls += 1
            return {"value": value * 2}

        self.sample = sample

    def test_registry_rejects_duplicates_and_unknown_tools(self) -> None:
        registry = ToolRegistry()
        spec = ToolSpec(
            name="sample",
            description="Double a value.",
            input_schema={"value": "integer"},
            output_schema={"value": "integer"},
            safety_level="safe",
            allowed_agents=["agent-a"],
        )
        registry.register(spec, self.sample)
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(spec, self.sample)

        result = ToolExecutor(registry).run(
            ToolCall(
                tool_name="missing",
                arguments={},
                reason="test",
                requested_by="agent-a",
            )
        )
        self.assertFalse(result.success)
        self.assertIn("Unknown tool", result.error)

    def test_executor_enforces_agent_and_safety_level(self) -> None:
        registry = ToolRegistry()
        for name, level in (
            ("safe_sample", "safe"),
            ("review_sample", "review"),
            ("blocked_sample", "blocked"),
        ):
            registry.register(
                ToolSpec(
                    name=name,
                    description="Test tool.",
                    input_schema={"value": "integer"},
                    output_schema={"value": "integer"},
                    safety_level=level,
                    allowed_agents=["agent-a"],
                ),
                self.sample,
            )
        executor = ToolExecutor(registry)

        unauthorized = executor.run(
            ToolCall(
                tool_name="safe_sample",
                arguments={"value": 2},
                reason="test",
                requested_by="agent-b",
            )
        )
        self.assertFalse(unauthorized.success)
        self.assertEqual(self.calls, 0)

        review_denied = executor.run(
            ToolCall(
                tool_name="review_sample",
                arguments={"value": 2},
                reason="test",
                requested_by="agent-a",
            )
        )
        self.assertFalse(review_denied.success)
        self.assertEqual(self.calls, 0)

        blocked = executor.run(
            ToolCall(
                tool_name="blocked_sample",
                arguments={"value": 2},
                reason="test",
                requested_by="agent-a",
            ),
            allow_safety_levels={"blocked"},
        )
        self.assertFalse(blocked.success)
        self.assertEqual(self.calls, 0)

        allowed = executor.run(
            ToolCall(
                tool_name="review_sample",
                arguments={"value": 3},
                reason="test",
                requested_by="agent-a",
            ),
            allow_safety_levels={"safe", "review"},
        )
        self.assertTrue(allowed.success)
        self.assertEqual(allowed.output, {"value": 6})
        self.assertGreaterEqual(allowed.elapsed_seconds, 0)

    def test_executor_normalizes_argument_errors(self) -> None:
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                name="sample",
                description="Test tool.",
                input_schema={"value": "integer"},
                output_schema={"value": "integer"},
                safety_level="safe",
                allowed_agents=["agent-a"],
            ),
            self.sample,
        )
        result = ToolExecutor(registry).run(
            ToolCall(
                tool_name="sample",
                arguments={"wrong": 1},
                reason="test",
                requested_by="agent-a",
            )
        )
        self.assertFalse(result.success)
        self.assertIn("arguments", result.error.lower())

    def test_default_registry_exposes_only_implemented_tools(self) -> None:
        registry = build_default_registry()
        names = {spec.name for spec in registry.list_specs()}
        self.assertIn("read_file", names)
        self.assertIn("code_search", names)
        self.assertIn("python_ast_summary", names)
        self.assertIn("pytest_collect", names)
        self.assertIn("parse_requirements", names)
        self.assertNotIn("safe_write_file", names)


if __name__ == "__main__":
    unittest.main()
