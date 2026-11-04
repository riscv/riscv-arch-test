##################################
# priv/extensions/ZicntrCommon.py
#
# Shared Zicntr test generation: counter-enable walks, htimedelta reads and instret retirement.
# David_Harris@hmc.edu 30 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zicntr counter-enable and instret retirement tests in all priv modes"""

from typing import Literal

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner, write64_csr, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.priv.extensions.PrivCommon import HTIMEDELTAS, read_time

Mode = Literal["M", "S", "U", "VS", "VU"]
Counteren = Literal["ones", "zeros"]

_COUNTERS = ["cycle", "time", "instret"]


def _access_counter(
    test_data: TestData, covergroup: str, coverpoint: str, bin_prefix: str, read_reg: int, i: int
) -> list[str]:
    """Read counter i and attempt to write it, low half and high half on RV32.

    The read traps or not according to the counter-enable registers; the write always raises an illegal
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
    """Write csr directly when mode can, otherwise through T-SBI."""
    instr = f"csrw {csr}, {operand}"
    if comment:
        instr += f"  # {comment}"
    return tsbi_call_or_direct(instr, mode)


def _preset_counteren(csr: str, setting: Counteren, mode: Mode, reg: int) -> list[str]:
    """Write all ones or all zeros to csr."""
    if setting == "zeros":
        return [_write_counteren(csr, "zero", mode, "disable all counters")]
    return [f"LI(x{reg}, -1)", _write_counteren(csr, f"x{reg}", mode, "enable all counters")]


def counteren_walk_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    *,
    csrs: list[str],
    mode: Mode,
    mcounteren: Counteren | None = None,
    hcounteren: Counteren | None = None,
    scounteren: Counteren | None = None,
    tag: str = "",
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading
    every counter after each write. Everything runs in mode; writes that mode cannot make directly
    go through T-SBI. mcounteren, hcounteren and scounteren optionally preset those registers to all
    ones or all zeros first; scounteren only when S-mode exists.
    tag prefixes the testcase names so a coverpoint tested with several mcounteren settings stays unique.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = [comment_banner(coverpoint, description), ""]
    if scounteren is not None:
        lines += [
            "#ifdef S_SUPPORTED",
            *_preset_counteren("scounteren", scounteren, mode, ones_reg),
            "#endif // S_SUPPORTED",
        ]
    presets: tuple[tuple[str, Counteren | None], ...] = (("mcounteren", mcounteren), ("hcounteren", hcounteren))
    for csr, setting in presets:
        if setting is not None:
            lines += _preset_counteren(csr, setting, mode, ones_reg)

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


def htimedelta_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Read time in mode for each htimedelta.

    VS and VU read time + htimedelta; M, HS and U read time; each read must be within 2^30 of a baseline read.
    """
    coverpoint = f"cp_delta_{'hs' if mode == 'S' else mode.lower()}"
    virtual = mode in ("VS", "VU")
    lower = mode in ("U", "VS", "VU")
    base_lo, base_hi, val_lo, val_hi, tmp = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(
            coverpoint,
            "With htimedelta = {0, 2^30, 2^32-1, 2^60, -1, -2^30, -2^60}, read time (and timeh on RV32) in "
            f"{'HS' if mode == 'S' else mode}-mode.\n"
            + ("It reads time + htimedelta." if virtual else "It reads time, unaffected by htimedelta."),
        ),
    ]
    for name, delta in HTIMEDELTAS.items():
        expected = delta & ((1 << 64) - 1) if virtual else 0
        lines.extend(
            [
                *write64_csr("htimedelta", 0, tmp),
                *read_time(base_lo, base_hi, tmp),
                *write64_csr("htimedelta", delta, tmp),
                *([f"RVTEST_TSBI_GOTO_{mode}MODE"] if lower else []),
                f"LI(x{val_lo}, 0)",
                f"LI(x{val_hi}, 0)",
                test_data.add_testcase(name, coverpoint, covergroup),
                *read_time(val_lo, val_hi, tmp),
                *(["RVTEST_TSBI_GOTO_SMODE"] if lower else []),
                "#if __riscv_xlen == 32",
                f"sltu x{tmp}, x{val_lo}, x{base_lo}",
                f"sub x{val_hi}, x{val_hi}, x{base_hi}",
                f"sub x{val_hi}, x{val_hi}, x{tmp}",
                "#endif",
                f"sub x{val_lo}, x{val_lo}, x{base_lo}    # read - baseline",
            ]
        )
        if expected:
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f"LI(x{tmp}, {expected:#x})",
                    "#else",
                    f"LI(x{tmp}, {expected >> 32:#x})",
                    f"sub x{val_hi}, x{val_hi}, x{tmp}",
                    f"LI(x{tmp}, {expected & 0xFFFFFFFF:#x})",
                    f"sltu x{base_lo}, x{val_lo}, x{tmp}",
                    f"sub x{val_hi}, x{val_hi}, x{base_lo}",
                    "#endif",
                    f"sub x{val_lo}, x{val_lo}, x{tmp}    # - htimedelta",
                ]
            )
        lines.extend(
            [
                f"srli x{val_lo}, x{val_lo}, 30",
                "#if __riscv_xlen == 32",
                f"or x{val_lo}, x{val_lo}, x{val_hi}",
                "#endif",
                f"seqz x{val_lo}, x{val_lo}    # 1 if the difference is below 2^30",
                write_sigupd(val_lo, test_data),
            ]
        )
    lines.extend(write64_csr("htimedelta", 0, tmp))
    test_data.int_regs.return_registers([base_lo, base_hi, val_lo, val_hi, tmp])
    return lines


