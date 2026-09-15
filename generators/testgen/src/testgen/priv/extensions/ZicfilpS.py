##################################
# priv/extensions/ZicfilpS.py
#
# Zicfilp S-mode test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp S-mode privileged extension test generator.

S-mode tests use menvcfg.LPE and sstatus.SPELP. U-mode tests run on the same
S-capable part, controlled by senvcfg.LPE and sstatus.SPELP.

Covergroups: Zicfilp_s_cg (S-mode), Zicfilpsu_cg (U-mode)
"""

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    COVERGROUP_S,
    COVERGROUP_U_S,
    MODE_GUARDS,
    MODES,
    both_xlens,
    emit_mode,
)
from testgen.priv.registry import add_priv_test_generator


def _emit_chunk(td: TestData, mode: str, covergroup: str, split_prefix: str, satp_mode: str) -> TestChunk:
    guard = MODE_GUARDS[satp_mode]

    def build(xlen: int) -> list[str]:
        # trampoline_section=".text.rvtest": the LPAD exception is reachable in
        # both modes, so a real fault can land on the trampolines and must be
        # recorded rather than treated as unrecognized.
        #
        # skip_trampoline_fallthrough=True: without it, mode-entry code falls
        # straight through into _tgt_lpad_zero's `c.jr x7` with x7
        # uncontrolled, landing back on the mode-switch ecall and looping
        # until TRAP_SIGUPD_COUNT overflows.
        return emit_mode(
            td,
            mode,
            covergroup,
            xlen,
            satp_mode,
            trampoline_section=".text.rvtest",
            skip_trampoline_fallthrough=True,
        )

    tc = td.begin_test_chunk(split_name=f"{split_prefix}_{satp_mode}")
    if guard:
        tc.code.append(f"#ifdef {guard}")
    tc.code.extend(both_xlens(build))
    if guard:
        tc.code.append(f"#endif // {guard}")
    return td.end_test_chunk()


@add_priv_test_generator(
    "ZicfilpS",
    required_extensions=["Zicfilp", "Zicsr", "S", "U"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zca"],
    extra_defines=["#define BOOT_TO_MMODE", "#define TRAP_SIGUPD_COUNT 40000"],
)
def make_zicfilp_s(td: TestData) -> list[TestChunk]:
    """Generate S-mode and U-mode tests. One chunk per SATP mode for each."""
    test_chunks: list[TestChunk] = []

    for satp_mode in MODES:
        test_chunks.append(_emit_chunk(td, "smode", COVERGROUP_S, "S", satp_mode))
        test_chunks.append(_emit_chunk(td, "umode", COVERGROUP_U_S, "SU", satp_mode))

    return test_chunks
