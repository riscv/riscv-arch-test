##################################
# priv/extensions/InterruptsSm.py
#
# InterruptsSm privileged extension test generator.
# David_Harris@hmc.edu 7 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""InterruptsSm privileged extension test generator for interrupts relying on M-mode."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import (
    INTR_IMPL_DEFINES,
    REG_TRIGGER_DEFINES,
    SHARED_GENERATORS,
    SSTC_TRIGGER_DEFINES,
    emit_interrupts,
    generate_cp_priority,
    guard_close,
    guard_open,
    guard_symbol,
    int_coverpoint,
    int_macro,
    machine_ints,
    mode_enter,
    mode_exit,
    reg_ints,
    sstc_ints,
    supervisor_ints,
    write_stce,
)
from testgen.priv.registry import add_priv_test_generator

SUITE = "InterruptsSm"
COVERGROUP = f"{SUITE}_cg"


def _generate_cp_trigger_sm(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Trigger each interrupt across mideleg, mtvec.MODE, mstatus.SIE, and mstatus.MIE."""

    ######################################
    banner = "cp_trigger / cp_trigger_reg / cp_trigger_sti_sstc"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, f"trigger_{priv}")
    tc.section_header = comment_banner(
        banner,
        f"Trigger each interrupt in {priv} mode with mie=1s x mideleg = zeros/ones x mtvec.MODE=DIRECT/VECTORED"
        " x mstatus.SIE=0/1 x mstatus.MIE=0/1",
    )
    tc.code += guard_open(suite, priv)
    tmp_reg = test_data.int_regs.get_register()

    for int_type in [*machine_ints, *supervisor_ints, *reg_ints, *sstc_ints]:
        if int_type not in int_macro:
            continue  # no RVTEST_SET/CLR macros for this interrupt yet
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        cp = int_coverpoint.get(int_type, "cp_trigger")
        for mideleg in [0, -1]:
            delegstr = "zeros" if mideleg == 0 else "ones"
            # mideleg only exists with S-mode. Without it the mideleg = zeros cases still run and just
            # skip the write, while the mideleg = ones cases are meaningless and are left out entirely.
            case_open = ["#ifdef S_SUPPORTED // only test delegation if S_SUPPORTED"] if mideleg == -1 else []
            case_close = ["#endif // S_SUPPORTED"] if mideleg == -1 else []
            write_open = ["#ifdef S_SUPPORTED // only write mideleg if S_SUPPORTED"] if mideleg == 0 else []
            write_close = ["#endif // S_SUPPORTED"] if mideleg == 0 else []
            for mode in [0, 1]:
                for sie in [0, 1]:
                    for mie in [0, 1]:
                        modecmd = "csrs" if mode == 1 else "csrc"
                        siecmd = "csrs" if sie == 1 else "csrc"
                        miecmd = "csrs" if mie == 1 else "csrc"
                        tc.code += [
                            f"#ifdef {guard}",
                            *case_open,
                            *write_open,
                            f"LI(x{tmp_reg}, {mideleg})",
                            f"csrw mideleg, x{tmp_reg} # mideleg = {delegstr}",
                            *write_close,
                            f"#ifdef UDB_MTVEC_MODES_{mode}",
                            f"LI(x{tmp_reg}, 1)",
                            f"{modecmd} mtvec, x{tmp_reg} # mtvec.mode = {mode}",
                            "#endif // mtvec.MODE",
                            # The trap handler clears the taken interrupt's xIE bit, so re-enable before every case
                            f"LI(x{tmp_reg}, -1)",
                            f"csrw mie, x{tmp_reg} # mie = 1s",
                            f"LI(x{tmp_reg}, 0x88) # MIE, MPIE",
                            f"{miecmd} mstatus, x{tmp_reg} # mstatus.MIE = {mie}",
                            f"LI(x{tmp_reg}, 0x22) # SIE, SPIE",
                            f"{siecmd} mstatus, x{tmp_reg} # mstatus.SIE = {sie}",
                            test_data.add_testcase(
                                f"priv_{priv}_{int_type}_mideleg_{delegstr}_mode_{mode}_sie_{sie}_mie_{mie}",
                                cp,
                                COVERGROUP,
                            ),
                            *mode_enter(suite, priv),
                            f"RVTEST_SET_{macro}_INT_{priv} # Set the interrupt",
                            f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupt to fire",
                            f"RVTEST_CLR_{macro}_INT_{priv} # Clear the interrupt if the handler hasn't done so",
                            *mode_exit(suite, priv),
                            *case_close,
                            f"#endif // {guard}",
                            "",
                        ]

    test_data.int_regs.return_register(tmp_reg)
    tc.code += guard_close(suite, priv)


def _generate_cp_priority_mideleg(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Priority of delegated interrupts: pair pending and enabled, one of them delegated."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "mideleg")


def _generate_cp_write_stip_sstc(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """With menvcfg.STCE = 1, mip.STIP follows stimecmp and ignores writes (M-mode only)."""

    ######################################
    coverpoint = "cp_write_stip_sstc"
    ######################################
    if priv != "M":
        return
    tc = test_data.new_test_chunk(test_chunks, "write_stip_sstc")
    tc.section_header = comment_banner(
        coverpoint, "With menvcfg.STCE = 1, write stimecmp = 0s/1s x mip.STIP = 0/1 and read STIP back"
    )
    tmp_reg = test_data.int_regs.get_register()

    tc.code += [
        "#ifdef SSTC_SUPPORTED",
        "csrw mideleg, zero # mideleg = zeros",
        "csrw mie, zero # mie = 0 so a pending STIP is not taken",
        *write_stce(True, "M", tmp_reg),
    ]
    for stimecmp, stimecmp_macro in [("zeros", "SET"), ("ones", "CLR")]:
        for stip, stip_macro in [(0, "CLR"), (1, "SET")]:
            tc.code += [
                f"RVTEST_{stimecmp_macro}_SSTC_INT_M # stimecmp = {stimecmp}",
                test_data.add_testcase(f"priv_M_stimecmp_{stimecmp}_STIP_{stip}", coverpoint, COVERGROUP),
                f"RVTEST_{stip_macro}_STIME_INT_M # Write mip.STIP = {stip}",
                f"csrr x{tmp_reg}, mip # mip.STIP = 1 only when stimecmp = 0s",
                f"andi x{tmp_reg}, x{tmp_reg}, 0x20 # STIP",
                write_sigupd(tmp_reg, test_data),
                "",
            ]
    tc.code += ["#endif // SSTC_SUPPORTED", ""]

    test_data.int_regs.return_register(tmp_reg)


@add_priv_test_generator(
    SUITE,
    required_extensions=["Sm"],
    extra_defines=[*INTR_IMPL_DEFINES, *REG_TRIGGER_DEFINES, *SSTC_TRIGGER_DEFINES, "#define BOOT_TO_MMODE"],
)
def make_interruptssm(test_data: TestData) -> list[TestChunk]:
    """Generate InterruptsSm tests: interrupt behavior that relies on M-mode, including delegation."""
    test_chunks: list[TestChunk] = []
    generators = [
        _generate_cp_trigger_sm,
        *SHARED_GENERATORS,
        _generate_cp_priority_mideleg,
        _generate_cp_write_stip_sstc,
    ]

    emit_interrupts(test_data, test_chunks, SUITE, ["M", "S", "U"], generators)  # + "VS", "VU"

    return test_chunks
