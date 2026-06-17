from __future__ import annotations

import unittest

from graphs.reproduce_graph import (
    ReproduceGraphDependencies,
    build_reproduce_graph,
)
from schemas.code_review_schema import CodeReview
from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)
from schemas.runner_schema import CommandPlan


def _accept_review(state: dict[str, object]) -> CodeReview:
    return CodeReview(overall_score=5.0, verdict="accept")


def _revise_noop(
    state: dict[str, object],
    suggestions: list[str],
) -> ImplementationBundle:
    return ImplementationBundle()


def _sandbox_pass(state: dict[str, object]) -> dict[str, object]:
    return {"passed": True, "results": [], "error": None}


class ReproduceBranchTests(unittest.TestCase):
    def test_parallel_branches_join_with_paper_and_repo_evidence(self) -> None:
        received: dict[str, object] = {}

        def understand_repository(
            research: dict[str, object],
            repo_scan: dict[str, object],
            github_url: str,
        ) -> RepositoryUnderstanding:
            received.update(
                research=research,
                repo_scan=repo_scan,
                github_url=github_url,
            )
            return RepositoryUnderstanding(repo_source="github")

        graph = build_reproduce_graph(
            ReproduceGraphDependencies(
                parse_paper=lambda path: "paper text",
                understand_research=lambda text, idea: PaperUnderstanding(
                    title="Paper", method_summary=text
                ),
                prepare_repository=lambda url: {"repo_path": "/tmp/repo"},
                understand_repository=understand_repository,
                plan_reproduction=lambda research, repository, inputs: ReproductionPlan(),
                generate_implementation=lambda state: ImplementationBundle(),
                review_code=_accept_review,
                revise_code=_revise_noop,
                diagnose_execution=lambda plan, results: ExecutionDiagnosis(),
                sandbox_verify=_sandbox_pass,
                second_review_code=_accept_review,
                build_outputs=lambda state: {"saved": True},
            )
        )
        state = graph.invoke(
            {
                "pdf_path": "paper.pdf",
                "github_url": "https://github.com/example/repo",
                "graph_trace": [],
                "errors": [],
                "command_results": [],
            }
        )

        self.assertEqual(received["research"]["title"], "Paper")
        self.assertEqual(received["repo_scan"]["repo_path"], "/tmp/repo")
        trace = state["graph_trace"]
        self.assertLess(
            trace.index("research_understanding"),
            trace.index("repository_understanding"),
        )
        self.assertLess(
            trace.index("prepare_repository"),
            trace.index("repository_understanding"),
        )

    def test_paper_only_repository_fallback_reaches_planning(self) -> None:
        graph = build_reproduce_graph(
            ReproduceGraphDependencies(
                parse_paper=lambda path: "paper text",
                understand_research=lambda text, idea: PaperUnderstanding(title="Paper"),
                prepare_repository=lambda url: {},
                understand_repository=lambda research, repo, url: RepositoryUnderstanding(
                    repo_source="paper-only"
                ),
                plan_reproduction=lambda research, repository, inputs: ReproductionPlan(
                    implementation_strategy=repository["repo_source"]
                ),
                generate_implementation=lambda state: ImplementationBundle(),
                review_code=_accept_review,
                revise_code=_revise_noop,
                diagnose_execution=lambda plan, results: ExecutionDiagnosis(),
                sandbox_verify=_sandbox_pass,
                second_review_code=_accept_review,
                build_outputs=lambda state: {},
            )
        )
        state = graph.invoke(
            {
                "pdf_path": "paper.pdf",
                "github_url": "",
                "graph_trace": [],
                "errors": [],
                "command_results": [],
            }
        )
        self.assertEqual(
            state["reproduction_plan"]["implementation_strategy"],
            "paper-only",
        )


class ReproduceRiskRoutingTests(unittest.TestCase):
    def _run(self, commands: list[CommandPlan]) -> dict[str, object]:
        graph = build_reproduce_graph(
            ReproduceGraphDependencies(
                parse_paper=lambda path: "paper",
                understand_research=lambda text, idea: PaperUnderstanding(),
                prepare_repository=lambda url: {"repo_path": "/tmp/repo"},
                understand_repository=lambda research, repo, url: RepositoryUnderstanding(
                    repo_path="/tmp/repo"
                ),
                plan_reproduction=lambda research, repository, inputs: ReproductionPlan(
                    command_plans=commands
                ),
                generate_implementation=lambda state: ImplementationBundle(),
                review_code=_accept_review,
                revise_code=_revise_noop,
                diagnose_execution=lambda plan, results: ExecutionDiagnosis(
                    feasibility=(
                        "planned_not_executed"
                        if all(not item["executed"] for item in results)
                        else "unexpected_execution"
                    )
                ),
                sandbox_verify=_sandbox_pass,
                second_review_code=_accept_review,
                build_outputs=lambda state: {},
            )
        )
        return graph.invoke(
            {
                "pdf_path": "paper.pdf",
                "github_url": "",
                "graph_trace": [],
                "errors": [],
                "command_results": [],
            }
        )

    def test_low_risk_commands_route_safe_without_execution(self) -> None:
        state = self._run(
            [CommandPlan(command="python --version", purpose="Check Python")]
        )
        self.assertEqual(state["command_route"], "safe")
        self.assertTrue(all(not item["executed"] for item in state["command_results"]))
        self.assertEqual(
            state["execution_diagnosis"]["feasibility"],
            "planned_not_executed",
        )

    def test_medium_or_high_commands_route_review_with_metadata(self) -> None:
        state = self._run(
            [CommandPlan(command="pip install torch", purpose="Install dependencies")]
        )
        self.assertEqual(state["command_route"], "review")
        pending = state["pending_human_review"]
        self.assertEqual(pending["command"], "pip install torch")
        self.assertEqual(pending["purpose"], "Install dependencies")
        self.assertEqual(pending["risk_level"], "medium")
        self.assertEqual(pending["cwd"], "/tmp/repo")

    def test_blocked_command_dominates_route(self) -> None:
        state = self._run(
            [
                CommandPlan(command="python --version", purpose="Check Python"),
                CommandPlan(command="sudo rm -rf /", purpose="Unsafe"),
            ]
        )
        self.assertEqual(state["command_route"], "blocked")
        self.assertEqual(
            state["pending_human_review"]["risk_level"],
            "blocked",
        )
        self.assertTrue(all(not item["executed"] for item in state["command_results"]))


if __name__ == "__main__":
    unittest.main()
