"""Product prototype generation utilities for PaperPilot."""

from productize.product_scaffold import scaffold_product
from productize.product_templates import select_product_template
from productize.product_tester import inspect_generated_product

__all__ = [
    "inspect_generated_product",
    "scaffold_product",
    "select_product_template",
]
