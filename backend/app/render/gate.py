"""
Numeric Traceability Gate Interface Contract — Master Spec §10.7, R4.
Provides verify_numeric_traceability returning GateReport which supports:
- Dict access: report.get("valid"), report.get("untraceable")
- Attribute access: report.valid, report.untraceable
- Tuple unpacking: is_valid, untraceable = verify_numeric_traceability(...)
- Flexible arg order: (block_state, docx_bytes) or (docx_bytes, block_state)
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from app.compute.traceability import check_traceability, TraceabilityResult


class GateReport(dict):
    """Result object for verify_numeric_traceability supporting dict, attr, and tuple unpacking."""

    def __init__(self, valid: bool, untraceable: List[str]):
        super().__init__(
            valid=valid,
            passed=valid,
            untraceable=untraceable,
            untraced_tokens=untraceable,
        )
        self.valid = valid
        self.passed = valid
        self.untraceable = untraceable
        self.untraced_tokens = untraceable

    def __iter__(self):
        return iter((self.valid, self.untraceable))


def verify_numeric_traceability(arg1: Any, arg2: Any) -> GateReport:
    """
    Verifies that all numeric tokens in the rendered docx_bytes trace back to
    user-supplied or confirmed values in block_state.
    Accepts (block_state, docx_bytes) or (docx_bytes, block_state).
    """
    if isinstance(arg1, (bytes, bytearray)):
        docx_bytes = bytes(arg1)
        block_state = arg2
    else:
        block_state = arg1
        docx_bytes = bytes(arg2)

    result: TraceabilityResult = check_traceability(block_state, docx_bytes)
    return GateReport(valid=result.passed, untraceable=result.untraceable)

