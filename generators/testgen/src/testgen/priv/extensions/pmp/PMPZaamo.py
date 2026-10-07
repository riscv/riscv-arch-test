##################################
# priv/extensions/pmp/PMPZaamo.py
#
# PMPZaamo: PMP enforcement of atomic memory operations.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZaamo suite: WR bits control every Zaamo atomic memory operation."""

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
    GRANULE_TOR,
    RV64,
    gen_accesses,
    granule_accesses,
    make_partial_chunk,
)
from testgen.priv.extensions.pmp.probes import (
    gen_amo,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPZaamo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzaamo(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("cfg_wr")
    chunk.section_header = comment_banner("cp_cfg_RW", "Every AMO against a locked NAPOT region with each legal XWR.")
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", gen_amo, "cp_cfg_RW"))
    chunk.raw_data.extend(make_exec_region(pad=None))
    return [test_data.end_test_chunk()]


_AMOS = ["amoswap", "amoadd", "amoxor", "amoand", "amoor", "amomin", "amomax", "amominu", "amomaxu"]
_AMO_D = gen_accesses([(f"{amo}.d", None) for amo in _AMOS])
_AMO_GRANULE = granule_accesses(
    words=[(f"{amo}.w", None) for amo in _AMOS], doubles=[(f"{amo}.d", RV64) for amo in _AMOS]
)


@add_priv_test_generator(
    "PMPZaamo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm"],
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpzaamo_partial_na4(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_na4",
            ALIGNED_NA4,
            _AMO_D,
            "cp_partial_match",
            "Every .d AMO on aligned doublewords that NA4 entries match in the lower half, the upper half or both;\n"
            "an aligned AMO is one memory operation, so it fails even with L=0.",
        )
    ]


@add_priv_test_generator(
    "PMPZaamo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm"],
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzaamo_partial_tor(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_tor",
            ALIGNED_TOR,
            _AMO_D,
            "cp_partial_match",
            "Every .d AMO on aligned doublewords that 4-byte TOR entries match in the lower half, the upper half\n"
            "or both; an aligned AMO is one memory operation, so it fails even with L=0.",
        )
    ]


@add_priv_test_generator(
    "PMPZaamo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zaamo", "Sm", "Zama16b"],
    march_extensions=["Zaamo", "Sm"],
    params=[ENTRIES_PARAM, "PMP_GRANULARITY: '<=3'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzaamo_partial_granule(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_granule",
            GRANULE_TOR,
            _AMO_GRANULE,
            "cp_misaligned_mag16",
            "Misaligned .w (and .d on RV64) AMOs inside a 16-byte granule that one-grain TOR entries match in the\n"
            "lower part, the upper part or both. Within a misaligned atomicity granule the AMO is one memory\n"
            "operation, so it fails.",
        )
    ]