def _counter_prep(test_data: TestData, mode: Mode) -> list[str]:
    """Start the counters and, below M-mode, make them readable."""
    lines = [
        "#ifdef UDB_MCOUNTINHIBIT_IMPLEMENTED",
        tsbi_call_or_direct("csrw mcountinhibit, zero  # run all counters", mode),
        "#endif // UDB_MCOUNTINHIBIT_IMPLEMENTED",
    ]
    if mode != "M":
        r_tmp = test_data.int_regs.get_register()
        lines += [f"LI(x{r_tmp}, -1)", *_set_counterens(f"x{r_tmp}", mode)]
        test_data.int_regs.return_register(r_tmp)
    return lines


def _instret_case(
    test_data: TestData,
    covergroup: str,
    name: str,
    mode: Mode,
    body: list[str],
) -> list[str]:
    """Read the counter before and after body and sigupd the delta."""
    r_before, r_after, r_diff = test_data.int_regs.get_registers(3)
    counter = "minstret" if mode == "M" else "instret"
    lines = [
        test_data.add_testcase(f"{counter}_{name}", f"cp_instret_{name}", covergroup),
        f"csrr x{r_before}, {counter}",
        *body,
        f"csrr x{r_after}, {counter}",
        f"sub x{r_diff}, x{r_after}, x{r_before}",
        write_sigupd(r_diff, test_data),
        "",
    ]
    test_data.int_regs.return_registers([r_before, r_after, r_diff])
    return lines


