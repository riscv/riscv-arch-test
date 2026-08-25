##################################
# priv/pmp/suites/PMPZalrsc.py
#
# PMPZalrsc: PMP enforcement of load-reserved / store-conditional.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZalrsc suite: WR bits control LR/SC at every supported width."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import LOCKED_LXWR_CASES, banner, exec_region, walk_file
from testgen.priv.pmp.model import XLENS, PmpFile

#: Configurations that permit both the load and the store, where the SC is expected to
#: succeed and so runs in the bounded retry loop.
_SUCCESS_CASES = {"1011", "1111"}


@add_pmp_suite("PMPZalrsc")
def build() -> list[PmpFile]:
    return [
        walk_file(
            xlen,
            "pmpzalrsc_cfg_wr.S",
            "LRSC",
            LOCKED_LXWR_CASES,
            "napot",
            banner=banner(
                "cp_cfg_RW for PMPZalrsc is fully covered in this test file.",
                "LR/SC pairs against a locked NAPOT region with each legal XWR.",
            ),
            prefix="pmpzalrsc_cfg_wr",
            required_extensions=("Zalrsc", "Sm"),
            march=f"rv{xlen.bits}i_zicsr_zifencei_zalrsc",
            data=exec_region(pad=None),
            macro_for=lambda lxwr: "LRSC_SUCCESS" if lxwr in _SUCCESS_CASES else "LRSC",
        )
        for xlen in XLENS.values()
    ]
