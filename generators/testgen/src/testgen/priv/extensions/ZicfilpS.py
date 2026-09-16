##################################
# priv/extensions/ZicfilpS.py
#
# Zicfilp S-mode test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp S-mode and U-mode test generator for an S-capable part.

S-mode uses menvcfg.LPE, U-mode senvcfg.LPE; both use sstatus.SPELP.
"""

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
        # LPAD faults are reachable here, so the trampolines live in .text.rvtest
        # and mode-entry code must not fall through into _tgt_lpad_zero.
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
    march_extensions=["Zca"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfilp_s(td: TestData) -> list[TestChunk]:
    """Generate S-mode and U-mode tests. One chunk per SATP mode for each."""
    test_chunks: list[TestChunk] = []

    for satp_mode in MODES:
        test_chunks.append(_emit_chunk(td, "smode", COVERGROUP_S, "S", satp_mode))
        test_chunks.append(_emit_chunk(td, "umode", COVERGROUP_U_S, "SU", satp_mode))

    return test_chunks
