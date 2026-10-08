##################################
# priv/extensions/pmp/PMPZalrsc.py
#
# PMPZalrsc: PMP enforcement of load-reserved / store-conditional.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZalrsc suite: WR bits control LR/SC at every supported width."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    lxwr_walk_body,
    make_exec_region,
)
from testgen.priv.extensions.pmp.partial import (
    ALIGNED_NA4,
    ALIGNED_TOR,
    ENTRIES_PARAM,
    gen_accesses,
    make_partial_chunk,
)
from testgen.priv.extensions.pmp.probes import (
    gen_lrsc,
    gen_lrsc_success,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPZalrsc",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zalrsc", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzalrsc(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("cfg_wr")
    chunk.section_header = comment_banner("cp_cfg_RW", "LR/SC pairs against a locked NAPOT region with each legal XWR.")
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            LOCKED_LXWR_CASES,
            "napot",
            {lxwr: gen_lrsc_success if lxwr in ("1011", "1111") else gen_lrsc for lxwr, _ in LOCKED_LXWR_CASES},
            "cp_cfg_RW",
        )
    )
    chunk.raw_data.extend(make_exec_region(pad=None))
    return [test_data.end_test_chunk()]


# No lr.d precedes the sc.d: an lr.d of the same bytes would fault, so there is no reservation.
_LRSC_D = gen_accesses([("lr.d", None), ("sc.d", None)])


@add_priv_test_generator(
    "PMPZalrsc",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zalrsc", "Sm"],
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpzalrsc_partial_na4(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_na4",
            ALIGNED_NA4,
            _LRSC_D,
            "cp_partial_match",
            "lr.d, and sc.d without a reservation, on aligned doublewords that NA4 entries match in the lower\n"
            "half, the upper half or both; both fail even with L=0. No SC retires unless it passes the permission\n"
            "checks.",
        )
    ]


@add_priv_test_generator(
    "PMPZalrsc",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zalrsc", "Sm"],
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzalrsc_partial_tor(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_tor",
            ALIGNED_TOR,
            _LRSC_D,
            "cp_partial_match",
            "lr.d, and sc.d without a reservation, on aligned doublewords that 4-byte TOR entries match in the\n"
            "lower half, the upper half or both; both fail even with L=0. No SC retires unless it passes the\n"
            "permission checks.",
        )
    ]
