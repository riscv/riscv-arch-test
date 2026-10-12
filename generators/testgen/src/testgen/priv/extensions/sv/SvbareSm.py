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
from testgen.priv.extensions.sv.generate import SvRegs, end_sv_test
from testgen.priv.extensions.sv.Svbare import bare_rwx, begin_bare_test
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "SvbareSm",
    required_extensions=["Sm", "S", "Svbare"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svbaresm_mprv(test_data: TestData) -> list[TestChunk]:
    regs = SvRegs.allocate(test_data)
    chunk = begin_bare_test(test_data, regs, "Svbare_mstatus_mprv")
    t = f"x{regs.scratch}"
    for number, mpp in ((1, "S"), (2, "U")):
        label = test_data.add_testcase(f"test{number}_mstatus", "cp_mprv", "SvbareSm_cg")
        chunk.code.extend(
            [
                f"LI({t}, MSTATUS_MPRV)",
                f"csrs mstatus, {t}",
                f"LI({t}, 0x1800)",
                f"csrc mstatus, {t}",
                *((f"LI({t}, 0x800)", f"csrs mstatus, {t}") if mpp == "S" else ()),
                label,
                gen_csr_read_sigupd(regs.result, ("mstatus", None), test_data),
                *bare_rwx(test_data, regs, f"test{number}"),
            ]
        )
    return [end_sv_test(test_data, regs)]
