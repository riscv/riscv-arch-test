##################################
# priv/extensions/pmp/Zicbo.py
#
# PMP Zicbo: PMP behavior of cache-block and prefetch instructions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP Zicbo group: cache-block and prefetch instructions checked against PMP."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    lxwr_walk_body,
    make_exec_region,
    napot_mask_defines,
    tor_twin_parts,
)
from testgen.priv.extensions.pmp.probes import (
    gen_cbo,
    gen_prefetch,
)
from testgen.priv.registry import add_priv_test_generator

_ENABLE_CBO = ["LI(t0, 0xF0)", "csrrs zero, menvcfg, t0"]
# The locked NAPOT region is max(page, grain) bytes from TEST_FOR_EXECUTION; pad to its end so that
# nothing the trap handler writes (e.g. the trap signature) shares it at grains above a page.
#: The page-sized region: NAPOT encodes it from PMP_REGION_SHIFT; a TOR twin bounds the same bytes.
_PAGE_BYTES = "(1 << PMP_REGION_SHIFT)"

_PAGE_REGION = [*make_exec_region(("1024", "nop"), pad=None), ".p2align 12", ".p2align (UDB_PMP_GRANULARITY)"]


def _cbo_chunks(test_data: TestData, amode: str) -> list[TestChunk]:
    """cbo.* against one locked page-sized region, one WR encoding per file. NAPOT uses entry 0;
    the TOR twin uses entry 1, bounded below by pmpaddr0."""
    tor = "_tor" if amode == "tor" else ""
    chunks = []
    for number, lxwr in ((1, "1000"), (2, "1001"), (3, "1011")):
        chunk = test_data.begin_test_chunk(f"Zicbo_cbo_wr{tor}_{number:02d}")
        chunk.section_header = comment_banner(
            f"cp_cbo_zero{tor}, cp_cbo_clean{tor}, cp_cbo_flush{tor} and cp_cbo_inval{tor}",
            f"cbo.zero/clean/flush/inval against a locked page-sized {amode.upper()} region with WR = {lxwr[2:]}.",
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data,
                [(lxwr, 1 if tor else 0)],
                amode,
                gen_cbo,
                lambda instruction: f"cp_cbo_{instruction.removeprefix('cbo.')}{tor}",
                first=number,
                extra_setup=_ENABLE_CBO,
                napot_mask=napot_mask_defines(12),
                tor_bytes=_PAGE_BYTES,
            )
        )
        chunk.raw_data.extend(_PAGE_REGION)
        chunks.append(test_data.end_test_chunk())
    return chunks


def _prefetch_chunks(test_data: TestData, amode: str) -> list[TestChunk]:
    """prefetch.* against a locked page-sized region with each legal XWR. The TOR twin stacks its
    cases on entries 5, 3 and 1, so it takes two files."""
    if amode == "tor":
        parts = [
            (f"Zicbo_prefetch_tor-{part:02d}", cases, 3 * part - 2)
            for part, cases in enumerate(tor_twin_parts(LOCKED_LXWR_CASES), 1)
        ]
    else:
        parts = [("Zicbo_prefetch", LOCKED_LXWR_CASES, 1)]
    tor = "_tor" if amode == "tor" else ""
    chunks = []
    for name, cases, first in parts:
        chunk = test_data.begin_test_chunk(name)
        chunk.section_header = comment_banner(
            f"cp_prefetch_i{tor}, cp_prefetch_r{tor} and cp_prefetch_w{tor}",
            f"prefetch.i/r/w against a locked page-sized {amode.upper()} region with each legal XWR; never faults.",
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data,
                cases,
                amode,
                gen_prefetch,
                lambda instruction: f"cp_prefetch_{instruction.removeprefix('prefetch.')}{tor}",
                first=first,
                extra_setup=_ENABLE_CBO,
                napot_mask=napot_mask_defines(12),
                tor_bytes=_PAGE_BYTES,
            )
        )
        chunk.raw_data.extend(_PAGE_REGION)
        chunks.append(test_data.end_test_chunk())
    return chunks


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbom", "Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpzicbo_cbo(test_data: TestData) -> list[TestChunk]:
    return _cbo_chunks(test_data, "napot")


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbom", "Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzicbo_cbo_tor(test_data: TestData) -> list[TestChunk]:
    return _cbo_chunks(test_data, "tor")


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbop"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpzicbo_prefetch(test_data: TestData) -> list[TestChunk]:
    return _prefetch_chunks(test_data, "napot")


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbop"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzicbo_prefetch_tor(test_data: TestData) -> list[TestChunk]:
    return _prefetch_chunks(test_data, "tor")
