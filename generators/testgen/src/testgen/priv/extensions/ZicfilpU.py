##################################
# priv/extensions/ZicfilpU.py
#
# Zicfilp U-mode WITHOUT S-mode test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp U-mode test generator for a part without S-mode: menvcfg.LPE and mstatus.MPELP."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    COVERGROUP_U_NS,
    both_xlens_bare,
    emit_mode,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ZicfilpU",
    required_extensions=["Zicfilp", "Zicsr", "U"],
    march_extensions=["Zca"],
)
def make_zicfilp_u(td: TestData) -> list[TestChunk]:
    """Generate U-mode (No S-mode) tests. Single chunk (bare)."""
    test_chunks: list[TestChunk] = []

    def build_u(xlen: int) -> list[str]:
        # LPAD faults are reachable on a real M+U part, so the trampolines live in
        # .text.rvtest and mode-entry code must not fall through into them.
        return emit_mode(
            td,
            "umode_nos",
            COVERGROUP_U_NS,
            xlen,
            "bare",
            trampoline_section=".text.rvtest",
            skip_trampoline_fallthrough=True,
        )

    tc = td.begin_test_chunk(split_name="U_NoS")
    tc.code.extend(both_xlens_bare(build_u))
    test_chunks.append(td.end_test_chunk())

    return test_chunks
