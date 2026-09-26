##################################
# priv/extensions/SstcCommon.py
#
# Shared Sstc test generation for SstcSm, Sstc, SstcHSm and SstcH.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc helpers and tests shared by SstcSm, Sstc, SstcHSm and SstcH.

``mode`` is "machine", "supervisor" (S-mode or HS-mode) or "user", as in the coverpoint names.  M-mode CSRs are written
directly in machine mode and through T-SBI otherwise; user-mode tests are entered from S-mode with
RVTEST_TSBI_GOTO_UMODE.
"""

from itertools import product

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData


def csr_op(instr: str, mode: str) -> str:
    """An M-mode CSR instruction, issued directly in machine mode and through T-SBI otherwise."""
    return instr if mode == "machine" else tsbi_call(instr)


def mcounteren_tm(test_data: TestData, enable: bool, mode: str) -> list[str]:
    """Set or clear mcounteren.TM."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, MCOUNTEREN_TIME)", csr_op(f"{'csrs' if enable else 'csrc'} mcounteren, x{reg}", mode)]
    test_data.int_regs.return_register(reg)
    return lines


def menvcfg_stce(test_data: TestData, enable: bool, mode: str) -> list[str]:
    """Set or clear menvcfg.STCE (menvcfgh on RV32)."""
    op = "csrs" if enable else "csrc"
    reg = test_data.int_regs.get_register()
    lines = [
        f"# {'Enable' if enable else 'Disable'} menvcfg.STCE{'' if mode == 'machine' else ' via T-SBI'}",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, MENVCFG_STCE)",
        csr_op(f"{op} menvcfg, x{reg}", mode),
        "#else",
        f"LI(x{reg}, MENVCFGH_STCE)",
        csr_op(f"{op} menvcfgh, x{reg}", mode),
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def stce_tm(test_data: TestData, m_stce: int, h_stce: int, m_tm: int, h_tm: int, mode: str) -> list[str]:
    """Write menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM from M-mode (machine) or HS-mode (supervisor).

    henvcfg follows menvcfg because henvcfg.STCE is read-only zero while menvcfg.STCE = 0.
    """
    op = "csrs" if h_stce else "csrc"
    reg = test_data.int_regs.get_register()
    lines = [
        *menvcfg_stce(test_data, bool(m_stce), mode),
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, HENVCFG_STCE)",
        f"{op} henvcfg, x{reg}",
        "#else",
        f"LI(x{reg}, HENVCFGH_STCE)",
        f"{op} henvcfgh, x{reg}",
        "#endif",
        *mcounteren_tm(test_data, bool(m_tm), mode),
        f"LI(x{reg}, MCOUNTEREN_TIME)",
        f"{'csrs' if h_tm else 'csrc'} hcounteren, x{reg}",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def rv32_only(csr: str, lines: list[str]) -> list[str]:
    """Wrap lines for an upper-half CSR in #if __riscv_xlen == 32."""
    return ["#if __riscv_xlen == 32", *lines, "#endif"] if csr.endswith("h") else lines


def access_cross(test_data: TestData, coverpoint: str, covergroup: str, mode: str, csrs: list[str]) -> list[str]:
    """Read each CSR in mode (m, hs, vs, vu or u) for every value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM
    and hcounteren.TM.  Mode m is in SstcHSm, which boots to M-mode; the others are in SstcH, which boots to
    HS-mode.  henvcfg.STCE = 1 with menvcfg.STCE = 0 is skipped because henvcfg.STCE is read-only zero then."""
    rd = test_data.int_regs.get_register()
    boot = "machine" if mode == "m" else "supervisor"
    lower = mode not in ("m", "hs")
    lines = []
    for m_stce, h_stce, m_tm, h_tm in product((0, 1), repeat=4):
        if h_stce > m_stce:
            continue
        lines.extend(stce_tm(test_data, m_stce, h_stce, m_tm, h_tm, boot))
        lines.extend([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if lower else [])
        for csr in csrs:
            bin_name = f"{csr}_mstce{m_stce}_hstce{h_stce}_mtm{m_tm}_htm{h_tm}"
            lines.extend(
                rv32_only(
                    csr,
                    [
                        f"LI(x{rd}, 42)",
                        test_data.add_testcase(bin_name, coverpoint, covergroup),
                        f"csrr x{rd}, {csr}",
                        write_sigupd(rd, test_data),
                    ],
                )
            )
        lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if lower else [])
    lines.extend(stce_tm(test_data, 0, 0, 1, 1, boot))
    test_data.int_regs.return_register(rd)
    return lines


def wait_for_trap(count_reg: int, tmp_reg: int) -> list[str]:
    """Wait until the trap handler has counted another trap, such as a timer interrupt armed to fire soon."""
    return [
        f"LA(x{count_reg}, rvtest_trap_count)",
        f"LREG x{count_reg}, 0(x{count_reg})",
        "1:",
        f"LA(x{tmp_reg}, rvtest_trap_count)",
        f"LREG x{tmp_reg}, 0(x{tmp_reg})",
        f"beq x{tmp_reg}, x{count_reg}, 1b",
    ]


