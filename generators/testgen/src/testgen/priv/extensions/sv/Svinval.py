##################################
# priv/extensions/sv/Svinval.py
#
# Svinval instruction tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval privilege and TVM tests.

The H group boots to HS-mode, and the HS-mode handler takes every trap (hedeleg = 0).  Tests with mstatus.TVM = 1
are in the SmH group because the HS-mode handler reads satp.  Under two-stage translation, the SFENCE.W.INVAL,
HINVAL.VVMA or HINVAL.GVMA (or SINVAL.VMA in VS-mode), SFENCE.INVAL.IR sequence must remove a changed VS-stage or
G-stage leaf (SvHFenceCommon).  The SmH group boots to M-mode and delegates nothing, so the M-mode handler takes
every trap.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.page_tables import SV32X4, SV39X4, VS_SV32, VS_SV39
from testgen.priv.extensions.sv.SvHFenceCommon import HINVAL_GVMA, HINVAL_VVMA, SINVAL_VMA_VS, fence_chunk
from testgen.priv.registry import add_priv_test_generator

_OPERATIONS = (
    ("sfence_w_inval", "sfence.w.inval"),
    ("sinval_vma", "sinval.vma x0, x0"),
    ("sfence_inval_ir", "sfence.inval.ir"),
    ("sfence_vma", "sfence.vma x0, x0"),
)
# The Svinval instructions with H: sfence.vma is covered by HSm
H_OPERATIONS = (
    *_OPERATIONS[:3],
    ("hinval_vvma", "hinval.vvma x0, x0"),
    ("hinval_gvma", "hinval.gvma x0, x0"),
)


def add_operations(test_data: TestData, number: int, covergroup: str) -> list[str]:
    lines = []
    for name, instruction in _OPERATIONS:
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", "cp_svinval", covergroup),
                instruction,
                "",
            ]
        )
    return lines


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svinval(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval")
    chunk.code.extend(
        [
            *add_operations(test_data, 1, "Svinval_cg"),
            "RVTEST_TSBI_GOTO_UMODE",
            *add_operations(test_data, 2, "Svinval_cg"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    chunk.trap_sigupd_count = 8
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["Sm", "S", "Svinval"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svinvalsm_tvm(test_data: TestData) -> list[TestChunk]:
    tvm_reg = test_data.int_regs.get_register(exclude_regs=[0])
    chunk = test_data.begin_test_chunk("Sm_Svinval_mstatus_tvm")
    # The mstatus readback checks the setup that the cp_tvm coverpoint samples.
    tvm_label = test_data.add_testcase("tvm", "cp_tvm", "Svinval_Sm_cg").removesuffix(":")
    number = 0
    code: list[str] = []
    for tvm in (0, 1):
        if tvm:
            code.extend(
                [
                    f"LI(x{tvm_reg}, MSTATUS_TVM)",
                    f"csrs mstatus, x{tvm_reg}",
                    f"{tvm_label}:",
                    f"RVTEST_SIGUPD_CSR_READ(mstatus, x{tvm_reg}, {tvm_label}, {tvm_label}_str)",
                ]
            )
        previous = "Mmode"
        for mode in ("Mmode", "Smode", "Umode"):
            number += 1
            switch = [] if mode == previous else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]
            code.extend([*switch, *add_operations(test_data, number, "Svinval_Sm_cg")])
            previous = mode
        if previous != "Mmode":
            code.append("RVTEST_TSBI_GOTO_MMODE")
    chunk.code.extend(code)
    chunk.sigupd_count = 1
    chunk.trap_sigupd_count = 20
    test_data.int_regs.return_register(tvm_reg)
    return [test_data.end_test_chunk()]


def svinval_h_tests(test_data: TestData, boot: str, tvms: tuple[int, ...], covergroup: str) -> list[str]:
    """Run the Svinval instructions for each mstatus.TVM in tvms and each hstatus.VTVM.

    boot is the mode the group boots to, M or S.  The instructions run in the boot mode and then in HS, VS, VU and
    U mode, except with TVM = 0 in the M-mode group: the H group covers those modes.  The coverpoints are cp_svinval
    in Svinval_H_cg, and cp_svinval_m (M-mode) and cp_svinval_tvm (TVM = 1 below M-mode) in Svinval_SmH_cg.
    """
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
    "Svinval",
    required_extensions=["H", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svinvalh(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("H_Svinval_hstatus_vtvm")
    chunk.code.extend(svinval_h_tests(test_data, "S", (0,), "Svinval_H_cg"))
    chunk.trap_sigupd_count = trap_sigupd_count(25)  # VS, VU and U traps with VTVM = 0 and 1
    return [test_data.end_test_chunk()]


INVAL_FENCES = (HINVAL_VVMA, HINVAL_GVMA, SINVAL_VMA_VS)


@add_priv_test_generator(
    "Svinval",
    required_extensions=["H", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svinvalh_sv39x4(test_data: TestData) -> list[TestChunk]:
    return [fence_chunk(test_data, SV39X4, VS_SV39, "H_sv39x4_inval", INVAL_FENCES, "Svinval_H_cg")]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["H", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svinvalh_sv32x4(test_data: TestData) -> list[TestChunk]:
    return [fence_chunk(test_data, SV32X4, VS_SV32, "H_sv32x4_inval", INVAL_FENCES, "Svinval_H_cg")]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["Sm", "H", "Svinval"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svinvalhsm(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("SmH_Svinval_mstatus_tvm")
    chunk.code.extend(svinval_h_tests(test_data, "M", (0, 1), "Svinval_SmH_cg"))
    chunk.trap_sigupd_count = trap_sigupd_count(29)  # TVM = 1: 4 in HS, 5 in VS, 10 in VU, 10 in U
    return [test_data.end_test_chunk()]
