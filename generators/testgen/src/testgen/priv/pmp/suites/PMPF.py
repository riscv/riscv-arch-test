##################################
# priv/pmp/suites/PMPF.py
#
# PMPF: PMP enforcement of floating-point loads and stores.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPF suite: WR bits control every width of floating-point load and store."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import LOCKED_LXWR_CASES, REGION_BLOBS, banner, walk_file
from testgen.priv.pmp.model import XLENS, PmpFile


@add_pmp_suite("PMPF")
def build() -> list[PmpFile]:
    return [
        walk_file(
            xlen,
            "pmpf_cfg_wr.S",
            "F",
            LOCKED_LXWR_CASES,
            "napot",
            banner=banner(
                "cp_cfg_RW for PMPF is fully covered in this test file.",
                "Every floating-point load and store width against a locked NAPOT region with each legal XWR.",
            ),
            prefix="pmpf_cfg_wr",
            required_extensions=("F", "Sm"),
            march=f"rv{xlen.bits}ifd_zicsr_zifencei_zfhmin",
            data=REGION_BLOBS["off"],
        )
        for xlen in XLENS.values()
    ]
