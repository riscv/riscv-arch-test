##################################
# priv/extensions/interruptsSstc.py
#
# InterruptsSstc privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import (
    clr_mtimer_int,
    mmode_sti_cleanup,
    mmode_sti_setup,
    set_menvcfg_stce,
    set_mpie,
    set_stimecmp_max,
    set_stimecmp_soon,
    set_stimecmp_zero,
)
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Machine-mode STI tests
# ---------------------------------------------------------------------------


def _generate_machine_sti_tests(test_data: TestData) -> list[str]:
    """cp_machine_sti: iterate mideleg x mie_stie; sample at ``csrw stimecmp, zero`` in M-mode.

    STCE=1 and MIE=1 are fixed (required by menvcfg_stce_one and mstatus_mie_one).
    The interrupt fires at the countdown loop after the sample.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_machine_sti"
    r_scratch, r_stce = test_data.int_regs.get_registers(2, exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "M-mode STI: mideleg x mie_stie (STCE=1, MIE=1 fixed)"),
        "",
    ]

    for mideleg_sti in [0, 1]:
        for mie_stie in [0, 1]:
            binname = f"{'d' if mideleg_sti else 'nd'}_stie{mie_stie}"
            lines += [
                "",
                f"# {coverpoint}: mideleg={mideleg_sti} stie={mie_stie}",
                *mmode_sti_setup(r_scratch, r_stce, mideleg_sti, mie_stie),
                # MIE=1 must be set before stimecmp=0: coverage samples at the csrw stimecmp
                # instruction and requires prev.MIE=1. set_stimecmp_zero() going from -1 to 0
                # is safe on RV32 (intermediate state lo=0,hi=max >> mtime, no spurious fire).
                "csrsi mstatus, 8",
                test_data.add_testcase(binname, coverpoint, covergroup),
                *set_stimecmp_zero(),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
                *mmode_sti_cleanup(r_scratch, r_stce),
                *clr_mtimer_int(r_scratch, r_stce),
            ]

    test_data.int_regs.return_registers([r_scratch, r_stce])
    return lines


# ---------------------------------------------------------------------------
# Machine-mode TM / STCE read tests
# ---------------------------------------------------------------------------


def _generate_machine_tm_tests(test_data: TestData) -> list[str]:
    """cp_machine_tm: M-mode csrr stimecmp with mcounteren.TM={0,1}."""
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_machine_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "M-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: TM={tm_val}",
            "RVTEST_GOTO_MMODE",
            # set or clear mcounteren.TM to control stimecmp visibility
        ]
        if tm_val:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRS(mcounteren, x{r_scratch})"]
        else:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRC(mcounteren, x{r_scratch})"]

        lines.append(test_data.add_testcase(f"tm{tm_val}", coverpoint, covergroup))
        lines += [f"CSRR x{r_scratch}, stimecmp", "nop"]
        # restore: clear mcounteren.TM
        lines += [f"LI(x{r_scratch}, 0x2)", f"CSRC(mcounteren, x{r_scratch})"]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_machine_stce_tests(test_data: TestData) -> list[str]:
    """cp_machine_stce: M-mode csrr stimecmp with menvcfg.STCE={0,1}."""
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_machine_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner("cp_machine_stce", "M-mode stimecmp read: menvcfg.STCE={0,1}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# cp_machine_stce: STCE={stce_val}",
            "RVTEST_GOTO_MMODE",
            # set menvcfg.STCE to the loop value
            *set_menvcfg_stce(r_scratch, bool(stce_val)),
        ]
        lines.append(test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup))
        lines += [f"CSRR x{r_scratch}, stimecmp", "nop"]
        # restore STCE=1 for subsequent tests
        lines += set_menvcfg_stce(r_scratch, True)

    test_data.int_regs.return_registers([r_scratch])
    return lines


# ---------------------------------------------------------------------------
# Supervisor-mode STI tests
# ---------------------------------------------------------------------------


def _generate_supervisor_sti_tests(test_data: TestData) -> list[str]:
    """cp_supervisor_sti_deleg: S-mode STI cross (32 bins).

    Cross of menvcfg_stce × mstatus_mie × mstatus_sie × mideleg_sti × mie_stie.
    For STCE=1: stimecmp=-1 in M-mode, enter S-mode, write stimecmp=0 in S-mode so the
    interrupt fires while already in S-mode. For STCE=0: stimecmp=0 in M-mode (STCE=0
    prevents STIP from asserting, so S-mode runs freely and the sample fires at the nop).
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_supervisor_sti_deleg"
    r_scratch, r_stce = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            f"{coverpoint}", "S-mode STI: menvcfg_stce × mstatus_mie × mstatus_sie × mideleg_sti × mie_stie (32 bins)"
        ),
        "",
    ]

    for stce in [0, 1]:
        for mie in [0, 1]:
            for sie in [0, 1]:
                for mideleg_val in [0, 1]:
                    for stie in [0, 1]:
                        binname = f"stce{stce}_mie{mie}_sie{sie}_mideleg{mideleg_val}_stie{stie}"

                        lines += [
                            "",
                            f"# {coverpoint}: STCE={stce} MIE={mie} SIE={sie} MIDELEG={mideleg_val} STIE={stie}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            # load 0x20 once; reused for mip/mideleg/mie below
                            # (set_menvcfg_stce uses r_stce so r_scratch stays valid)
                            f"LI(x{r_scratch}, 0x20)",
                            f"CSRC(mip, x{r_scratch})",
                            "csrsi mcounteren, 2",
                        ]

                        lines += set_menvcfg_stce(r_stce, bool(stce))

                        if mideleg_val:
                            lines.append(f"CSRW(mideleg, x{r_scratch})")
                        else:
                            lines.append("CSRW(mideleg, zero)")

                        if stie:
                            lines.append(f"CSRW(mie, x{r_scratch})")

                        # stimecmp setup last (clobbers r_scratch)
                        if stce:
                            lines += set_stimecmp_max(r_scratch)
                        else:
                            lines += set_stimecmp_zero()

                        lines += set_mpie(r_scratch, bool(mie))
                        lines.append("RVTEST_GOTO_LOWER_MODE Smode")

                        if sie:
                            lines.append("    csrsi sstatus, 2")
                        else:
                            lines.append("    csrci sstatus, 2")

                        lines.append(f"    {test_data.add_testcase(binname, coverpoint, covergroup)}")

                        if stce:
                            lines += set_stimecmp_zero()

                        lines.append(f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

                        lines += mmode_sti_cleanup(r_scratch, r_stce)
                        lines += clr_mtimer_int(r_scratch, r_stce)
                        lines.append("csrci mcounteren, 2")

    test_data.int_regs.return_registers([r_scratch, r_stce])
    return lines


# ---------------------------------------------------------------------------
# Supervisor-mode TM / STCE read tests
# ---------------------------------------------------------------------------


def _generate_supervisor_tm_tests(test_data: TestData) -> list[str]:
    """cp_supervisor_tm: S-mode csrr stimecmp with mcounteren.TM={0,1}.

    TM=0: csrr stimecmp from S-mode traps; coverage is still sampled at the csrr.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_supervisor_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "S-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: TM={tm_val}",
            "RVTEST_GOTO_MMODE",
            # STCE=1 so stimecmp is accessible from S-mode
            *set_menvcfg_stce(r_scratch, True),
            # set or clear mcounteren.TM
        ]
        if tm_val:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRS(mcounteren, x{r_scratch})"]
        else:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRC(mcounteren, x{r_scratch})"]

        lines += [
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"    {test_data.add_testcase(f'tm{tm_val}', coverpoint, covergroup)}",
            f"    CSRR x{r_scratch}, stimecmp",
            "    nop",
            # --- return to M-mode and restore ---
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mcounteren, x{r_scratch})",
            *set_menvcfg_stce(r_scratch, False),
        ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_supervisor_stce_tests(test_data: TestData) -> list[str]:
    """cp_supervisor_stce: S-mode csrr stimecmp with menvcfg.STCE={0,1}.

    STCE=0: csrr stimecmp from S-mode traps; coverage sampled at the csrr.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_supervisor_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "S-mode stimecmp read: menvcfg.STCE={0,1}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: STCE={stce_val}",
            "RVTEST_GOTO_MMODE",
            # set STCE to test value before entering S-mode
            *set_menvcfg_stce(r_scratch, bool(stce_val)),
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"    {test_data.add_testcase(f'stce{stce_val}', coverpoint, covergroup)}",
            f"    CSRR x{r_scratch}, stimecmp",
            "    nop",
            # --- return to M-mode and restore STCE=0 ---
            "RVTEST_GOTO_MMODE",
            *set_menvcfg_stce(r_scratch, False),
        ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


# ---------------------------------------------------------------------------
# User-mode STI tests
# ---------------------------------------------------------------------------


def _generate_user_sti_tests(test_data: TestData) -> list[str]:
    """cp_user_sti: U-mode STI cross (32 bins).

    Cross of:
      menvcfg.STCE  x  mstatus.MIE  x  mstatus.SIE  x  mideleg.STI  x  mie.STIE
    = 2^5 = 32 bins

    STIMECMP is always set to TIME+RVMODEL_TIMER_INT_SOON_DELAY unless a different time is specified so the interrupt fires AFTER the sample
    nop in U-mode.  The interrupt is expected to be taken in M-mode (mideleg=0)
    or S-mode (mideleg=1) regardless of MIE/SIE — the interrupt pending bit
    (mip.STIP) asserts only when STCE=1; when STCE=0 the Sstc extension is
    disabled so no timer interrupt fires and we only sample the CSR state.

    Note: for stce=0 we do NOT manually set mip.STIP because with
    mideleg=0 + STIE=1 M-mode would preempt U-mode before the sample executes.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_user_sti"
    r_scratch, r_stce, r_hi = test_data.int_regs.get_registers(3, exclude_regs=[])

    lines = [
        comment_banner(
            f"{coverpoint}",
            "U-mode STI cross (32 bins)\n"
            "menvcfg_stce x mstatus_mie x mstatus_sie x mideleg_sti x mie_stie\n"
            "STIMECMP=TIME+RVMODEL_TIMER_INT_SOON_DELAY: interrupt fires after sample nop.\n"
            "stce=0: Sstc disabled; CSR state sampled only, no interrupt.",
        ),
        "",
    ]

    for stce in [0, 1]:
        for mie in [0, 1]:
            for sie in [0, 1]:
                for deleg in [0, 1]:
                    for stie in [0, 1]:
                        deleg_name = ["no_deleg", "deleg"][deleg]
                        binname = f"stce{stce}_mie{mie}_sie{sie}_{deleg_name}_stie{stie}"

                        lines += [
                            "",
                            f"# ---- {coverpoint} bin: {binname} ----",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            # load 0x20 once; reused for mip/mideleg/mie below
                            # (set_menvcfg_stce uses r_stce so r_scratch stays valid)
                            f"LI(x{r_scratch}, 0x20)",
                            f"CSRC(mip, x{r_scratch})",
                            *set_menvcfg_stce(r_stce, bool(stce)),
                        ]

                        if deleg:
                            lines.append(f"CSRW(mideleg, x{r_scratch})")
                        else:
                            lines.append("CSRW(mideleg, zero)")

                        if stie:
                            lines.append(f"CSRW(mie, x{r_scratch})")

                        # stimecmp setup last (clobbers r_scratch)
                        lines += set_stimecmp_max(r_scratch)

                        # Set stimecmp = TIME+RVMODEL_TIMER_INT_SOON_DELAY so the interrupt fires after
                        # the sample nop in U-mode. From U-mode, MIE and SIE don't gate the trap —
                        # it routes to M or S depending on mideleg regardless of mstatus.MIE/SIE.
                        lines += set_stimecmp_soon(r_scratch, r_stce, r_hi)

                        # ---- mstatus.SIE — set before mret so it's live in U-mode ----
                        if sie:
                            lines += ["# mstatus.SIE=1", "csrsi mstatus, 2"]
                        else:
                            lines += ["# mstatus.SIE=0", "csrci mstatus, 2"]

                        # ---- mstatus.MIE — encoded in MPIE so mret restores it ----
                        lines += [
                            "# MPIE encodes the MIE value that mret will restore",
                            *set_mpie(r_scratch, bool(mie)),
                        ]

                        lines += [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            f"    {test_data.add_testcase(binname, coverpoint, covergroup)}",
                            f"    RVTEST_IDLE_FOR_TIMER_INTERRUPT(x{r_scratch})",
                        ]

                        # ---- Cleanup: back to M-mode, restore safe CSR state ----
                        lines += [
                            "# Cleanup: reset stimecmp, STCE, mideleg, mie",
                            *mmode_sti_cleanup(r_scratch, r_stce),
                        ]

    test_data.int_regs.return_registers([r_scratch, r_stce, r_hi])
    return lines


# ---------------------------------------------------------------------------
# User-mode TM / STCE read tests
# ---------------------------------------------------------------------------


def _generate_user_tm_tests(test_data: TestData) -> list[str]:
    """cp_user_tm: U-mode csrr stimecmp with mcounteren.TM={0,1}.

    scounteren.TM is fixed to 1 so mcounteren.TM is the only variable.
    TM=0 causes a trap; coverage is sampled at the csrr before the trap.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_user_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "U-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: TM={tm_val}",
            "RVTEST_GOTO_MMODE",
            # STCE=1 so stimecmp is accessible (when TM=1)
            *set_menvcfg_stce(r_scratch, True),
            # scounteren.TM=1 always; only mcounteren.TM varies
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(scounteren, x{r_scratch})",
        ]
        if tm_val:
            lines += [f"CSRS(mcounteren, x{r_scratch})"]
        else:
            lines += [f"CSRC(mcounteren, x{r_scratch})"]

        lines += [
            "RVTEST_GOTO_LOWER_MODE Umode",
            f"    {test_data.add_testcase(f'tm{tm_val}', coverpoint, covergroup)}",
            f"    CSRR x{r_scratch}, stimecmp",
            "    nop",
            # --- return to M-mode and restore ---
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mcounteren, x{r_scratch})",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(scounteren, x{r_scratch})",
            *set_menvcfg_stce(r_scratch, False),
        ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_stce_tests(test_data: TestData) -> list[str]:
    """cp_user_stce: U-mode csrr stimecmp with menvcfg.STCE={0,1}.

    mcounteren.TM and scounteren.TM are fixed to 1.
    STCE=0: csrr stimecmp from U-mode traps; coverage sampled at the csrr.
    """
    covergroup = "InterruptsSstc_cg"
    coverpoint = "cp_user_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(f"{coverpoint}", "U-mode stimecmp read: menvcfg.STCE={0,1}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: STCE={stce_val}",
            "RVTEST_GOTO_MMODE",
            # set STCE to test value before entering U-mode
            *set_menvcfg_stce(r_scratch, bool(stce_val)),
            # TM=1 in both counteren so stimecmp access depends only on STCE
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(mcounteren, x{r_scratch})",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(scounteren, x{r_scratch})",
            "RVTEST_GOTO_LOWER_MODE Umode",
            f"    {test_data.add_testcase(f'stce{stce_val}', coverpoint, covergroup)}",
            f"    CSRR x{r_scratch}, stimecmp",
            "    nop",
            # --- return to M-mode and restore ---
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mcounteren, x{r_scratch})",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(scounteren, x{r_scratch})",
            *set_menvcfg_stce(r_scratch, False),
        ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator("InterruptsSstc", required_extensions=["Sm", "S", "Sstc"])
