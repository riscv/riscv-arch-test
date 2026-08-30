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
    make_sig_strings,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPF",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["F", "Sm"],
    march_extensions=["F", "D", "Zfhmin"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    xlens=(32, 64),
)
def make_pmpf(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("cfg_wr")
    chunk.section_header = comment_banner(
        "cp_cfg_RW", "Every floating-point load and store width against a locked NAPOT region with each legal XWR."
    )
    chunk.code.extend(lxwr_walk_body(test_data.xlen, LOCKED_LXWR_CASES, "napot", "F"))
    strings = make_sig_strings("F", test_data.xlen, "pmpf_cfg_wr")
    chunk.data_strings.extend(f'{label}_str: .string "\\"{message}\\""' for label, message in strings)
    chunk.sigupd_count = len(LOCKED_LXWR_CASES) * len(strings)
    chunk.num_testcases = len(strings)
    chunk.raw_data.extend(REGION_BLOBS["off"])
    return [test_data.end_test_chunk()]