def vstimecmp_int_tests(test_data: TestData, covergroup: str, boot: str) -> list[str]:
    """Arm vstimecmp in the boot mode (machine or supervisor) at once or soon, with hie.VSTIE = 1 and hideleg.VSTI = 0/1.

    VS-mode takes STI when hideleg.VSTI = 1.  HS-mode takes VSTI otherwise: in HS-mode with sstatus.SIE = 1 when
    the suite boots to HS-mode, else in VS-mode.
    """
    priv = "M" if boot == "machine" else "S"
    tmp_reg, count_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_vstimecmp_int",
            f"With STCE = 1 and hie.VSTIE = 1, arm vstimecmp in {'M' if boot == 'machine' else 'HS'}-mode at once "
            "(vstimecmp = 0) or soon\n(time + htimedelta + delay).  VS-mode takes STI with hideleg.VSTI = 1; "
            "HS-mode takes VSTI with\n"
            f"hideleg.VSTI = 0, {'in VS-mode' if boot == 'machine' else 'in HS-mode with sstatus.SIE = 1'}",
        ),
        *stce_tm(test_data, 1, 1, 1, 1, boot),
        "csrw hvip, zero",
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrs vsstatus, x{tmp_reg}",
    ]
    for deleg, soon in product((0, 1), (False, True)):
        in_hs = boot == "supervisor" and not deleg
        lines.extend(
            [
                f"LI(x{tmp_reg}, MIP_VSTIP)",
                f"csrw hie, x{tmp_reg}",
                f"LI(x{tmp_reg}, {'MIP_VSTIP' if deleg else 0})",
                f"csrw hideleg, x{tmp_reg}",
                *(["csrsi sstatus, SSTATUS_SIE"] if in_hs else []),
                test_data.add_testcase(f"hideleg{deleg}{'_soon' if soon else ''}", "cp_vstimecmp_int", covergroup),
                f"RVTEST_SET_VSSTC_INT{'_SOON' if soon else ''}_{priv}",
                *([] if in_hs else ["RVTEST_TSBI_GOTO_VSMODE"]),
                *(wait_for_trap(count_reg, tmp_reg) if soon else [f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})"]),
                "csrci sstatus, SSTATUS_SIE" if in_hs else f"RVTEST_TSBI_GOTO_{priv}MODE",
                f"RVTEST_CLR_VSSTC_INT_{priv}",
            ]
        )
    lines.extend(["csrw hideleg, zero", "csrw hie, zero", *stce_tm(test_data, 0, 0, 1, 1, boot)])
    test_data.int_regs.return_registers([tmp_reg, count_reg])
    return lines


def access_stimecmp(test_data: TestData) -> list[str]:
    """Read stimecmp, and stimecmph on RV32, to check whether the reads are permitted; the values are discarded."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"csrr x{reg}, stimecmp",
        "#if __riscv_xlen == 32",
        f"csrr x{reg}, stimecmph",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def tm_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with mcounteren.TM = 0/1 and STCE = 1; user mode also crosses scounteren.TM = 0/1.

    Below M-mode, TM = 0 makes the read trap; coverage is sampled at the csrr before the trap.  The suite rests
    with mcounteren.TM = scounteren.TM = 1 and STCE = 0, and these tests restore that state.
    """
    coverpoint = f"cp_{mode}_tm"
    user = mode == "user"
    lines = [
        comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: mcounteren.TM = 0/1, STCE = 1"),
        "",
        *menvcfg_stce(test_data, True, mode),
    ]
    for tm_val in (0, 1):
        lines += mcounteren_tm(test_data, bool(tm_val), mode)
        for stm_val in (1, 0) if user else (1,):
            lines += [
                "",
                f"# {coverpoint}: TM = {tm_val}" + (f", scounteren.TM = {stm_val}" if user else ""),
                *([] if stm_val else ["csrci scounteren, 0x2"]),
                *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
                test_data.add_testcase(f"tm{tm_val}_stm{stm_val}" if user else f"tm{tm_val}", coverpoint, covergroup),
                *access_stimecmp(test_data),
                *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
                *([] if stm_val else ["csrsi scounteren, 0x2"]),
            ]
    return [*lines, "", *menvcfg_stce(test_data, False, mode)]


def stce_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with menvcfg.STCE = 0/1; mcounteren.TM = scounteren.TM = 1 from the suite's resting state.

    Below M-mode, STCE = 0 makes the read trap; coverage is sampled at the csrr before the trap.
    """
    coverpoint = f"cp_{mode}_stce"
    user = mode == "user"
    lines = [comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: menvcfg.STCE = 0/1"), ""]
    for stce_val in (0, 1):
        lines += [
            "",
            f"# {coverpoint}: STCE = {stce_val}",
            *menvcfg_stce(test_data, bool(stce_val), mode),
            *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
            test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup),
            *access_stimecmp(test_data),
            *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
        ]
    return [*lines, "", *menvcfg_stce(test_data, False, mode)]
