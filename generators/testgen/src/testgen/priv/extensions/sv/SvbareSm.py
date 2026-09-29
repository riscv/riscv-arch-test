##################################
# priv/extensions/sv/SvbareSm.py
#
# SvbareSm suite: Bare-mode MPRV accesses, which need M-mode.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Bare-mode MPRV tests, which run in M-mode."""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import Crosses
from testgen.priv.extensions.sv.Svbare import bare_rwx, begin_bare_test
from testgen.priv.registry import add_priv_test_generator

_MPRV_CROSSES = Crosses("SvbareSm_cg", "cp_satp_bare_mprv_store", "cp_satp_bare_mprv_load", "cp_satp_bare_mprv_exec")


@add_priv_test_generator(
    "SvbareSm",
    required_extensions=["Sm", "S", "Svbare"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svbaresm_mprv(test_data: TestData) -> list[TestChunk]:
    chunk = begin_bare_test(test_data, "Svbare_mstatus_mprv")
    for number, mpp in ((1, "S"), (2, "U")):
        # The mstatus readback checks the setup that the mprv_mstatus coverpoint samples.
        label = test_data.add_testcase(f"test{number}_mstatus", "mprv_mstatus", "SvbareSm_cg")
        chunk.code.extend(
            [
                "LI(t0, MSTATUS_MPRV)",
                "csrs mstatus, t0",
                "LI(t0, 0x1800)",
                "csrc mstatus, t0",
                *(("LI(t0, 0x800)", "csrs mstatus, t0") if mpp == "S" else ()),
                label,
                gen_csr_read_sigupd(14, ("mstatus", None), test_data),
                *bare_rwx(test_data, f"test{number}", crosses=_MPRV_CROSSES),
            ]
        )
    return [test_data.end_test_chunk()]
