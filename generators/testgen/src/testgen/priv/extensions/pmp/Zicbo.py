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
)
from testgen.priv.extensions.pmp.probes import (
    ProbeGenerator,
    gen_cbom,
    gen_cboz,
    gen_prefetch,
)
from testgen.priv.registry import add_priv_test_generator

# The locked NAPOT region is max(page, grain) bytes from TEST_FOR_EXECUTION; pad to its end so that
# nothing the trap handler writes (e.g. the trap signature) shares it at grains above a page.
_PAGE_REGION = [*make_exec_region(("1024", "nop"), pad=None), ".p2align 12", ".p2align (UDB_PMP_GRANULARITY)"]


def _make_cbo_chunks(
    test_data: TestData, name: str, probe_generator: ProbeGenerator, coverpoints: str, instructions: str
) -> list[TestChunk]:
    chunks = []
    for number, lxwr in ((1, "1000"), (2, "1001"), (3, "1011")):
        chunk = test_data.begin_test_chunk(f"Zicbo_{name}_wr_{number:02d}")
        chunk.section_header = comment_banner(
            coverpoints,
            f"{instructions} against a locked page-sized NAPOT region with WR = {lxwr[2:]}.",
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data,
                [(lxwr, 0)],
                "napot",
                probe_generator,
                lambda instruction: f"cp_cbo_{instruction.removeprefix('cbo.')}",
                first=number,
                napot_mask=napot_mask_defines(12),
            )
        )
        chunk.raw_data.extend(_PAGE_REGION)
        chunks.append(test_data.end_test_chunk())
    return chunks


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_cbom(test_data: TestData) -> list[TestChunk]:
    return _make_cbo_chunks(
        test_data, "cbom", gen_cbom, "cp_cbo_clean, cp_cbo_flush and cp_cbo_inval", "cbo.clean/flush/inval"
    )


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_cboz(test_data: TestData) -> list[TestChunk]:
    return _make_cbo_chunks(test_data, "cboz", gen_cboz, "cp_cbo_zero", "cbo.zero")


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    # prefetch.i/r/w are HINTs (ORI with rd = x0), so the test runs with or without Zicbop
    required_extensions=["Sm"],
    march_extensions=["Zicbop"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_prefetch(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Zicbo_prefetch")
    chunk.section_header = comment_banner(
        "cp_prefetch_i, cp_prefetch_r and cp_prefetch_w",
        "prefetch.i/r/w against a locked page-sized NAPOT region with each legal XWR; never faults.",
    )
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            LOCKED_LXWR_CASES,
            "napot",
            gen_prefetch,
            lambda instruction: f"cp_prefetch_{instruction.removeprefix('prefetch.')}",
            napot_mask=napot_mask_defines(12),
        )
    )
    chunk.raw_data.extend(_PAGE_REGION)
    return [test_data.end_test_chunk()]
