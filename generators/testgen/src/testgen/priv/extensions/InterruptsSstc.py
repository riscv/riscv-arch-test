##################################
# priv/extensions/interruptsSstc.py
#
# InterruptsSstc privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import (
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
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_machine_sti"
    r_scratch, r_stce = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner("cp_machine_sti", "M-mode STI: mideleg x mie_stie (STCE=1, MIE=1 fixed)"),
        "",
    ]

    for mideleg_sti in [0, 1]:
        for mie_stie in [0, 1]:
            binname = f"{'d' if mideleg_sti else 'nd'}_stie{mie_stie}"
            lines += [
                "",
                f"# cp_machine_sti: mideleg={mideleg_sti} stie={mie_stie}",
                # --- setup: STCE=1, mideleg, mie.STIE, stimecmp=-1, MIE/SIE=0 ---
                *mmode_sti_setup(r_scratch, r_stce, mideleg_sti, mie_stie),
                # enable MIE=1; interrupt won't fire yet because stimecmp=-1
                "csrsi mstatus, 8",
                test_data.add_testcase(binname, coverpoint, covergroup),
                *set_stimecmp_zero(),
                # --- wait for interrupt to be handled ---
                f"LI(x{r_scratch}, 2500)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
                # --- cleanup: restore stimecmp=-1, STCE=0, mideleg=0, mie=0 ---
                *mmode_sti_cleanup(r_scratch, r_stce),
            ]

    test_data.int_regs.return_registers([r_scratch, r_stce])
    return lines


# ---------------------------------------------------------------------------
# Machine-mode TM / STCE read tests
# ---------------------------------------------------------------------------


