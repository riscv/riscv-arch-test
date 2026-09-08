##################################
# priv/extensions/ZicfilpUS.py
#
# Zicfilp U-mode WITH S-mode implemented test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp U-mode (with S-mode) privileged extension test generator.

Tests senvcfg.LPE and sstatus.SPELP.

Covergroup: Zicfilpsu_cg
"""

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    COVERGROUP_U_S,
    MODE_GUARDS,
    MODES,
    both_xlens,
    emit_mode,
)
from testgen.priv.registry import add_priv_test_generator


def _emit_guarded_chunk(td: TestData, satp_mode: str) -> TestChunk:
    """Emit one SATP-mode chunk with the same guard logic as before."""
    guard = MODE_GUARDS[satp_mode]

    def build_us(xlen: int, mode: str = satp_mode) -> list[str]:
        return emit_mode(td, "umode", COVERGROUP_U_S, xlen, mode)

    tc = td.begin_test_chunk(split_name=f"US_{satp_mode}")
    if guard:
        tc.code.append(f"#ifdef {guard}")
    tc.code.extend(both_xlens(build_us))
    if guard:
        tc.code.append(f"#endif // {guard}")
    return tc


@add_priv_test_generator(
    "ZicfilpUS",
    required_extensions=["Zicfilp", "Zicsr", "U", "S"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zca"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilp_us(td: TestData) -> list[TestChunk]:
    """Generate U-mode (S implemented) tests. One chunk per SATP mode."""
    test_chunks: list[TestChunk] = []

    for satp_mode in MODES:
        _emit_guarded_chunk(td, satp_mode)
        test_chunks.append(td.end_test_chunk())

    return test_chunks
