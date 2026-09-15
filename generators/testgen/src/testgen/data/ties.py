##################################
# data/ties.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exact-tie operand selection shared by the _ties coverpoint generators."""

from testgen.data.edges import FLOAT_EDGES

# RMM and RNE differ only on an exact tie, so the tie coverpoints sweep just those two.
TIE_FRM_MODES = ("rne", "rmm")


def _format_suffix(coverpoint: str) -> str:
    """Return the floating-point format suffix of a _ties coverpoint name."""
    for suffix in ("_D", "_H", "_BF16"):
        if coverpoint.endswith(suffix):
            return suffix
    return ""


def tie_edges_for(coverpoint: str) -> tuple[int, ...]:
    """Return the exact-tie operand table for a coverpoint's floating-point format."""
    return {
        "_D": FLOAT_EDGES.ties_double,
        "_H": FLOAT_EDGES.ties_half,
        "_BF16": FLOAT_EDGES.ties_bf16,
        "": FLOAT_EDGES.ties_single,
    }[_format_suffix(coverpoint)]


def tie_partners_for(coverpoint: str) -> tuple[int, ...]:
    """Return the tie partner operands (+-1.0) for a coverpoint's floating-point format."""
    return {
        "_D": FLOAT_EDGES.tie_partners_double,
        "_H": FLOAT_EDGES.tie_partners_half,
        "_BF16": FLOAT_EDGES.tie_partners_bf16,
        "": FLOAT_EDGES.tie_partners_single,
    }[_format_suffix(coverpoint)]
