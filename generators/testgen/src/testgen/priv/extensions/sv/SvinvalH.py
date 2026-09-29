##################################
# priv/extensions/sv/SvinvalH.py
#
# SvinvalH suite: Svinval instructions in HS, VS, U and VU modes with hstatus.VTVM.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval tests in HS, VS, U and VU modes with hstatus.VTVM clear and set.

The suite boots to HS-mode, and the HS-mode handler takes every trap (hedeleg = 0).  Tests with
mstatus.TVM = 1 are in SvinvalHSm because the HS-mode handler reads satp.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.Svinval import H_OPERATIONS
from testgen.priv.registry import add_priv_test_generator


def svinval_h_tests(test_data: TestData, boot: str, tvms: tuple[int, ...]) -> list[str]:
    """Run the Svinval instructions for each mstatus.TVM in tvms and each hstatus.VTVM.

    boot is the mode the suite boots to, M or S.  The instructions run in the boot mode and then in HS, VS, VU and
    U mode, except with TVM = 0 in the M-mode suite: SvinvalH covers those modes.  The coverpoints are cp_svinval
    in SvinvalH, and cp_svinval_m (M-mode) and cp_svinval_tvm (TVM = 1 below M-mode) in SvinvalHSm.
    """
    covergroup = f"{test_data.testsuite}_cg"
    temp_reg = test_data.int_regs.get_register()
    lines = []
    for tvm in tvms:
        for vtvm in (0, 1):
            if boot == "M":
                lines.extend([f"LI(x{temp_reg}, MSTATUS_TVM)", f"{'csrs' if tvm else 'csrc'} mstatus, x{temp_reg}"])
            lines.extend([f"LI(x{temp_reg}, HSTATUS_VTVM)", f"{'csrs' if vtvm else 'csrc'} hstatus, x{temp_reg}"])
            lower = [mode for mode in ("S", "VS", "VU", "U") if mode != boot] if boot == "S" or tvm else []
            for mode in (boot, *lower):
                coverpoint = "cp_svinval" if boot == "S" else "cp_svinval_m" if mode == "M" else "cp_svinval_tvm"
                if mode != boot:
                    lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
                for name, instruction in H_OPERATIONS:
                    bin_name = f"tvm{tvm}_vtvm{vtvm}_{'hs' if mode == 'S' else mode.lower()}_{name}"
                    lines.extend([test_data.add_testcase(bin_name, coverpoint, covergroup), instruction])
            if lower:
                lines.append(f"RVTEST_TSBI_GOTO_{boot}MODE")
    if boot == "M":
        lines.extend([f"LI(x{temp_reg}, MSTATUS_TVM)", f"csrc mstatus, x{temp_reg}"])
    lines.extend([f"LI(x{temp_reg}, HSTATUS_VTVM)", f"csrc hstatus, x{temp_reg}"])
    test_data.int_regs.return_register(temp_reg)
    return lines


@add_priv_test_generator(
    "SvinvalH",
    required_extensions=["H", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_svinvalh(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval_hstatus_vtvm")
    chunk.code.extend(svinval_h_tests(test_data, "S", (0,)))
    chunk.trap_sigupd_count = trap_sigupd_count(25)  # VS, VU and U traps with VTVM = 0 and 1
    return [test_data.end_test_chunk()]
