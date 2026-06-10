"""PaperPilot agent package."""

from agents.base_agent import BaseAgent
from agents.code_agent import CodeAgent
from agents.debug_agent import DebugAgent
from agents.env_agent import EnvironmentAgent
from agents.experiment_agent import ExperimentPlannerAgent
from agents.frontend_builder_agent import FrontendBuilderAgent
from agents.method_extractor_agent import MethodExtractorAgent
from agents.paper_reader_agent import PaperReaderAgent
from agents.product_designer_agent import ProductDesignerAgent
from agents.product_evaluator_agent import ProductEvaluatorAgent
from agents.product_opportunity_agent import ProductOpportunityAgent
from agents.product_planner_agent import ProductPlannerAgent
from agents.product_test_agent import ProductTestAgent
from agents.prototype_builder_agent import PrototypeBuilderAgent
from agents.research_synthesizer_agent import ResearchSynthesizerAgent
from agents.repo_analyzer_agent import RepoAnalyzerAgent
from agents.repo_clone_agent import RepoCloneAgent
from agents.report_agent import ReportAgent
from agents.runner_agent import RunnerAgent
from agents.tech_adapter_agent import TechAdapterAgent

EnvAgent = EnvironmentAgent
ExperimentAgent = ExperimentPlannerAgent

__all__ = [
    "BaseAgent",
    "CodeAgent",
    "DebugAgent",
    "EnvAgent",
    "EnvironmentAgent",
    "ExperimentAgent",
    "ExperimentPlannerAgent",
    "FrontendBuilderAgent",
    "MethodExtractorAgent",
    "PaperReaderAgent",
    "ProductDesignerAgent",
    "ProductEvaluatorAgent",
    "ProductOpportunityAgent",
    "ProductPlannerAgent",
    "ProductTestAgent",
    "PrototypeBuilderAgent",
    "ResearchSynthesizerAgent",
    "RepoAnalyzerAgent",
    "RepoCloneAgent",
    "ReportAgent",
    "RunnerAgent",
    "TechAdapterAgent",
]