def make_interruptss_s(test_data: TestData) -> list[str]:
    """Generate all Sstc interrupt tests (machine, supervisor, user modes)."""
    r_temp, r_mtcmp = test_data.int_regs.get_registers(2, exclude_regs=[])

    lines = [
        comment_banner(
            "InterruptsSstc",
            "Supervisor timer (Sstc) interrupt tests\n"
            "Covers M-mode, S-mode, and U-mode scenarios for stimecmp-based STI.",
        ),
        "",
        # Initialize mtimecmp=-1 so MTIP is not spuriously set during Sstc tests.
        # SAIL initializes mtimecmp=0, which makes MTIP permanently set. Without
        # this, mip reads during Sstc traps see STIP+MTIP, but whisper (which
        # initializes mtimecmp to a large default) only sees STIP, causing a mismatch.
        *clr_mtimer_int(r_temp, r_mtcmp),
        # global init: no delegation, clear TW so WFI doesn't trap in lower modes
        "CSRW(mideleg, zero)",
        f"LI(x{r_temp}, 0x200000)",
        f"CSRC(mstatus, x{r_temp})",  # clear TW bit
        "",
    ]

    lines += _generate_machine_sti_tests(test_data)
    lines += _generate_machine_tm_tests(test_data)
    lines += _generate_machine_stce_tests(test_data)
    lines += _generate_supervisor_sti_tests(test_data)
    lines += _generate_supervisor_tm_tests(test_data)
    lines += _generate_supervisor_stce_tests(test_data)
    lines += _generate_user_sti_tests(test_data)
    lines += _generate_user_tm_tests(test_data)
    lines += _generate_user_stce_tests(test_data)

    test_data.int_regs.return_registers([r_temp, r_mtcmp])
    return lines