def _generate_machine_tm_tests(test_data: TestData) -> list[str]:
    """cp_machine_tm: M-mode csrr stimecmp with mcounteren.TM={0,1}."""
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_machine_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner("cp_machine_tm", "M-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# cp_machine_tm: TM={tm_val}",
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
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_machine_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

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
    """cp_supervisor_sti_deleg / cp_supervisor_sti_nodeleg: all 32 bins.

    deleg=1 (cp_supervisor_sti_deleg, priv_mode_s):
      Enter S-mode via mret. For STCE=1: sample at csrw stimecmp,0 in S-mode,
      interrupt fires after. For STCE=0: stimecmp=0 written in M-mode (no STI
      since STCE=0 disables Sstc), sample at nop in S-mode.
      MIE in S-mode is controlled via MPIE; SIE via csrsi/csrci in S-mode.

    deleg=0 (cp_supervisor_sti_nodeleg, priv_mode_m):
      Stay in M-mode. Enable MIE=1 before testcase so prev.MIE=1 at sample.
      For STCE=1: sample at csrw stimecmp,0. For STCE=0: sample at nop
      (stimecmp already 0 from setup, no interrupt since STCE=0).
    """
    covergroup = "InterruptsS_S_cg"
    r_scratch, r_stce = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_supervisor_sti_deleg / cp_supervisor_sti_nodeleg",
            "S-mode STI: menvcfg_stce x mstatus_mie x mstatus_sie\n"
            "         x mideleg_sti x mie_stie x stimecmp_zero  (32 bins each)",
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

                        # --- common M-mode setup: disable all interrupts, clear state ---
                        lines += [
                            "",
                            f"# cp_supervisor_sti: STCE={stce} MIE={mie} SIE={sie} deleg={deleg} STIE={stie}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                            f"LI(x{r_scratch}, 0x20)",
                            f"CSRC(mip, x{r_scratch})",  # clear any pending STIP
                        ]

                        # configure STCE and stimecmp
                        if stce:
                            lines += set_stimecmp_max(r_scratch)  # stimecmp=-1 (no pending STI yet)
                            lines += set_menvcfg_stce(r_stce, True)  # STCE=1: enable Sstc
                        else:
                            lines += set_menvcfg_stce(r_stce, False)  # STCE=0: disable Sstc
                            lines.append("CSRW(stimecmp, zero)")  # stimecmp=0; no STI fires (STCE=0)

                        # configure delegation and interrupt enable
                        if deleg:
                            lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mideleg, x{r_scratch})"]  # STI → S-mode
                        else:
                            lines.append("CSRW(mideleg, zero)")  # STI → M-mode

                        if stie:
                            lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mie, x{r_scratch})"]  # STIE=1
                        else:
                            lines.append("CSRW(mie, zero)")  # STIE=0

                        if deleg:
                            # --- enter S-mode; MIE controlled via MPIE, SIE set inside S-mode ---
                            lines += set_mpie(r_scratch, bool(mie))  # MPIE → MIE after mret
                            lines.append("RVTEST_GOTO_LOWER_MODE Smode")
                            if sie:
                                lines.append("    csrsi sstatus, 2")  # SIE=1
                            else:
                                lines.append("    csrci sstatus, 2")  # SIE=0
                            lines.append(
                                f"    {test_data.add_testcase(binname, 'cp_supervisor_sti_deleg', covergroup)}"
                            )
                            if stce:
                                lines += ["    " + l for l in set_stimecmp_zero()]
                            else:
                                lines.append("    nop")
                            lines += [
                                f"    LI(x{r_scratch}, 2500)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        else:
                            # --- stay in M-mode; enable MIE=1 before testcase so prev.MIE=1 at sample ---
                            lines.append("csrsi mstatus, 8")  # MIE=1 (prev.MIE=1 at next insn)
                            lines.append("nop")  # stable prev state
                            lines.append(test_data.add_testcase(binname, "cp_supervisor_sti_nodeleg", covergroup))
                            if stce:
                                lines += set_stimecmp_zero()
                            else:
                                lines.append("nop")
                            lines += [
                                f"LI(x{r_scratch}, 2500)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]

                        # --- cleanup: restore stimecmp=-1, STCE=0, mideleg=0, mie=0 ---
                        lines += mmode_sti_cleanup(r_scratch, r_stce)

    test_data.int_regs.return_registers([r_scratch, r_stce])
    return lines


# ---------------------------------------------------------------------------
# Supervisor-mode TM / STCE read tests
# ---------------------------------------------------------------------------


def _generate_supervisor_tm_tests(test_data: TestData) -> list[str]:
    """cp_supervisor_tm: S-mode csrr stimecmp with mcounteren.TM={0,1}.

    TM=0: csrr stimecmp from S-mode traps; coverage is still sampled at the csrr.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_supervisor_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner("cp_supervisor_tm", "S-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# cp_supervisor_tm: TM={tm_val}",
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
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_supervisor_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner("cp_supervisor_stce", "S-mode stimecmp read: menvcfg.STCE={0,1}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# cp_supervisor_stce: STCE={stce_val}",
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

    All 32 bins (menvcfg_stce x mstatus_mie x mstatus_sie x mideleg_sti x mie_stie)
    are sampled at a nop in U-mode.

    stce=1: stimecmp=TIME+500 so the interrupt fires AFTER the sample nop; the
            interrupt then goes to S-mode (mideleg=1) or M-mode (mideleg=0).
    stce=0: stimecmp=TIME+500 is set but STCE=0 disables Sstc, so no interrupt fires;
            we only sample the CSR configuration.  mip.STIP is NOT set for stce=0
            because doing so with mideleg=0+STIE=1 would cause M-mode to preempt
            U-mode unconditionally before the sample instruction executes.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_sti"
    r_scratch, r_stce, r_hi = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_user_sti",
            "U-mode STI: menvcfg_stce x mstatus_mie x mstatus_sie\n"
            "         x mideleg_sti x mie_stie  (32 bins)\n"
            "stce=1: stimecmp=TIME+500, interrupt fires after sample.\n"
            "stce=0: CSR state sampled only; no interrupt (avoids mideleg=0+STIE=1 preemption).",
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

                        # --- common M-mode setup: disable all interrupts, clear state ---
                        lines += [
                            "",
                            f"# cp_user_sti: STCE={stce} MIE={mie} SIE={sie} deleg={deleg} STIE={stie}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                            f"LI(x{r_scratch}, 0x20)",
                            f"CSRC(mip, x{r_scratch})",  # clear any pending STIP
                            *set_stimecmp_max(r_scratch),  # stimecmp=-1
                            *set_menvcfg_stce(r_stce, bool(stce)),  # set STCE
                        ]

                        # configure delegation and interrupt enable
                        if deleg:
                            lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mideleg, x{r_scratch})"]  # STI → S-mode
                        else:
                            lines.append("CSRW(mideleg, zero)")  # STI → M-mode

                        if stie:
                            lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mie, x{r_scratch})"]  # STIE=1
                        else:
                            lines.append("CSRW(mie, zero)")  # STIE=0

                        # schedule interrupt: stce=1 fires after sample; stce=0 no interrupt
                        if stce:
                            lines += set_stimecmp_soon(r_scratch, r_stce, r_hi)  # stimecmp=TIME+500

                        # set SIE in mstatus before entering U-mode
                        if sie:
                            lines.append("csrsi mstatus, 2")
                        else:
                            lines.append("csrci mstatus, 2")

                        # MPIE controls MIE after mret into U-mode
                        lines += set_mpie(r_scratch, bool(mie))
                        lines.append("RVTEST_GOTO_LOWER_MODE Umode")
                        lines.append(f"    {test_data.add_testcase(binname, coverpoint, covergroup)}")
                        lines += [
                            f"    LI(x{r_scratch}, 2500)",
                            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                            f"    bnez x{r_scratch}, 1b",
                        ]

                        # --- cleanup: restore stimecmp=-1, STCE=0, mideleg=0, mie=0 ---
                        lines += mmode_sti_cleanup(r_scratch, r_stce)

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
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_tm"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner("cp_user_tm", "U-mode stimecmp read: mcounteren.TM={0,1}"),
        "",
    ]
    for tm_val in [0, 1]:
        lines += [
            "",
            f"# cp_user_tm: TM={tm_val}",
            "RVTEST_GOTO_MMODE",
            # STCE=1 so stimecmp is accessible (when TM=1)
            *set_menvcfg_stce(r_scratch, True),
            # scounteren.TM=1 always; only mcounteren.TM varies
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(scounteren, x{r_scratch})",
        ]
        if tm_val:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRS(mcounteren, x{r_scratch})"]
        else:
            lines += [f"LI(x{r_scratch}, 0x2)", f"CSRC(mcounteren, x{r_scratch})"]

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
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_stce"
    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner("cp_user_stce", "U-mode stimecmp read: menvcfg.STCE={0,1}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# cp_user_stce: STCE={stce_val}",
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


@add_priv_test_generator("InterruptsSstc", required_extensions=["Sm", "S", "Sstc", "I", "Zicsr"])
def make_interruptss_s(test_data: TestData) -> list[str]:
    """Generate all Sstc interrupt tests (machine, supervisor, user modes)."""
    r_temp = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "InterruptsSstc",
            "Supervisor timer (Sstc) interrupt tests\n"
            "Covers M-mode, S-mode, and U-mode scenarios for stimecmp-based STI.",
        ),
        "",
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

    test_data.int_regs.return_registers([r_temp])
    return lines
