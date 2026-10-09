##################################
# priv/extensions/ZicntrCommon.py
#
# Shared Zicntr test generation for the Sm/S/U counter-enable suites.
# David_Harris@hmc.edu 30 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zicntr counter-enable tests in all priv modes"""

from typing import Literal

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData

Mode = Literal["M", "S", "U"]
Counteren = Literal["ones", "zeros"]

_COUNTERS = ["cycle", "time", "instret"]


def _access_counter(
    test_data: TestData, covergroup: str, coverpoint: str, bin_prefix: str, read_reg: int, i: int
) -> list[str]:
    """Read counter i and attempt to write it, low half and high half on RV32.

    The read traps or not according to mcounteren and scounteren; the write always raises an illegal
    instruction, because the unprivileged counters are read-only CSRs.
    """

    def access(name: str, suffix: str) -> list[str]:
        return [
            test_data.add_testcase(f"{bin_prefix}_read{suffix}", coverpoint, covergroup),
            f"csrr x{read_reg}, {name}",
            test_data.add_testcase(f"{bin_prefix}_write{suffix}", coverpoint, covergroup),
            f"csrw {name}, zero  # read-only CSR: illegal instruction whatever the counterens hold",
        ]

    if i < 3:
        name = _COUNTERS[i]
        return [
            *access(name, ""),
            "#if __riscv_xlen == 32",
            *access(f"{name}h", "h"),
            "#endif",
        ]
    # Access only the hpmcounters the configuration implements: an unimplemented counter may trap or
    # return a constant (norm:hpm_unimplemented_counter_access), so no reference signature fits both.
    # UDB_HPM_COUNTER_EN_<n> comes from the HPM_COUNTER_EN parameter of the UDB config.
    return [
        f"#if defined(ZIHPM_SUPPORTED) && defined(UDB_HPM_COUNTER_EN_{i})",
        *access(f"hpmcounter{i}", ""),
        "#if __riscv_xlen == 32",
        *access(f"hpmcounter{i}h", "h"),
        "#endif",
        "#endif",
    ]


def _write_counteren(csr: str, operand: str, mode: Mode, comment: str = "") -> str:
    """Write csr directly when mode can, otherwise through T-SBI: mcounteren is M-mode only,
    scounteren is writable from M and S."""
    instr = f"csrw {csr}, {operand}"
    if comment:
        instr += f"  # {comment}"
    return tsbi_call_or_direct(instr, mode)


def counteren_walk_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    *,
    csrs: list[str],
    mode: Mode,
    mcounteren: Counteren | None = None,
    scounteren_ones: bool = False,
    tag: str = "",
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading
    every counter after each write. Everything runs in mode; writes that mode cannot make directly
    go through T-SBI. mcounteren optionally presets that register to all ones or all zeros first, and
    scounteren_ones presets scounteren to all ones when S-mode exists.
    tag prefixes the testcase names so a coverpoint tested with several mcounteren settings stays unique.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = [comment_banner(coverpoint, description), ""]
    if scounteren_ones:
        lines += [
            "#ifdef S_SUPPORTED",
            f"LI(x{ones_reg}, -1)",
            _write_counteren("scounteren", f"x{ones_reg}", mode, "enable all counters for U-mode"),
            "#endif // S_SUPPORTED",
        ]
    if mcounteren == "ones":
        lines += [
            f"LI(x{ones_reg}, -1)",
            _write_counteren("mcounteren", f"x{ones_reg}", mode, "enable all counters"),
        ]
    elif mcounteren == "zeros":
        lines.append(_write_counteren("mcounteren", "zero", mode, "disable all counters"))

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            *(_write_counteren(csr, f"x{walk_reg}", mode, "set only the current bit") for csr in csrs),
            *_access_counter(test_data, covergroup, coverpoint, f"{tag}walking_1_{i}", read_reg, i),
            f"slli x{walk_reg}, x{walk_reg}, 1",
        ]

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            f"not x{inv_reg}, x{walk_reg}  # all bits but the current one",
            *(_write_counteren(csr, f"x{inv_reg}", mode, "clear only the current bit") for csr in csrs),
            *_access_counter(test_data, covergroup, coverpoint, f"{tag}walking_0_{i}", read_reg, i),
            f"slli x{walk_reg}, x{walk_reg}, 1",
        ]
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg, inv_reg])
    return lines


def _set_counterens(operand: str, mode: Mode) -> list[str]:
    """Write mcounteren, plus scounteren when it also gates the running mode."""
    lines = [_write_counteren("mcounteren", operand, mode)]
    if mode == "U":
        lines += ["#ifdef S_SUPPORTED", _write_counteren("scounteren", operand, mode), "#endif"]
    return lines


