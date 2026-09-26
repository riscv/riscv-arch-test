##################################
# priv/extensions/InterruptsSm.py
#
# InterruptsSm privileged extension test generator.
# David_Harris@hmc.edu 7 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""InterruptsSm privileged extension test generator for interrupts relying on M-mode."""

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import (
    Generator,
    InterruptSuite,
    emit_interrupts,
    generate_cp_enable,
    generate_cp_priority,
    generate_cp_priority_enable,
    generate_cp_priority_pending,
    generate_cp_wfi,
    generate_cp_wfi_timeout,
    guard_symbol,
    int_coverpoint,
    int_macro,
    machine_ints,
    mode_enter,
    mode_exit,
    reg_ints,
    sstc_ints,
    supervisor_ints,
)
from testgen.priv.registry import add_priv_test_generator

# Boots to M-mode. mideleg is cleared before each case so every interrupt is enabled by mie alone.
SUITE = InterruptSuite(
    name="InterruptsSm",
    boot="M",
    types=[*machine_ints, *supervisor_ints],
    # MEI and SEI usually share one PLIC source, so priority pairs raise SEI through mip.SEIP instead
    priority_types=["MEI", "MTI", "MSI", "MIP_SEIP", "STI", "SSI", "LCOFI"],
    ip="mip",
    ie="mie",
    status={"csr": "mstatus", "mask": 0x88, "field": "MIE"},
    # cp_wfi: wake on the machine timer, enabled by mie.MTIE, pending in mip.MTIP
    wfi={
        "guard": "UDB_MTI_INTR_IMPL",
        "timer": "MTIME",
        "ie": ("MTIE", 0x80),
        "ip": ("mip", "MTIP", 0x80),
        "stce": False,
    },
    deleg=["#ifdef S_SUPPORTED", "csrw mideleg, zero # mideleg = zeros", "#endif // S_SUPPORTED"],
)
COVERGROUP = SUITE.covergroup


def _generate_cp_trigger_sm(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
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
    tmp_reg = test_data.int_regs.get_register()

    for int_type in [*machine_ints, *supervisor_ints, *reg_ints, *sstc_ints]:
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
                            f"#ifdef UDB_MTVEC_MODES_{mode}",
                            *write_open,
                            f"LI(x{tmp_reg}, {mideleg})",
                            f"csrw mideleg, x{tmp_reg} # mideleg = {delegstr}",
                            *write_close,
                            f"LI(x{tmp_reg}, 1)",
                            f"{modecmd} mtvec, x{tmp_reg} # mtvec.mode = {mode}",
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
                            f"#endif // UDB_MTVEC_MODES_{mode}",
                            *case_close,
                            f"#endif // {guard}",
                            "",
                        ]

    test_data.int_regs.return_register(tmp_reg)


def _generate_cp_priority_mideleg(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """Priority of delegated interrupts: pair pending and enabled, one of them delegated."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "mideleg")


def _generate_cp_write_stip_sstc(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """With menvcfg.STCE = 1, mip.STIP follows stimecmp and ignores writes (M-mode only)."""

    ######################################
    coverpoint = "cp_write_stip_sstc"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, "write_stip_sstc")
    tc.section_header = comment_banner(
        coverpoint, "With menvcfg.STCE = 1, write stimecmp = 0s/1s x mip.STIP = 0/1 and read STIP back"
    )
    tmp_reg = test_data.int_regs.get_register()

    tc.code += [
        "#ifdef SSTC_SUPPORTED",
        "csrw mideleg, zero # mideleg = zeros",
        "csrw mie, zero # mie = 0 so a pending STIP is not taken",
        *write_stce(test_data, True, priv),
    ]
    for stimecmp, stimecmp_macro in [("zeros", "SET"), ("ones", "CLR")]:
        for stip, stip_macro in [(0, "CLR"), (1, "SET")]:
            tc.code += [
                f"RVTEST_{stimecmp_macro}_SSTC_INT_{priv} # stimecmp = {stimecmp}",
                test_data.add_testcase(f"priv_{priv}_stimecmp_{stimecmp}_STIP_{stip}", coverpoint, COVERGROUP),
                f"RVTEST_{stip_macro}_STIME_INT_{priv} # Write mip.STIP = {stip}",
                f"csrr x{tmp_reg}, mip # mip.STIP = 1 only when stimecmp = 0s",
                f"andi x{tmp_reg}, x{tmp_reg}, 0x20 # STIP",
                write_sigupd(tmp_reg, test_data),
                "",
            ]
    tc.code += ["#endif // SSTC_SUPPORTED", ""]

    test_data.int_regs.return_register(tmp_reg)


# Coverpoints for each test mode. cp_write_stip_sstc is M-only; cp_wfi_timeout does not apply to M-mode.
_GENERATORS: dict[str, list[Generator]] = {
    "M": [
        _generate_cp_trigger_sm,
        generate_cp_enable,
        generate_cp_priority_pending,
        generate_cp_priority_enable,
        generate_cp_wfi,
        _generate_cp_priority_mideleg,
        _generate_cp_write_stip_sstc,
    ],
}
_GENERATORS["S"] = _GENERATORS["U"] = [
    _generate_cp_trigger_sm,
    generate_cp_enable,
    generate_cp_priority_pending,
    generate_cp_priority_enable,
    generate_cp_wfi,
    generate_cp_wfi_timeout,
    _generate_cp_priority_mideleg,
]


# One generator per test mode, each requiring the extension for its mode, so no test file is
# compiled away entirely on a target without that mode.
@add_priv_test_generator(SUITE.name, required_extensions=["Sm"], extra_defines=["#define BOOT_TO_MMODE"])
def make_interruptssm_m(test_data: TestData) -> list[TestChunk]:
    """InterruptsSm tests that run in M-mode."""
    return emit_interrupts(test_data, SUITE, "M", _GENERATORS["M"])


@add_priv_test_generator(SUITE.name, required_extensions=["Sm", "S"], extra_defines=["#define BOOT_TO_MMODE"])
def make_interruptssm_s(test_data: TestData) -> list[TestChunk]:
    """InterruptsSm tests that run in S-mode."""
    return emit_interrupts(test_data, SUITE, "S", _GENERATORS["S"])


@add_priv_test_generator(SUITE.name, required_extensions=["Sm", "U"], extra_defines=["#define BOOT_TO_MMODE"])
def make_interruptssm_u(test_data: TestData) -> list[TestChunk]:
    """InterruptsSm tests that run in U-mode."""
    return emit_interrupts(test_data, SUITE, "U", _GENERATORS["U"])
