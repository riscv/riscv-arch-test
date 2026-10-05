##################################
# priv/extensions/pmp/PMPF.py
#
# PMPF: PMP enforcement of floating-point loads and stores.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPF suite: WR bits control every width of floating-point load and store."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    REGION_BLOBS,
    lxwr_walk_body,
)
from testgen.priv.extensions.pmp.partial import (
    ENTRIES_PARAM,
    GRANULE_TOR,
    RV64_D,
    granule_accesses,
    make_partial_chunk,
)
from testgen.priv.extensions.pmp.probes import (
    gen_float,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPF",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=[["I", "E"], "F", "Sm"],
    march_extensions=["F", "D", "Zfhmin"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpf(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("cfg_wr")
    chunk.section_header = comment_banner(
        "cp_cfg_RW", "Every floating-point load and store width against a locked NAPOT region with each legal XWR."
    )
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", gen_float, "cp_cfg_RW"))
    # The NAPOT pad keeps the region 8-byte aligned at every grain, so fld and fsd stay naturally aligned.
    chunk.raw_data.extend(REGION_BLOBS["napot_pad"])
    return [test_data.end_test_chunk()]


# fld and fsd are in the granule only when they are at most XLEN bits.
_FP_GRANULE = granule_accesses(words=[("flw", None), ("fsw", None)], doubles=[("fld", RV64_D), ("fsd", RV64_D)])


@add_priv_test_generator(
    "PMPF",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=[["I", "E"], "F", "Sm", "Zama16b"],
    march_extensions=["F", "D"],
    params=[ENTRIES_PARAM, "PMP_GRANULARITY: '<=3'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpf_partial_granule(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_granule",
            GRANULE_TOR,
            _FP_GRANULE,
            "cp_misaligned_mag16",
            "Misaligned flw, fsw (and fld, fsd on RV64) inside a 16-byte granule that one-grain TOR entries match\n"
            "in the lower part, the upper part or both. Within a misaligned atomicity granule the access is one\n"
            "memory operation, so it fails.",
        )
    ]