def counter_inc_inaccessible_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Check that instret keeps counting while it is inaccessible in mode."""
    coverpoint = "cp_mcounter_inc_inaccessible"
    description = (
        f"running in {mode} mode\n"
        "enable counters and read instret\n"
        f"disable counters so instret is inaccessible in {mode} mode\n"
        "re-enable counters; the instructions doing so retire while instret is inaccessible\n"
        "read and sigupd change in instret"
    )

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, description),
        "",
        test_data.add_testcase(mode, coverpoint, covergroup),
        f"# make counter accessible in {mode} mode",
        f"LI(x{read_reg}, -1)",
        *_set_counterens(f"x{read_reg}", mode),
        f"csrr x{old_reg}, instret",
        f"# make counter inaccessible in {mode} mode",
        *_set_counterens("zero", mode),
        f"# make counter accessible in {mode} mode",
        *_set_counterens(f"x{read_reg}", mode),
        f"csrr x{read_reg}, instret",
        f"sub x{read_reg}, x{read_reg}, x{old_reg}",
        "# SIGUPD the difference in instret",
        write_sigupd(read_reg, test_data),
    ]
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines


def _counter_prep(test_data: TestData, mode: Mode) -> list[str]:
    """Start the counters and, in U-mode, make them readable."""
    lines = [
        "#ifdef UDB_MCOUNTINHIBIT_IMPLEMENTED",
        tsbi_call_or_direct("csrw mcountinhibit, zero  # run all counters", mode),
        "#endif // UDB_MCOUNTINHIBIT_IMPLEMENTED",
    ]
    if mode == "U":
        (r_tmp,) = test_data.int_regs.get_registers(1)
        lines += [f"LI(x{r_tmp}, -1)", *_set_counterens(f"x{r_tmp}", mode)]
        test_data.int_regs.return_registers([r_tmp])
    return lines


def _instret_case(
    test_data: TestData,
    covergroup: str,
    name: str,
    mode: Mode,
    body: list[str],
    *,
    setup: list[str] | None = None,
    cleanup: list[str] | None = None,
) -> list[str]:
    """Read the counter before and after body and sigupd the delta."""
    r_before, r_after, r_diff = test_data.int_regs.get_registers(3)
    counter = "instret" if mode == "U" else "minstret"
    lines = [
        *(setup or []),
        test_data.add_testcase(f"{counter}_{name}", f"cp_instret_{name}", covergroup),
        f"csrr x{r_before}, {counter}",
        *body,
        f"csrr x{r_after}, {counter}",
        f"sub x{r_diff}, x{r_after}, x{r_before}",
        write_sigupd(r_diff, test_data),
        *(cleanup or []),
        "",
    ]
    test_data.int_regs.return_registers([r_before, r_after, r_diff])
    return lines


def _instret_wait_case(test_data: TestData, covergroup: str, name: str, mode: Mode, wait: str) -> list[str]:
    """Delta around a wait instruction (wfi) that a timer interrupt ends."""
    csr = "instret" if mode == "U" else "minstret"
    r_before, r_after, r_diff = test_data.int_regs.get_registers(3)
    r_count, r_addr = test_data.int_regs.get_registers(2)

    trip = [
        f"LREG x{r_after}, 0(x{r_addr})  # trap count now",
        f"bne x{r_after}, x{r_count}, 2f  # interrupt taken: leave the loop",
        wait,
    ]
    insns_per_trip = len(trip) + 2  # plus the addi and j below

    lines = [
        tsbi_call_or_direct("csrw mie, zero", mode),
        *(["csrci mstatus, 8  # MIE = 0"] if mode == "M" else []),
        f"LI(x{r_after}, 0x80)",
        tsbi_call_or_direct(f"csrw mie, x{r_after}  # MTIE only", mode),
        f"RVTEST_SET_MTIME_INT_SOON_{mode}",
        # Sampled after the last setup trap, so only the timer interrupt can change it
        f"LA(x{r_addr}, rvtest_trap_count)",
        f"LREG x{r_count}, 0(x{r_addr})  # trap count before waiting",
        f"LI(x{r_diff}, 0)  # tally of instructions retired by the loop",
        *(["csrsi mstatus, 8  # MIE = 1"] if mode == "M" else []),
        test_data.add_testcase(f"{csr}_{name}", f"cp_instret_{name}", covergroup),
        f"csrr x{r_before}, {csr}",
        "1:",
        *trip,
        f"addi x{r_diff}, x{r_diff}, {insns_per_trip}  # tally this trip",
        "j 1b",
        "2:",
        f"csrr x{r_after}, {csr}",
        f"sub x{r_after}, x{r_after}, x{r_diff}  # remove the timing-dependent part",
        f"sub x{r_diff}, x{r_after}, x{r_before}",
        write_sigupd(r_diff, test_data),
        *(["csrci mstatus, 8  # MIE = 0"] if mode == "M" else []),
        f"RVTEST_CLR_MTIME_INT_{mode}",
        "",
    ]
    test_data.int_regs.return_registers([r_before, r_after, r_diff, r_count, r_addr])
    return lines


def instret_retire_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Normally retiring instructions: add (M, U), mret and sret (M only)."""
    assert mode in ("M", "U")
    csr = "instret" if mode == "U" else "minstret"
    lines = _counter_prep(test_data, mode)

    (r_tmp,) = test_data.int_regs.get_registers(1)
    lines += [
        comment_banner("cp_instret_add", f"{csr} delta around add in {mode}-mode"),
        "",
        *_instret_case(test_data, covergroup, "add", mode, [f"add x{r_tmp}, zero, zero  # instruction under test"]),
    ]
    test_data.int_regs.return_registers([r_tmp])

    if mode == "M":
        r_save, r_mask = test_data.int_regs.get_registers(2)
        lines += [
            comment_banner("cp_instret_mret", "minstret delta around mret (MPP = M)"),
            "",
            *_instret_case(
                test_data,
                covergroup,
                "mret",
                mode,
                ["mret  # instruction under test", "1:"],
                setup=[
                    f"csrr x{r_save}, mstatus",
                    f"LI(x{r_mask}, 0x1800)  # MPP = M",
                    f"or x{r_mask}, x{r_mask}, x{r_save}",
                    f"csrw mstatus, x{r_mask}",
                    f"LA(x{r_mask}, 1f)",
                    f"csrw mepc, x{r_mask}",
                ],
                cleanup=[f"csrw mstatus, x{r_save}"],
            ),
        ]
        test_data.int_regs.return_registers([r_save, r_mask])

        # sret returns to U-mode, so T-SBI goes back to M before minstret is read
        r_save, r_tmp = test_data.int_regs.get_registers(2)
        lines += [
            "#ifdef S_SUPPORTED",
            comment_banner("cp_instret_sret", "minstret delta around sret (SPP = U, T-SBI back to M)"),
            "",
            *_instret_case(
                test_data,
                covergroup,
                "sret",
                mode,
                [
                    "sret  # instruction under test",
                    "1:",
                    "RVTEST_TSBI_GOTO_MMODE",
                ],
                setup=[
                    f"csrr x{r_save}, sstatus",
                    f"LI(x{r_tmp}, 0x100)",
                    f"csrc sstatus, x{r_tmp}  # SPP = U",
                    f"LA(x{r_tmp}, 1f)",
                    f"csrw sepc, x{r_tmp}",
                ],
                cleanup=[f"csrw sstatus, x{r_save}"],
            ),
            "#else",
            "#ifdef UDB_TIME_CSR_IMPLEMENTED",
            comment_banner(
                "cp_instret_sret_illegal", "minstret delta around sret without S-mode (illegal instruction)"
            ),
            "",
            *_instret_case(test_data, covergroup, "sret_illegal", mode, ["sret", "nop"]),
            "#endif // UDB_TIME_CSR_IMPLEMENTED",
            "#endif // S_SUPPORTED",
        ]
        test_data.int_regs.return_registers([r_save, r_tmp])

    return lines


