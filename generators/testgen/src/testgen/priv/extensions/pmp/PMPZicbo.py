##################################
# priv/extensions/pmp/PMPZicbo.py
#
# PMPZicbo: PMP behavior of cache-block and prefetch instructions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZicbo suite: cache-block and prefetch instructions checked against PMP."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    lxwr_walk_body,
    make_exec_region,
)
from testgen.priv.extensions.pmp.probes import (
    gen_cbo,
    gen_prefetch,
)
from testgen.priv.registry import add_priv_test_generator

_PAGE_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY > 12",
    "#define PMPZICBO_REGION_SHIFT  UDB_PMP_GRANULARITY",
    "#else",
    "#define PMPZICBO_REGION_SHIFT  12",
    "#endif",
    "#define PMP_MASK                   ~((1 << (PMPZICBO_REGION_SHIFT - 3))-1)",
    "#define PMP_REGION_SIZE            ((1 << (PMPZICBO_REGION_SHIFT - 3)) - 1)",
]

_ENABLE_CBO = ["LI(t0, 0xF0)", "csrrs zero, menvcfg, t0"]
_PAGE_REGION = make_exec_region(("1024", "nop"), pad=None)


@add_priv_test_generator(
    "PMPZicbo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbom", "Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_cbo(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for number, lxwr in ((1, "1000"), (2, "1001"), (3, "1011")):
        chunk = test_data.begin_test_chunk(f"cbo_wr_{number:02d}")
        chunk.section_header = comment_banner(
            "cp_cbo", f"cbo.zero/clean/flush/inval against a locked page-sized NAPOT region with WR = {lxwr[2:]}."
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data,
                [(lxwr, 0)],
                "napot",
                gen_cbo,
                "cp_cbo",
                first=number,
                extra_setup=_ENABLE_CBO,
                napot_mask=_PAGE_MASK_DEFINES,
            )
        )
        chunk.raw_data.extend(_PAGE_REGION)
        chunks.append(test_data.end_test_chunk())
    return chunks


@add_priv_test_generator(
    "PMPZicbo",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbop"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_prefetch(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("prefetch")
    chunk.section_header = comment_banner(
        "cp_prefetch", "prefetch.i/r/w against a locked page-sized NAPOT region with each legal XWR; never faults."
    )
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            LOCKED_LXWR_CASES,
            "napot",
            gen_prefetch,
            "cp_prefetch",
            extra_setup=_ENABLE_CBO,
            napot_mask=_PAGE_MASK_DEFINES,
        )
    )
    chunk.raw_data.extend(_PAGE_REGION)
    return [test_data.end_test_chunk()]
