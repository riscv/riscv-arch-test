##################################
# priv/extensions/pmp/Zaamo.py
#
# PMP Zaamo: PMP enforcement of atomic memory operations.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP Zaamo group: WR bits control every Zaamo atomic memory operation."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    TOR_TWIN_BYTES,
    lxwr_walk_body,
    make_exec_region,
    tor_twin_parts,
)
from testgen.priv.extensions.pmp.probes import (
    gen_amo,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpzaamo(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Zaamo_cfg_wr")
    chunk.section_header = comment_banner("cp_cfg_RW", "Every AMO against a locked NAPOT region with each legal XWR.")
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", gen_amo, "cp_cfg_RW"))
    chunk.raw_data.extend(make_exec_region(pad=None))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzaamo_tor(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for part, cases in enumerate(tor_twin_parts(LOCKED_LXWR_CASES), start=1):
        chunk = test_data.begin_test_chunk(f"Zaamo_cfg_wr_tor-{part:02d}")
        chunk.section_header = comment_banner(
            "cp_cfg_RW_tor", "Every AMO against a locked TOR region with each legal XWR."
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data, cases, "tor", gen_amo, "cp_cfg_RW_tor", first=3 * part - 2, tor_bytes=TOR_TWIN_BYTES
            )
        )
        chunk.raw_data.extend(make_exec_region(pad=None))
        chunks.append(test_data.end_test_chunk())
    return chunks
