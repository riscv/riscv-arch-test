##################################
# priv/pmp/suites/PMPZaamo.py
#
# PMPZaamo: PMP enforcement of atomic memory operations.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZaamo suite: WR bits control every Zaamo atomic memory operation."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import LOCKED_LXWR_CASES, banner, exec_region, walk_file
from testgen.priv.pmp.model import XLENS, PmpFile


@add_pmp_suite("PMPZaamo")
def build() -> list[PmpFile]:
    return [
        walk_file(
            xlen,
            "pmpzaamo_cfg_wr.S",
            "AMO",
            LOCKED_LXWR_CASES,
            "napot",
            banner=banner(
                "cp_cfg_RW for PMPZaamo is fully covered in this test file.",
                "Every AMO against a locked NAPOT region with each legal XWR.",
            ),
            prefix="pmpzaamo_cfg_wr",
            required_extensions=("Zaamo", "Sm"),
            march=f"rv{xlen.bits}i_zicsr_zifencei_zaamo",
            data=exec_region(pad=None),
        )
        for xlen in XLENS.values()
    ]
