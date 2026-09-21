##################################
# priv/extensions/InterruptsS.py
#
# InterruptsS privileged extension test generator.
# David_Harris@hmc.edu 7 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""InterruptsS privileged extension test generator for interrupts not relying on M-mode."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import (
    INTR_IMPL_DEFINES,
    REG_TRIGGER_DEFINES,
    SHARED_GENERATORS,
    SSTC_TRIGGER_DEFINES,
    emit_interrupts,
    guard_close,
    guard_open,
    guard_symbol,
    int_coverpoint,
    int_macro,
    mode_enter,
    mode_exit,
    reg_ints,
    sstc_ints,
    supervisor_ints,
)
from testgen.priv.registry import add_priv_test_generator

SUITE = "InterruptsS"
COVERGROUP = f"{SUITE}_cg"


def _generate_cp_trigger_s(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Trigger each interrupt across stvec.MODE and sstatus.SIE."""

    ######################################
    banner = "cp_trigger / cp_trigger_reg / cp_trigger_sti_sstc"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, f"trigger_{priv}")
    tc.section_header = comment_banner(
        banner,
        f"Trigger each interrupt in {priv} mode with sie=1s x stvec.MODE=DIRECT/VECTORED x sstatus.SIE=0/1",
    )
    tc.code += guard_open(suite, priv)
    tmp_reg = test_data.int_regs.get_register()

    for int_type in [*supervisor_ints, *reg_ints, *sstc_ints]:
        if int_type not in int_macro:
            continue  # no RVTEST_SET/CLR macros for this interrupt yet
        if priv == "U" and int_type == "SSTC_STCE0":
            # Arming Sstc from U mode goes through T-SBI.  This suite boots to S mode with
            # medeleg delegating U-mode ecalls, so the S-mode handler services the request and
            # executes the stimecmp write at S privilege.  That access is illegal while
            # menvcfg.STCE = 0, and the trap fires inside the handler after it has swapped
            # sscratch, so re-entry overwrites the saved context instead of recording a test
            # trap.  InterruptsSm covers priv U with STCE = 0: it boots to M mode, leaving
            # medeleg = 0, so the same request reaches M mode where stimecmp is accessible.
            continue
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        cp = int_coverpoint.get(int_type, "cp_trigger")
        for mode in [0, 1]:
            for enable in [0, 1]:
                # stvec.MODE
                modecmd = "csrs" if mode == 1 else "csrc"
                enablecmd = "csrs" if enable == 1 else "csrc"
                tc.code += [
                    f"#ifdef {guard}",
                    f"LI(x{tmp_reg}, -1)",
                    f"csrw sie, x{tmp_reg} # sie = 1s",
                    f"#ifdef UDB_STVEC_MODES_{mode}",
                    f"LI(x{tmp_reg}, 1)",
                    f"{modecmd} stvec, x{tmp_reg} # stvec.mode = {mode}",
                    "#endif // stvec.MODE",
                    f"LI(x{tmp_reg}, 0x22) # SIE, SPIE",
                    f"{enablecmd} sstatus, x{tmp_reg} # sstatus.SIE = {enable}",
                    test_data.add_testcase(
                        f"priv_{priv}_{int_type}_mode_{mode}_enable_{enable}",
                        cp,
                        COVERGROUP,
                    ),
                    *mode_enter(suite, priv),
                    f"RVTEST_SET_{macro}_INT_{priv} # Set the interrupt",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupt to fire",
                    f"RVTEST_CLR_{macro}_INT_{priv} # Clear the interrupt if the handler hasn't done so",
                    *mode_exit(suite, priv),
                    f"#endif // {guard}",
                    "",
                ]

    test_data.int_regs.return_register(tmp_reg)
    tc.code += guard_close(suite, priv)


@add_priv_test_generator(
    SUITE,
    required_extensions=["S"],
    extra_defines=[*INTR_IMPL_DEFINES, *REG_TRIGGER_DEFINES, *SSTC_TRIGGER_DEFINES, "#define BOOT_TO_SMODE"],
)
def make_interruptss(test_data: TestData) -> list[TestChunk]:
    """Generate tests for InterruptsS interrupt behavior that does not rely on M-mode."""
    test_chunks: list[TestChunk] = []
    generators = [_generate_cp_trigger_s, *SHARED_GENERATORS]

    emit_interrupts(test_data, test_chunks, SUITE, ["S", "U"], generators)  # + "VS", "VU"

    return test_chunks
