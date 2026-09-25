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
