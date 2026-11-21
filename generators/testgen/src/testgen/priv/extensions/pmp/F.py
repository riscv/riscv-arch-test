##################################
# priv/extensions/pmp/F.py
#
# PMP F: PMP enforcement of floating-point loads and stores.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP F group: WR bits control every width of floating-point load and store."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    REGION_BLOBS,
    TOR_TWIN_BYTES,
    lxwr_walk_body,
    tor_twin_parts,
)
from testgen.priv.extensions.pmp.probes import (
    cross_by_access,
    gen_float,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["F", "Sm"],
    march_extensions=["F", "D", "Zfhmin"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpf(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("F_cfg_wr")
    chunk.section_header = comment_banner(
        "cp_cfg_R and cp_cfg_W",
        "Every floating-point load and store width against a locked NAPOT region with each legal XWR.",
    )
    crosses = cross_by_access(load="cp_cfg_R", store="cp_cfg_W")
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", gen_float, crosses))
    # The NAPOT pad keeps the region 8-byte aligned at every grain, so fld and fsd stay naturally aligned.
    chunk.raw_data.extend(REGION_BLOBS["napot_pad"])
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["F", "Sm"],
    march_extensions=["F", "D", "Zfhmin"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpf_tor(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for part, cases in enumerate(tor_twin_parts(LOCKED_LXWR_CASES), start=1):
        chunk = test_data.begin_test_chunk(f"F_cfg_wr_tor-{part:02d}")
        chunk.section_header = comment_banner(
            "cp_cfg_R_tor and cp_cfg_W_tor",
            "Every floating-point load and store width against a locked TOR region with each legal XWR.",
        )
        crosses = cross_by_access(load="cp_cfg_R_tor", store="cp_cfg_W_tor")
        chunk.code.extend(
            lxwr_walk_body(test_data, cases, "tor", gen_float, crosses, first=3 * part - 2, tor_bytes=TOR_TWIN_BYTES)
        )
        chunk.raw_data.extend(REGION_BLOBS["napot_pad"])
        chunks.append(test_data.end_test_chunk())
    return chunks