def instret_exception_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Instructions that trap before retiring: ecall, ebreak, illegal, load access fault, load misaligned."""
    assert mode in ("M", "U")
    csr = "instret" if mode == "U" else "minstret"
    lines = _counter_prep(test_data, mode)

    lines += [
        comment_banner("cp_instret_ecall", f"ecall in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(test_data, covergroup, "ecall", mode, ["RVTEST_TSBI_ECALL_TEST"]),
        comment_banner("cp_instret_ebreak", f"ebreak in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(test_data, covergroup, "ebreak", mode, ["ebreak", "nop"]),
        # The illegal-instruction trap goes through the invisible time-emulation handler when
        # time is not implemented. Sail runs without it, so no reference value fits that DUT.
        "#ifdef UDB_TIME_CSR_IMPLEMENTED",
        comment_banner("cp_instret_illegal", f"Illegal instruction in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(test_data, covergroup, "illegal", mode, [".word 0xFFFFFFFF", "nop"], setup=[".p2align 2"]),
        "#endif // UDB_TIME_CSR_IMPLEMENTED",
    ]

    r_addr, r_tmp = test_data.int_regs.get_registers(2)
    lines += [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner("cp_instret_load_access_fault", f"Load access fault in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(
            test_data,
            covergroup,
            "load_access_fault",
            mode,
            [f"lw x{r_tmp}, 0(x{r_addr})"],
            setup=[f"LA(x{r_addr}, RVMODEL_ACCESS_FAULT_ADDRESS)"],
        ),
        "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
        "",
        comment_banner("cp_instret_load_misaligned", f"Load address misaligned in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(
            test_data,
            covergroup,
            "load_misaligned",
            mode,
            [f"lw x{r_tmp}, 0(x{r_addr})"],
            setup=[f"LA(x{r_addr}, scratch)", f"addi x{r_addr}, x{r_addr}, 1  # misalign by 1 byte"],
        ),
    ]
    test_data.int_regs.return_registers([r_addr, r_tmp])
    return lines


def instret_interrupt_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """wfi and wrs cases in M-mode (minstret) or U-mode (instret),

    wfi_taken goes through _instret_wait_case; wfi_timeout, wfi_pending, wrs_nto and wrs_sto
    record the raw delta through _instret_case.
    """

    assert mode in ("M", "U")
    csr = "instret" if mode == "U" else "minstret"
    lines = _counter_prep(test_data, mode)
    if mode == "U":
        (r_tmp,) = test_data.int_regs.get_registers(1)
        lines += [f"LI(x{r_tmp}, 0x200000)", tsbi_call_or_direct(f"csrc mstatus, x{r_tmp}  # mstatus.TW = 0", mode)]
        test_data.int_regs.return_registers([r_tmp])

    cond = "defined(UDB_WFI_FINITE)" + (" && defined(UDB_WFI_U_MODE)" if mode == "U" else "")
    lines += [
        f"#if {cond}",
        comment_banner("cp_instret_wfi_timeout", f"wfi in {mode}-mode with nothing armed: {csr} delta recorded"),
        "",
        *_instret_case(
            test_data,
            covergroup,
            "wfi_timeout",
            mode,
            ["wfi  # no event armed", *(["nop"] if mode == "U" else [])],
            setup=[
                tsbi_call_or_direct("csrw mie, zero", mode),
                *(["csrci mstatus, 8  # MIE = 0"] if mode == "M" else []),
                f"RVTEST_CLR_MTIME_INT_{mode}",
            ],
        ),
        f"#endif // {cond}",
        "",
    ]

    if mode == "M":
        (r_tmp,) = test_data.int_regs.get_registers(1)
        lines += [
            comment_banner("cp_instret_wfi_pending", "wfi with timer interrupt pending and MIE = 0: no trap."),
            "",
            *_instret_case(
                test_data,
                covergroup,
                "wfi_pending",
                mode,
                ["wfi  # already pending, not taken"],
                setup=[
                    tsbi_call_or_direct("csrw mie, zero", mode),
                    "csrci mstatus, 8  # MIE = 0",
                    f"LI(x{r_tmp}, 0x80)",
                    tsbi_call_or_direct(f"csrw mie, x{r_tmp}  # MTIE only", mode),
                    "RVTEST_SET_MTIME_INT_SOON_M",
                    "1:",
                    f"csrr x{r_tmp}, mip",
                    f"andi x{r_tmp}, x{r_tmp}, 0x80  # mip.MTIP",
                    f"beqz x{r_tmp}, 1b  # wait until MTIP is really pending",
                ],
                cleanup=["RVTEST_CLR_MTIME_INT_M"],
            ),
        ]
        test_data.int_regs.return_registers([r_tmp])

    if mode == "U":
        lines.append("#ifdef UDB_WFI_U_MODE")
    lines += [
        comment_banner("cp_instret_wfi_taken", f"wfi in {mode}-mode: timer interrupt taken, {csr} delta recorded"),
        "",
        *_instret_wait_case(test_data, covergroup, "wfi_taken", mode, "wfi"),
    ]
    if mode == "U":
        lines.append("#endif // UDB_WFI_U_MODE")

    lines += [
        "#ifdef ZAWRS_SUPPORTED",
        comment_banner(
            "cp_instret_wrs_nto", f"wrs.nto in {mode}-mode, no reservation: does not stall, {csr} delta recorded"
        ),
        "",
        *_instret_case(
            test_data,
            covergroup,
            "wrs_nto",
            mode,
            ["wrs.nto  # instruction under test"],
            setup=[tsbi_call_or_direct("csrw mie, zero", mode)],
        ),
        comment_banner("cp_instret_wrs_sto", f"wrs.sto in {mode}-mode: short stall, {csr} delta recorded"),
        "",
        *_instret_case(
            test_data,
            covergroup,
            "wrs_sto",
            mode,
            ["wrs.sto  # instruction under test"],
            setup=[tsbi_call_or_direct("csrw mie, zero", mode)],
        ),
        "#endif // ZAWRS_SUPPORTED",
    ]
    return lines
