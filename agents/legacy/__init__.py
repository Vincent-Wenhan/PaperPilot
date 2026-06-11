"""Legacy fragmented agents kept for migration reference only.

The active pipelines do not import or call these classes.
"""

from agents.legacy.code_agent import CodeAgent
from agents.legacy.debug_agent import DebugAgent
from agents.legacy.env_agent import EnvironmentAgent
from agents.legacy.experiment_agent import ExperimentPlannerAgent
from agents.legacy.frontend_builder_agent import FrontendBuilderAgent
from agents.legacy.method_extractor_agent import MethodExtractorAgent
from agents.legacy.paper_reader_agent import PaperReaderAgent
from agents.legacy.product_designer_agent import ProductDesignerAgent
from agents.legacy.product_opportunity_agent import ProductOpportunityAgent
from agents.legacy.product_test_agent import ProductTestAgent
from agents.legacy.repo_analyzer_agent import RepoAnalyzerAgent
from agents.legacy.repo_clone_agent import RepoCloneAgent
from agents.legacy.report_agent import ReportAgent
from agents.legacy.runner_agent import RunnerAgent
from agents.legacy.tech_adapter_agent import TechAdapterAgent

__all__ = [
    "CodeAgent",
    "DebugAgent",
    "EnvironmentAgent",
    "ExperimentPlannerAgent",
    "FrontendBuilderAgent",
    "MethodExtractorAgent",
    "PaperReaderAgent",
    "ProductDesignerAgent",
    "ProductOpportunityAgent",
    "ProductTestAgent",
    "RepoAnalyzerAgent",
    "RepoCloneAgent",
    "ReportAgent",
    "RunnerAgent",
    "TechAdapterAgent",
]
