##################################
# priv/extensions/ExceptionsH.py
#
# ExceptionsH hypervisor exception tests that run in HS, VS, U and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsH test generator.

The suite boots to HS-mode with medeleg delegating to HS-mode every exception but the ecalls from HS-mode and
M-mode.  hedeleg is 0 except where a test delegates to VS-mode.
"""

from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.ExceptionsHCommon import (
    DELEGATED_FAULTS,
    HEDELEG_WALK,
    HEDELEG_WRITABLE,
    hedeleg_tests,
    hlv_priority_tests,
    xtinst_exception_tests,
)
from testgen.priv.extensions.HCommon import P1P13_OFF, P1P13_ON, gated
from testgen.priv.registry import add_priv_test_generator

CG = "ExceptionsH_cg"

HEDELEGH_GATE = "__riscv_xlen == 32 && defined(SM1P13P0_OR_LATER_SUPPORTED)"


def _ecall_tests(test_data: TestData) -> list[str]:
    """Ecalls recorded in the trap signature by the HS-mode and VS-mode handlers, and traps through vstvec."""
    temp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_ecall_to_hs",
            "With hedeleg = 0, ecall from U, VS and VU modes with hstatus.SPVP = 0 and 1.  The trap record holds\n"
            "sstatus.SPP/SPIE/SIE and hstatus.SPVP/SPV/GVA; SPVP changes only for traps from VS and VU",
        ),
        "csrw hedeleg, zero",
    ]
    for mode in ("u", "vs", "vu"):
        for spvp in (0, 1):
            lines.extend(
                [
                    f"LI(x{temp_reg}, HSTATUS_SPVP)",
                    f"{'csrs' if spvp else 'csrc'} hstatus, x{temp_reg}",
                    f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
                    test_data.add_testcase(f"{mode}_spvp{spvp}", "cp_ecall_to_hs", CG),
                    "RVTEST_TSBI_ECALL_RECORD",
                    "RVTEST_TSBI_GOTO_SMODE",
                ]
            )
    lines.extend(
        [
            comment_banner(
                "cp_ecall_to_vs",
                "With hedeleg[8] = 1, ecall from VU-mode with vsstatus.SIE = 0 and 1.  The VS-mode trap record holds\n"
                "vsstatus.SPP/SPIE/SIE",
            ),
            f"LI(x{temp_reg}, 1 << CAUSE_USER_ECALL)",
            f"csrw hedeleg, x{temp_reg}",
        ]
    )
    for sie in (0, 1):
        lines.extend(
            [
                f"{'csrsi' if sie else 'csrci'} vsstatus, SSTATUS_SIE",
                "RVTEST_TSBI_GOTO_VUMODE",
                test_data.add_testcase(f"vu_sie{sie}", "cp_ecall_to_vs", CG),
                "RVTEST_TSBI_ECALL_RECORD",
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    lines.extend(
        [
            "csrci vsstatus, SSTATUS_SIE",
            comment_banner(
                "cp_vstvec",
                "With hedeleg[3] = hedeleg[8] = 1, ebreak from VS-mode and ebreak and ecall from VU-mode trap through\n"
                "vstvec, which points to a different handler than stvec.  An ecall from VS-mode is never delegated",
            ),
            f"LI(x{temp_reg}, (1 << CAUSE_BREAKPOINT) | (1 << CAUSE_USER_ECALL))",
            f"csrw hedeleg, x{temp_reg}",
            "RVTEST_TSBI_GOTO_VSMODE",
            test_data.add_testcase("vs_ebreak", "cp_vstvec", CG),
            "ebreak",
            "RVTEST_TSBI_GOTO_VUMODE",
            test_data.add_testcase("vu_ebreak", "cp_vstvec", CG),
            "ebreak",
            test_data.add_testcase("vu_ecall", "cp_vstvec", CG),
            "RVTEST_TSBI_ECALL_RECORD",
            "RVTEST_TSBI_GOTO_SMODE",
            "csrw hedeleg, zero",
        ]
    )
    test_data.int_regs.return_register(temp_reg)
    return lines


def _virtual_instruction_tests(test_data: TestData) -> list[str]:
    """Each way to raise a virtual-instruction exception from VS-mode and VU-mode (hypervisor.adoc H_virtinst_*)."""
    addr_reg, rd, save_reg, temp_reg = test_data.int_regs.get_registers(4)

    def trap(bin_name: str, coverpoint: str, instr: str, writes_rd: bool = True) -> list[str]:
        """One instruction that raises virtual instruction; rd must keep its value."""
        return [
            *([f"LI(x{rd}, 42)"] if writes_rd else []),
            test_data.add_testcase(bin_name, coverpoint, CG),
            instr,
            *([write_sigupd(rd, test_data)] if writes_rd else []),
        ]

    def hypervisor_instructions(mode: str, coverpoint: str) -> list[str]:
        """hlv.w, hlvx.wu, hsv.w, hfence.vvma and hfence.gvma; hsv.w is followed by a check of its target."""
        return [
            *trap(f"hlv.w_{mode}", coverpoint, f"hlv.w x{rd}, (x{addr_reg})"),
            *trap(f"hlvx.wu_{mode}", coverpoint, f"hlvx.wu x{rd}, (x{addr_reg})"),
            f"LI(x{rd}, 0x0BADC0DE)",
            *trap(f"hsv.w_{mode}", coverpoint, f"hsv.w x{rd}, (x{addr_reg})", writes_rd=False),
            f"lw x{rd}, 0(x{addr_reg})",
            write_sigupd(rd, test_data),
            *trap(f"hfence.vvma_{mode}", coverpoint, "hfence.vvma", writes_rd=False),
            *trap(f"hfence.gvma_{mode}", coverpoint, "hfence.gvma", writes_rd=False),
        ]

    lines = [
        comment_banner(
            "cp_virtual_instr_vs_*",
            "In VS-mode with mstatus.TVM = TW = 0: read instret(h) with hcounteren.IR = 0 and mcounteren.IR = 1;\n"
            "execute hlv.w, hlvx.wu, hsv.w, hfence.vvma and hfence.gvma; read vstval, htval, vsatp and hgatp;\n"
            "execute sret with hstatus.VTSR = 1; execute sfence.vma and sinval.vma and read satp with\n"
            "hstatus.VTVM = 1; on RV32 read hedelegh.  Each raises virtual instruction",
        ),
        "RVTEST_TSBI_CSR_CLEAR(CSR_MSTATUS, MSTATUS_TVM | MSTATUS_TW)",
        "RVTEST_TSBI_CSR_SET(CSR_MCOUNTEREN, MCOUNTEREN_IR)",
        "csrw hedeleg, zero",
        f"csrr x{save_reg}, hcounteren",
        "csrci hcounteren, MCOUNTEREN_IR",
        f"LI(x{temp_reg}, HSTATUS_VTSR | HSTATUS_VTVM)",
        f"csrs hstatus, x{temp_reg}",
        *gated(list(P1P13_ON), HEDELEGH_GATE),
        f"LA(x{addr_reg}, scratch)",
        "RVTEST_TSBI_GOTO_VSMODE",
        *gated(
            [
                *trap("instret", "cp_virtual_instr_vs_instret", f"csrr x{rd}, instret"),
                *gated(
                    trap("instreth", "cp_virtual_instr_vs_rv32_instreth_mcounter", f"csrr x{rd}, instreth"),
                    "__riscv_xlen == 32",
                ),
            ],
            "defined(ZICNTR_SUPPORTED)",
        ),
        *hypervisor_instructions("vs", "cp_virtual_instr_vs_execute_hypervisor"),
        *trap("vstval", "cp_virtual_instr_vs_read_vstval_htval", f"csrr x{rd}, vstval"),
        *trap("htval", "cp_virtual_instr_vs_read_vstval_htval", f"csrr x{rd}, htval"),
        *trap("vsatp", "cp_virtual_instr_vs_mstatus_vsatp", f"csrr x{rd}, vsatp"),
        *trap("hgatp", "cp_virtual_instr_vs_mstatus_hgatp", f"csrr x{rd}, hgatp"),
        *trap("sret", "cp_virtual_instr_vs_sret", "sret", writes_rd=False),
        *trap("sfence.vma", "cp_virtual_instr_vs_s_vma_instr", "sfence.vma", writes_rd=False),
        *gated(
            [
                test_data.add_testcase("sinval.vma", "cp_virtual_instr_vs_s_vma_instr", CG),
                *arch_block(["sinval.vma x0, x0"], "Svinval"),
            ],
            "defined(SVINVAL_SUPPORTED)",
        ),
        *trap("satp", "cp_virtual_instr_vs_satp", f"csrr x{rd}, satp"),
        *gated(trap("hedelegh", "cp_virtual_instr_vs_rv32_hedelegh", f"csrr x{rd}, hedelegh"), HEDELEGH_GATE),
        "RVTEST_TSBI_GOTO_SMODE",
        f"LI(x{temp_reg}, HSTATUS_VTSR | HSTATUS_VTVM)",
        f"csrc hstatus, x{temp_reg}",
        comment_banner(
            "cp_virtual_instr_vs_wfi",
            "With nothing pending, WFI in VS-mode with hstatus.VTW = 1 and mstatus.TW = 0 raises virtual instruction\n"
            "unless the implementation lets WFI complete at once",
        ),
        # TODO: WFI_TRAP_ON_TIMEOUT_BEHAVIOR is a proposed riscv-unified-db parameter (link the UDB issue here).
        # Until a configuration defines it, this case is not assembled.
        *gated(
            [
                f"LI(x{temp_reg}, HSTATUS_VTW)",
                f"csrs hstatus, x{temp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                *trap("wfi", "cp_virtual_instr_vs_wfi", "wfi", writes_rd=False),
                "RVTEST_TSBI_GOTO_SMODE",
                f"csrc hstatus, x{temp_reg}",
            ],
            "defined(UDB_WFI_TRAP_ON_TIMEOUT_BEHAVIOR_ALWAYS_TRAP) || "
            "defined(UDB_WFI_TRAP_ON_TIMEOUT_BEHAVIOR_TRAP_ON_TIMEOUT)",
        ),
        comment_banner(
            "cp_virtual_instr_vu_*",
            "In VU-mode with mstatus.TVM = TW = 0: read instret(h) with hcounteren.IR or scounteren.IR = 0 and\n"
            "mcounteren.IR = 1; execute hlv.w, hlvx.wu, hsv.w, hfence.vvma and hfence.gvma; read vstval, htval,\n"
            "stval, satp and vsatp; execute wfi, sret and sfence.vma; on RV32 read hedelegh.  Each raises\n"
            "virtual instruction",
        ),
        "csrsi scounteren, MCOUNTEREN_IR",
        "RVTEST_TSBI_GOTO_VUMODE",
        *gated(
            [
                *trap("instret_1", "cp_virtual_instr_vu_instret_1", f"csrr x{rd}, instret"),
                *gated(
                    trap("instreth_1", "cp_virtual_instr_vu_rv32_instreth_1", f"csrr x{rd}, instreth"),
                    "__riscv_xlen == 32",
                ),
                "RVTEST_TSBI_GOTO_SMODE",
                "csrsi hcounteren, MCOUNTEREN_IR",
                "csrci scounteren, MCOUNTEREN_IR",
                "RVTEST_TSBI_GOTO_VUMODE",
                *trap("instret_2", "cp_virtual_instr_vu_instret_2", f"csrr x{rd}, instret"),
                *gated(
                    trap("instreth_2", "cp_virtual_instr_vu_rv32_instreth_2", f"csrr x{rd}, instreth"),
                    "__riscv_xlen == 32",
                ),
            ],
            "defined(ZICNTR_SUPPORTED)",
        ),
        *hypervisor_instructions("vu", "cp_virtual_instr_vu_execute_h"),
        *trap("vstval", "cp_virtual_instr_vu_read_vstval_htval", f"csrr x{rd}, vstval"),
        *trap("htval", "cp_virtual_instr_vu_read_vstval_htval", f"csrr x{rd}, htval"),
        *trap("stval", "cp_virtual_instr_vu_read_stval", f"csrr x{rd}, stval"),
        *trap("satp", "cp_virtual_instr_vu_satp", f"csrr x{rd}, satp"),
        *trap("vsatp", "cp_virtual_instr_vu_vsatp", f"csrr x{rd}, vsatp"),
        *trap("wfi", "cp_virtual_instr_vu_wfi", "wfi", writes_rd=False),
        *trap("sret", "cp_virtual_instr_vu_sret", "sret", writes_rd=False),
        *trap("sfence.vma", "cp_virtual_instr_vu_sfence_vma", "sfence.vma", writes_rd=False),
        *gated(trap("hedelegh", "cp_virtual_instr_vu_rv32_hedelegh", f"csrr x{rd}, hedelegh"), HEDELEGH_GATE),
        "RVTEST_TSBI_GOTO_SMODE",
        *gated(list(P1P13_OFF), HEDELEGH_GATE),
        "csrsi scounteren, MCOUNTEREN_IR",
        f"csrw hcounteren, x{save_reg}",
    ]
    test_data.int_regs.return_registers([addr_reg, rd, save_reg, temp_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsH",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_exceptionsh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the ExceptionsH hypervisor exception testsuite."""
    test_chunks: list[TestChunk] = []
    # hedeleg matters only for traps from VS and VU; traps from HS and U ignore even all of its writable bits
    for mode, values in (
        ("s", (HEDELEG_WRITABLE,)),
        ("vs", HEDELEG_WALK),
        ("u", (HEDELEG_WRITABLE,)),
        ("vu", HEDELEG_WALK),
    ):
        tc = test_data.new_test_chunk(test_chunks, f"hedeleg_{mode}")
        tc.code.extend(hedeleg_tests(test_data, CG, mode, "s", values))
        tc.trap_sigupd_count = trap_sigupd_count(len(values) * DELEGATED_FAULTS)

    tc = test_data.new_test_chunk(test_chunks, "ecall")
    tc.code.extend(_ecall_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "virtual")
    tc.code.extend(_virtual_instruction_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "hlv")
    for mode in ("s", "vs", "u", "vu"):
        tc.code.extend(hlv_priority_tests(test_data, CG, mode, "s"))

    tc = test_data.new_test_chunk(test_chunks, "xtinst")
    tc.code.extend(xtinst_exception_tests(test_data, CG, "s"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
