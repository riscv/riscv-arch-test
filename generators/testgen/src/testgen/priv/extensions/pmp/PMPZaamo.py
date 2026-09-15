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
