##################################
# priv/extensions/ZicfilpS.py
#
# Zicfilp S-mode test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp S-mode privileged extension test generator.

Tests menvcfg.LPE and sstatus.SPELP across satp modes.

Covergroup: Zicfilp_s_cg
"""

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    COVERGROUP_S,
    MODE_GUARDS,
    MODES,
    both_xlens,
    emit_mode,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ZicfilpS",
    required_extensions=["Zicfilp", "Zicsr", "S"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zca"],
    extra_defines=["#define BOOT_TO_MMODE", "#define TRAP_SIGUPD_COUNT 40000"],
)
def make_zicfilp_s(td: TestData) -> list[TestChunk]:
    """Generate S-mode tests. One chunk per SATP mode."""
    test_chunks: list[TestChunk] = []

    for satp_mode in MODES:
        guard = MODE_GUARDS[satp_mode]

        def build_s(xlen: int, mode: str = satp_mode) -> list[str]:
            # trampoline_section=".text.rvtest": S-mode's LPAD exception is
            # reachable (menvcfg.LPE gates it directly, no cross-CSR
            # mismatch like the no-S U-mode case), so a real fault can land
            # here and needs to be recorded rather than treated as
            # unrecognized.
            #
            # skip_trampoline_fallthrough=True: without it, mode-entry code
            # falls straight through into _tgt_lpad_zero's `c.jr x7` with x7
            # uncontrolled, which lands back on an earlier ecall and loops
            # forever -- the same bug fixed for ZicfilpUS, confirmed here
            # too (this suite overflows TRAP_SIGUPD_COUNT without it).
            return emit_mode(
                td,
                "smode",
                COVERGROUP_S,
                xlen,
                mode,
                trampoline_section=".text.rvtest",
                skip_trampoline_fallthrough=True,
            )

        tc = td.begin_test_chunk(split_name=f"S_{satp_mode}")

        if guard:
            tc.code.append(f"#ifdef {guard}")

        tc.code.extend(both_xlens(build_s))

        if guard:
            tc.code.append(f"#endif // {guard}")

        test_chunks.append(td.end_test_chunk())

    return test_chunks
