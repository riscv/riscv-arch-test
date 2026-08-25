##################################
# priv/pmp/suites/PMPZicbo.py
#
# PMPZicbo: PMP enforcement of cache-block operations and prefetch hints.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZicbo suite: WR bits control cbo.*, and prefetch.* never faults."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import LOCKED_LXWR_CASES, banner, exec_region, walk_file
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

#: The region under test is a whole page, so the NAPOT mask covers at least 4 KiB.
_PAGE_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY > 12",
    "    #define PMPZICBO_REGION_SHIFT  UDB_PMP_GRANULARITY",
    "#else",
    "    #define PMPZICBO_REGION_SHIFT  12",
    "#endif",
    "#define PMP_MASK                   ~((1 << (PMPZICBO_REGION_SHIFT - 3))-1)",
    "#define PMP_REGION_SIZE            ((1 << (PMPZICBO_REGION_SHIFT - 3)) - 1)",
]

#: menvcfg.CBIE, CBCFE and CBZE must all be set for cbo.* to be legal.
_ENABLE_CBO = ["    LI(t0, 0xF0)", "    csrrs zero, menvcfg, t0"]

_PAGE_REGION = exec_region(("1024", "nop"), pad=None)


def _file(
    xlen: Xlen,
    filename: str,
    macro: str,
    cases: list[tuple[str, int]],
    *,
    banner: str,
    prefix: str,
    required_extensions: tuple[str, ...],
    march: str,
    first: int = 1,
) -> PmpFile:
    return walk_file(
        xlen,
        filename,
        macro,
        cases,
        "napot",
        banner=banner,
        prefix=prefix,
        required_extensions=required_extensions,
        march=march,
        first=first,
        extra_setup=_ENABLE_CBO,
        napot_mask=_PAGE_MASK_DEFINES,
        data=_PAGE_REGION,
    )


@add_pmp_suite("PMPZicbo")
def build() -> list[PmpFile]:
    files: list[PmpFile] = []
    for xlen in XLENS.values():
        for number, lxwr in ((1, "1000"), (2, "1001"), (3, "1011")):
            files.append(
                _file(
                    xlen,
                    f"pmpzicbo_cbo_wr_{number:02d}.S",
                    "CBO",
                    [(lxwr, 0)],
                    first=number,
                    banner=banner(
                        "cp_cbo for PMPZicbo is partially covered in this test file.",
                        f"cbo.zero/clean/flush/inval against a locked page-sized NAPOT region with WR = {lxwr[2:]}.",
                    ),
                    prefix="pmpzicbo_cbo",
                    required_extensions=("Sm", "Zicbom", "Zicboz"),
                    march=f"rv{xlen.bits}i_zicsr_zifencei_zicbom_zicboz",
                )
            )
        files.append(
            _file(
                xlen,
                "pmpzicbo_prefetch.S",
                "PREFETCH",
                LOCKED_LXWR_CASES,
                banner=banner(
                    "cp_prefetch for PMPZicbo is partially covered in this test file.",
                    "prefetch.i/r/w against a locked page-sized NAPOT region with each legal XWR; never faults.",
                ),
                prefix="pmpzicbo",
                required_extensions=("Sm", "Zicbop"),
                march=f"rv{xlen.bits}i_zicsr_zifencei_zicbop",
            )
        )
    return files
