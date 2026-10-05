##################################
# priv/extensions/pmp/PMPZacas.py
#
# PMPZacas: PMP entries that match only part of an amocas.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZacas suite: an aligned amocas is one memory operation even when it is wider than XLEN, so it fails when
the deciding PMP entry matches only part of it. The same holds for a misaligned amocas inside a misaligned
atomicity granule."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.partial import (
    ALIGNED_NA4,
    ALIGNED_TOR,
    ENTRIES_PARAM,
    GRANULE_TOR,
    QUAD_NAPOT,
    QUAD_TOR,
    gen_accesses,
    granule_accesses,
    make_partial_chunk,
)
from testgen.priv.registry import add_priv_test_generator

_EXTENSIONS = [["I", "E"], "Zacas", "Sm"]
_MARCH = ["Zaamo", "Zacas", "Sm"]

_WHY = "the access fails even with L=0."


@add_priv_test_generator(
    "PMPZacas",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    params=[ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpzacas_partial_na4(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_na4",
            ALIGNED_NA4,
            gen_accesses([("amocas.d", None)]),
            "cp_partial_match_d",
            "amocas.d on aligned doublewords that NA4 entries match in the lower half, the upper half or\n"
            f"both; {_WHY}",
        )
    ]


@add_priv_test_generator(
    "PMPZacas",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    params=[ENTRIES_PARAM, "PMP_GRANULARITY: 2", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzacas_partial_tor(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_tor",
            ALIGNED_TOR,
            gen_accesses([("amocas.d", None)]),
            "cp_partial_match_d",
            "amocas.d on aligned doublewords that 4-byte TOR entries match in the lower half, the upper half or\n"
            f"both; {_WHY}",
        )
    ]


@add_priv_test_generator(
    "PMPZacas",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: '<=3'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpzacas_quad_napot(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "quad_napot",
            QUAD_NAPOT,
            gen_accesses([("amocas.q", None)]),
            "cp_partial_match_q",
            "amocas.q on aligned quadwords that 8-byte NAPOT entries match in the lower half, the upper half or\n"
            f"both; {_WHY}",
        )
    ]


@add_priv_test_generator(
    "PMPZacas",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    params=["MXLEN: 64", ENTRIES_PARAM, "PMP_GRANULARITY: '<=3'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzacas_quad_tor(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "quad_tor",
            QUAD_TOR,
            gen_accesses([("amocas.q", None)]),
            "cp_partial_match_q",
            "amocas.q on aligned quadwords that 8-byte TOR entries match in the lower half, the upper half or\n"
            f"both; {_WHY}",
        )
    ]


@add_priv_test_generator(
    "PMPZacas",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=[*_EXTENSIONS, "Zama16b"],
    march_extensions=_MARCH,
    params=[ENTRIES_PARAM, "PMP_GRANULARITY: '<=3'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzacas_granule(test_data: TestData) -> list[TestChunk]:
    return [
        make_partial_chunk(
            test_data,
            "partial_granule",
            GRANULE_TOR,
            granule_accesses(words=[("amocas.w", None)], doubles=[("amocas.d", None)]),
            "cp_misaligned_mag16",
            "Misaligned amocas.w and amocas.d inside a 16-byte granule that one-grain TOR entries match in the\n"
            "lower part, the upper part or both. Within a misaligned atomicity granule the AMO is one memory\n"
            "operation, so it fails.",
        )
    ]
