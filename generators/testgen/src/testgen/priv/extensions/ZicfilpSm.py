##################################
# priv/extensions/ZicfilpM.py
#
# Zicfilp M-mode (Sm) privileged extension test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp M-mode (Sm) privileged extension test generator.

Tests mseccfg.MLPE and mstatus.MPELP.

Covergroup: Zicfilp_Sm_cg
"""

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    COVERGROUP_M,
    both_xlens_bare,
    emit_mode,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ZicfilpSm",
    required_extensions=["Zicfilp", "Zicsr"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zca"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilp_m(td: TestData) -> list[TestChunk]:
    """Generate M-mode (Sm) tests. Single chunk (bare metal)."""
    test_chunks: list[TestChunk] = []

    def build_sm(xlen: int) -> list[str]:
        # M-mode always runs bare, no satp modes.
        # trampoline_section=".text.rvtest": matches the other modes for
        # consistency, though M-mode's own _build_faults deliberate-mismatch
        # testcases are skipped entirely (see the comment there -- tripping
        # LPE=1 in M-mode recurses into the shared M-mode dispatcher's own
        # unguarded indirect jump), so no real fault currently lands on
        # these trampolines here either way.
        #
        # skip_trampoline_fallthrough=True: without it, mode-entry code
        # falls straight through into _tgt_lpad_zero's `c.jr x7` with x7
        # uncontrolled, landing back on an earlier ecall and looping
        # forever -- the same bug fixed for ZicfilpUS, independently
        # confirmed here too (Sail's own watchdog reports "possible trap
        # loop detected" for this suite).
        return emit_mode(
            td,
            "mmode",
            COVERGROUP_M,
            xlen,
            "bare",
            trampoline_section=".text.rvtest",
            skip_trampoline_fallthrough=True,
        )

    tc = td.begin_test_chunk(split_name="Sm")
    tc.code.extend(both_xlens_bare(build_sm))
    test_chunks.append(td.end_test_chunk())

    return test_chunks
