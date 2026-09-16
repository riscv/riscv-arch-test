##################################
# priv/extensions/ZicfilpSm.py
#
# Zicfilp M-mode (Sm) privileged extension test generator.
# Author : Eman Nasar email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicfilp M-mode test generator: mseccfg.MLPE and mstatus.MPELP."""

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
    march_extensions=["Zca"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilp_m(td: TestData) -> list[TestChunk]:
    """Generate M-mode (Sm) tests. Single chunk (bare metal)."""
    test_chunks: list[TestChunk] = []

    def build_sm(xlen: int) -> list[str]:
        # M-mode runs bare; mode-entry code must not fall through into _tgt_lpad_zero.
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
