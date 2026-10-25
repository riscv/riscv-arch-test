##################################
# priv/extensions/sv/Svinval.py
#
# Svinval instruction tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval privilege, TVM and invalidation tests."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.generate import set_atp
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV32X4,
    SV39,
    SV39X4,
    VS_SV32,
    VS_SV39,
    PteFlags,
    SvMode,
    create_page_mapping,
    lower_table_data,
    write_pte,
)
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


_S_INVAL_PAGES = (
    ".p2align 12",
    "sinval_page_a:",
    ".4byte 0x0a0a0a0a",
    ".skip 4092",
    "sinval_page_b:",
    ".4byte 0x0b0b0b0b",
    ".skip 4092",
)

# S-mode Svinval sequence operands: (bin name, rs1, rs2).  rs1 is x0 or the address; rs2 is x0, the current ASID or
# every ASIDMAX bit, which a hart with fewer ASID bits ignores.
_S_INVAL_CASES = (
    ("rs1_x0_rs2_x0", "x0", "x0"),
    ("rs1_va_rs2_x0", "va", "x0"),
    ("rs1_x0_rs2_asid", "x0", "asid"),
    ("rs1_va_rs2_asid", "va", "asid"),
    ("rs1_va_rs2_asidmax", "va", "asidmax"),
)


def _s_inval_case(test_data: TestData, sv: SvMode, name: str, rs1: str, rs2: str) -> list[str]:
    """Load through page A, point the leaf at page B, run the Svinval sequence, and load again."""
    label = test_data.add_testcase(name, "cp_sinval_vma", "Svinval_cg")
    sig_label = label.removesuffix(":")
    asid_mask, asid_shift = f"SATP{sv.xlen}_ASID", 44 if sv.xlen == 64 else 22
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = [
        "",
        f"// Testcase: sinval.vma with {name}",
        *create_page_mapping(
            sv,
            leaf_level=0,
            leaf_flags=PteFlags(),
            virtual_address=sv.data_va,
            physical_address="sinval_page_a",
            regs=regs,
        ),
        "sfence.vma",
    ]
    va, data = test_data.int_regs.get_registers(2)
    lines.extend(
        [
            f"LI(x{va}, {sv.data_va})",
            f"lw x{data}, 0(x{va})",
            write_sigupd(data, test_data, label=sig_label),
            *write_pte(
                sv, level=0, flags=PteFlags(), virtual_address=sv.data_va, physical_address="sinval_page_b", regs=regs
            ),
        ]
    )
    if rs2 == "asid":
        lines.extend(
            [
                f"LI(x{tmp}, {asid_mask})",
                f"csrr x{pte}, satp",
                f"and x{pte}, x{pte}, x{tmp}",
                f"srli x{pte}, x{pte}, {asid_shift}",
            ]
        )
    elif rs2 == "asidmax":
        lines.append(f"LI(x{pte}, ({asid_mask}) >> {asid_shift})")
    lines.extend(
        [
            label,
            "sfence.w.inval",
            f"sinval.vma {'x0' if rs1 == 'x0' else f'x{va}'}, {'x0' if rs2 == 'x0' else f'x{pte}'}",
            "sfence.inval.ir",
            f"lw x{data}, 0(x{va})",
            write_sigupd(data, test_data, label=sig_label),
            "",
        ]
    )
    test_data.int_regs.return_registers([pte, addr, tmp, va, data])
    return lines


def _s_inval_chunk(test_data: TestData, sv: SvMode) -> TestChunk:
    """Check that the S-mode Svinval sequence removes a changed leaf.

    S-mode maps sv.data_va to sinval_page_a and loads from it, which may cache the translation, then points the leaf
    at sinval_page_b and runs sfence.w.inval, sinval.vma and sfence.inval.ir.  The next load must read page B.  The
    cases run with every implemented satp.ASID bit set.  A hart that caches nothing passes.
    """
    chunk = test_data.begin_test_chunk(f"{sv.name}_inval")
    chunk.section_header = comment_banner(
        "cp_sinval_vma",
        "Change an S-mode leaf, run sfence.w.inval, sinval.vma and sfence.inval.ir with x0, address and ASID\n"
        "operands, and check that the next load uses the new leaf",
    )
    chunk.raw_data.extend([*_S_INVAL_PAGES, *lower_table_data(sv)])
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    code = ["// Identity map the test image, turn on translation and set every implemented satp.ASID bit"]
    for label in ("rvtest_code_begin", "rvtest_data_begin", "rvtest_sig_end"):
        code.extend(
            write_pte(
                sv,
                level=sv.levels - 1,
                flags=PteFlags(),
                virtual_address=label,
                physical_address=label,
                regs=regs,
                va_is_label=True,
                superpage=True,
            )
        )
    code.extend([*set_atp(sv, pte, addr), f"LI(x{tmp}, SATP{sv.xlen}_ASID)", f"csrs satp, x{tmp}", "sfence.vma"])
    test_data.int_regs.return_registers(list(regs))
    for name, rs1, rs2 in _S_INVAL_CASES:
        code.extend(_s_inval_case(test_data, sv, name, rs1, rs2))
    chunk.code.extend([*code, "csrw satp, zero", "sfence.vma"])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval", "Sv39"],
    march_extensions=["S", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svinval_sv39(test_data: TestData) -> list[TestChunk]:
    return [_s_inval_chunk(test_data, SV39)]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval", "Sv32"],
    march_extensions=["S", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svinval_sv32(test_data: TestData) -> list[TestChunk]:
    return [_s_inval_chunk(test_data, SV32)]


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