def instret_retire_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Normally retiring instructions: add, mret (M only) and sret (M and S)."""
    assert mode in ("M", "S", "U")
    csr = "minstret" if mode == "M" else "instret"
    lines = _counter_prep(test_data, mode)

    r_tmp = test_data.int_regs.get_register()
    lines += [
        comment_banner("cp_instret_add", f"{csr} delta around add in {mode}-mode"),
        "",
        *_instret_case(test_data, covergroup, "add", mode, [f"add x{r_tmp}, zero, zero  # instruction under test"]),
    ]
    test_data.int_regs.return_register(r_tmp)

    if mode == "M":
        r_save, r_mask = test_data.int_regs.get_registers(2)
        lines += [
            comment_banner("cp_instret_mret", "minstret delta around mret (MPP = M)"),
            "",
            f"csrr x{r_save}, mstatus",
            f"LI(x{r_mask}, 0x1800)  # MPP = M",
            f"or x{r_mask}, x{r_mask}, x{r_save}",
            f"csrw mstatus, x{r_mask}",
            f"LA(x{r_mask}, 1f)",
            f"csrw mepc, x{r_mask}",
            *_instret_case(test_data, covergroup, "mret", mode, ["mret  # instruction under test", "1:"]),
            f"csrw mstatus, x{r_save}",
        ]
        test_data.int_regs.return_registers([r_save, r_mask])

        lines += ["#ifdef S_SUPPORTED", *_instret_sret_case(test_data, covergroup, mode), "#endif // S_SUPPORTED"]
    elif mode == "S":
        lines += _instret_sret_case(test_data, covergroup, mode)

    return lines


def _instret_sret_case(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """sret returns to U-mode: read instret there, then T-SBI back to ``mode``."""
    csr = "minstret" if mode == "M" else "instret"
    r_save, r_tmp, r_before, r_after, r_diff = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner("cp_instret_sret", f"{csr} delta around sret (SPP = U)"),
        "",
        f"csrr x{r_save}, sstatus",
        f"LI(x{r_tmp}, 0x100)",
        f"csrc sstatus, x{r_tmp}  # SPP = U",
        f"LA(x{r_tmp}, 1f)",
        f"csrw sepc, x{r_tmp}",
        f"LI(x{r_tmp}, -1)",
        _write_counteren("mcounteren", f"x{r_tmp}", mode, "instret readable from U-mode"),
        f"csrw scounteren, x{r_tmp}",
        test_data.add_testcase(f"{csr}_sret", "cp_instret_sret", covergroup),
        f"csrr x{r_before}, {csr}",
        "sret  # instruction under test",
        "1:",
        f"csrr x{r_after}, instret",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        f"sub x{r_diff}, x{r_after}, x{r_before}",
        write_sigupd(r_diff, test_data),
        f"csrw sstatus, x{r_save}",
        "",
    ]
    test_data.int_regs.return_registers([r_save, r_tmp, r_before, r_after, r_diff])
    return lines


def instret_exception_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Instructions that trap before retiring: ecall, ebreak, load access fault, load misaligned."""
    assert mode in ("M", "S", "U")
    csr = "minstret" if mode == "M" else "instret"
    lines = _counter_prep(test_data, mode)

    lines += [
        comment_banner("cp_instret_ecall", f"ecall in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(test_data, covergroup, "ecall", mode, ["RVTEST_TSBI_ECALL_TEST"]),
        comment_banner("cp_instret_ebreak", f"ebreak in {mode}-mode: {csr} delta recorded"),
        "",
        *_instret_case(test_data, covergroup, "ebreak", mode, ["ebreak", "nop"]),
    ]

    r_addr, r_tmp = test_data.int_regs.get_registers(2)
    lines += [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD",
        comment_banner("cp_instret_load_access_fault", f"Load access fault in {mode}-mode: {csr} delta recorded"),
        "",
        f"LA(x{r_addr}, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)",
        *_instret_case(test_data, covergroup, "load_access_fault", mode, [f"lw x{r_tmp}, 0(x{r_addr})"]),
        "#endif // RVMODEL_ACCESS_FAULT_ADDRESS_LOAD",
        "",
        comment_banner("cp_instret_load_misaligned", f"Load address misaligned in {mode}-mode: {csr} delta recorded"),
        "",
        f"LA(x{r_addr}, scratch)",
        f"addi x{r_addr}, x{r_addr}, 1  # misalign by 1 byte",
        *_instret_case(test_data, covergroup, "load_misaligned", mode, [f"lw x{r_tmp}, 0(x{r_addr})"]),
    ]
    test_data.int_regs.return_registers([r_addr, r_tmp])
    return lines


def instret_interrupt_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """wfi and wrs cases in M-mode (minstret), S-mode or U-mode (instret).

    No case takes an interrupt, so the delta never includes a trap handler. A wfi that ends with a
    taken interrupt is not measured: whether the wfi retires before the trap depends on when the
    interrupt is taken, and the handler's retired-instruction count is implementation-defined.
    M-mode wfi_pending wakes on a machine timer interrupt that mstatus.MIE = 0 keeps from being
    taken. S-mode uses delegated supervisor interrupts with sstatus.SIE = 0: wfi_pending with SSIP
    already pending, and wfi_wake with an Sstc timer that fires while the wfi waits.
    """

    assert mode in ("M", "S", "U")
    csr = "minstret" if mode == "M" else "instret"
    lines = _counter_prep(test_data, mode)
    if mode != "M":
        r_tmp = test_data.int_regs.get_register()
        lines += [f"LI(x{r_tmp}, 0x200000)", tsbi_call_or_direct(f"csrc mstatus, x{r_tmp}  # mstatus.TW = 0", mode)]
        test_data.int_regs.return_register(r_tmp)

    cond = "defined(UDB_WFI_FINITE)" + (" && defined(UDB_WFI_U_MODE)" if mode == "U" else "")
    lines += [
        f"#if {cond}",
        comment_banner("cp_instret_wfi_timeout", f"wfi in {mode}-mode with nothing armed: {csr} delta recorded"),
        "",
        tsbi_call_or_direct("csrw mie, zero", mode),
        *(["csrci mstatus, 8  # MIE = 0"] if mode == "M" else []),
        f"RVTEST_CLR_MTIME_INT_{mode}",
        *_instret_case(
            test_data,
            covergroup,
            "wfi_timeout",
            mode,
            ["wfi  # no event armed", *(["nop"] if mode == "U" else [])],
        ),
        f"#endif // {cond}",
    ]

    if mode == "M":
        lines += _instret_wfi_m_tests(test_data, covergroup)
    elif mode == "S":
        lines += _instret_wfi_s_tests(test_data, covergroup)

    lines += [
        "#ifdef ZAWRS_SUPPORTED",
        comment_banner(
            "cp_instret_wrs_nto", f"wrs.nto in {mode}-mode, no reservation: does not stall, {csr} delta recorded"
        ),
        "",
        tsbi_call_or_direct("csrw mie, zero", mode),
        *_instret_case(
            test_data,
            covergroup,
            "wrs_nto",
            mode,
            ["wrs.nto  # instruction under test"],
        ),
        comment_banner("cp_instret_wrs_sto", f"wrs.sto in {mode}-mode: short stall, {csr} delta recorded"),
        "",
        tsbi_call_or_direct("csrw mie, zero", mode),
        *_instret_case(
            test_data,
            covergroup,
            "wrs_sto",
            mode,
            ["wrs.sto  # instruction under test"],
        ),
        "#endif // ZAWRS_SUPPORTED",
    ]
    return lines


def _instret_wfi_m_tests(test_data: TestData, covergroup: str) -> list[str]:
    """M-mode wfi with a machine timer interrupt pending that mstatus.MIE = 0 keeps from being taken."""
    r_tmp = test_data.int_regs.get_register()
    lines = [
        "#ifdef UDB_MTI_INTR_IMPL",
        comment_banner("cp_instret_wfi_pending", "wfi with timer interrupt pending and MIE = 0: no trap."),
        "",
        "csrw mie, zero",
        "csrci mstatus, 8  # MIE = 0",
        f"LI(x{r_tmp}, 0x80)",
        f"csrw mie, x{r_tmp}  # MTIE only",
        "RVTEST_SET_MTIME_INT_SOON_M",
        "1:",
        f"csrr x{r_tmp}, mip",
        f"andi x{r_tmp}, x{r_tmp}, 0x80  # mip.MTIP",
        f"beqz x{r_tmp}, 1b  # wait until MTIP is really pending",
        *_instret_case(test_data, covergroup, "wfi_pending", "M", ["wfi  # already pending, not taken"]),
        "RVTEST_CLR_MTIME_INT_M",
        "#endif // UDB_MTI_INTR_IMPL",
    ]
    test_data.int_regs.return_register(r_tmp)
    return lines


def _instret_wfi_s_tests(test_data: TestData, covergroup: str) -> list[str]:
    """S-mode wfi woken by a delegated supervisor interrupt that sstatus.SIE = 0 keeps from being taken.

    The boot code delegates SSI and STI to S-mode. With no trap, the instret delta has no handler in it.
    """
    r_tmp = test_data.int_regs.get_register()
    lines = [
        comment_banner("cp_instret_wfi_pending", "wfi with SSIP pending, sie.SSIE = 1 and sstatus.SIE = 0: no trap."),
        "",
        "csrci sstatus, 2  # SIE = 0",
        f"LI(x{r_tmp}, 0x2)",
        f"csrw sie, x{r_tmp}  # SSIE only",
        "csrsi sip, 2  # SSIP pending",
        *_instret_case(test_data, covergroup, "wfi_pending", "S", ["wfi  # already pending, not taken"]),
        "csrci sip, 2  # clear SSIP",
        "csrw sie, zero",
        "",
    ]
    test_data.int_regs.return_register(r_tmp)

    lines += [
        "#ifdef SSTC_SUPPORTED",
        comment_banner(
            "cp_instret_wfi_wake",
            "wfi woken by an Sstc timer interrupt with sie.STIE = 1 and sstatus.SIE = 0: no trap.\n"
            "wfi may resume early, so it repeats until STIP is pending. Each pass retires 6 instructions\n"
            "and is tallied, so the delta minus the tally is the same on every implementation.",
        ),
        "",
        *write_stce(test_data, True, "S"),
    ]
    r_tmp, r_tally, r_before, r_after, r_diff = test_data.int_regs.get_registers(5)
    lines += [
        "RVTEST_CLR_SSTC_INT_S",
        f"LI(x{r_tmp}, 0x20)",
        f"csrw sie, x{r_tmp}  # STIE only",
        "RVTEST_SET_SSTC_INT_SOON_S",
        f"LI(x{r_tally}, 0)  # instructions retired by the passes below",
        test_data.add_testcase("instret_wfi_wake", "cp_instret_wfi_wake", covergroup),
        f"csrr x{r_before}, instret",
        "1:",
        f"csrr x{r_tmp}, sip",
        f"andi x{r_tmp}, x{r_tmp}, 0x20  # sip.STIP",
        f"bnez x{r_tmp}, 2f  # woken by the pending timer",
        "wfi  # instruction under test",
        f"addi x{r_tally}, x{r_tally}, 6",
        "j 1b",
        "2:",
        f"csrr x{r_after}, instret",
        f"sub x{r_after}, x{r_after}, x{r_tally}",
        f"sub x{r_diff}, x{r_after}, x{r_before}",
        write_sigupd(r_diff, test_data),
        "RVTEST_CLR_SSTC_INT_S",
        "csrw sie, zero",
    ]
    test_data.int_regs.return_registers([r_tmp, r_tally, r_before, r_after, r_diff])
    lines += [*write_stce(test_data, False, "S"), "#endif // SSTC_SUPPORTED", ""]
    return lines
