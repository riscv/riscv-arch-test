##################################
# priv/extensions/ZicfilpU.py
#
# Zicfilp U-mode WITHOUT S-mode test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp U-mode (no S-mode) privileged extension test generator.

Tests menvcfg.LPE and mstatus.MPELP.

Covergroup: Zicfilp_u_cg
"""

from __future__ import annotations

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
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zca"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilp_u(td: TestData) -> list[TestChunk]:
    """Generate U-mode (No S-mode) tests. Single chunk (bare)."""
    test_chunks: list[TestChunk] = []

    def build_u(xlen: int) -> list[str]:
        # umode_nos uses menvcfg + mstatus/mstatush, runs bare
        # trampoline_section=".text": this mode's LPAD exception can't
        # actually fire under the current no-S Sail config (see
        # ZicfilpCommon.py's umode_nos xLPE note), so the trampolines never
        # take a fault here. Moving them into .text.rvtest gained nothing
        # for this suite but shifted overall code layout by ~64 bytes,
        # which was enough to trip an unrelated, pre-existing fragility in
        # the shared trap handler's dispatch-table addressing (an early
        # boot-time trap reading a poisoned mepc). Keep the old placement
        # here until that's root-caused; ZicfilpUS needs .text.rvtest
        # because its exception is genuinely reachable.
        return emit_mode(td, "umode_nos", COVERGROUP_U_NS, xlen, "bare", trampoline_section=".text")

    tc = td.begin_test_chunk(split_name="U_NoS")
    tc.code.extend(both_xlens_bare(build_u))
    test_chunks.append(td.end_test_chunk())

    return test_chunks
