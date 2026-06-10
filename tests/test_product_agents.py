from __future__ import annotations

import unittest

from agents import (
    FrontendBuilderAgent,
    ProductDesignerAgent,
    ProductOpportunityAgent,
    ProductTestAgent,
    TechAdapterAgent,
)
from tools.llm_client import LLMClient


class ProductAgentTests(unittest.TestCase):
    def test_product_agents_load_prompts_and_run_in_mock_mode(self) -> None:
        cases = [
            (
                ProductOpportunityAgent,
                {
                    "paper_info": "paper",
                    "method_info": "method",
                    "repo_info": "repo",
                    "target_user": "student",
                    "product_goal": "demo",
                },
            ),
            (
                ProductDesignerAgent,
                {
                    "opportunities": "ideas",
                    "paper_info": "paper",
                    "method_info": "method",
                    "repo_info": "repo",
                },
            ),
            (
                TechAdapterAgent,
                {
                    "repo_info": "repo",
                    "repo_path": "/tmp/repo",
                    "product_spec": "spec",
                    "template_type": "file",
                },
            ),
            (
                FrontendBuilderAgent,
                {
                    "product_spec": "spec",
                    "template_type": "file",
                    "adapter_plan": "adapter",
                },
            ),
            (
                ProductTestAgent,
                {
                    "generated_product_dir": "generated_product",
                    "template_type": "file",
                    "files": ["app.py"],
                },
            ),
        ]
        client = LLMClient(mock_mode=True)
        for agent_type, input_data in cases:
            with self.subTest(agent_type=agent_type.__name__):
                agent = agent_type(client)
                self.assertTrue(agent.system_prompt)
                self.assertTrue(agent.prompt_path.is_file())
                output = agent.run(input_data)
                self.assertIn("PaperPilot Mock Result", output)


if __name__ == "__main__":
    unittest.main()
