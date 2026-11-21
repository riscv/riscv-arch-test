##################################
# priv/extensions/InterruptsCommon.py
#
# Shared interrupt test generation for InterruptsS and InterruptsSm.
# David_Harris@hmc.edu 6 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""Shared interrupt test generators"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.asm.wait import wait_loop, wait_loop_arm
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

machine_ints = {"MEI": 11, "MTI": 7, "MSI": 3}
supervisor_ints = {"LCOFI": 13, "SEI": 9, "STI": 5, "SSI": 1}
# Interrupts raised by writing a pending bit directly instead of through the platform (cp_trigger_reg)
reg_ints = {"MIP_SEIP": 9, "MIP_SSIP": 1, "SIP_SSIP": 1, "SIP_LCOFIP": 13}
# STI raised through stimecmp with menvcfg.STCE = 1, and with STCE = 0, where the same stimecmp
# write must not raise it (cp_trigger_sti_sstc)
sstc_ints = {"SSTC_STCE0": 5, "SSTC_STCE1": 5}
# VS-level interrupts, raised through hvip. hideleg is left at its boot value of 0, so they trap to HS-mode.
vs_ints = {"VSEI": 10, "VSTI": 6, "VSSI": 2}
# mip/mie bit position of every interrupt type
int_bit = machine_ints | supervisor_ints | reg_ints | sstc_ints | vs_ints
# Interrupts that RVTEST_SET_<int>_INT raises with a CSR write (mip, sip or hvip), directly or through
# T-SBI, so an enabled one is taken right after that write (or the T-SBI xRET) and its xEPC is checked.
# SSI and SEI may be raised through the platform (RVMODEL_SET_SSW_INT, RVMODEL_SET_SEXT_INT), and MSI,
# MTI and MEI always are, so they become pending after an unspecified delay.
csr_raised_ints = reg_ints | vs_ints | {"LCOFI": 13, "STI": 5}
# Guard symbol and coverpoint for types that do not use the UDB_<int>_INTR_IMPL / cp_trigger defaults
int_guard = {"MIP_SEIP": "UDB_SEI_INTR_IMPL", "MIP_SSIP": "UDB_SSI_INTR_IMPL", "SIP_SSIP": "UDB_SSI_INTR_IMPL"}
int_guard |= {"LCOFI": "SSCOFPMF_SUPPORTED", "SIP_LCOFIP": "SSCOFPMF_SUPPORTED"}
int_guard |= {name: "SSTC_SUPPORTED" for name in sstc_ints}
# H makes every hvip bit writable, so each VS-level interrupt can be raised whenever H is implemented
int_guard |= {name: "H_SUPPORTED" for name in vs_ints}
# sip.LCOFIP writes land in the plain cp_trigger cross; the other register writes have their own crosses.
int_coverpoint = {
    "MIP_SEIP": "cp_trigger_reg_mip_seip",
    "MIP_SSIP": "cp_trigger_reg_mip_ssip",
    "SIP_SSIP": "cp_trigger_reg_sip_ssip",
}
int_coverpoint |= {name: "cp_trigger_sti_sstc" for name in sstc_ints}


def label_coverpoint(
    suite: "InterruptSuite", coverpoint: str, priv: str, int_type: str = "", delegated: bool = False
) -> str:
    """Coverpoint a testcase label names: ``coverpoint``, or its ``_tsbi`` twin when the coverage model
    records the case on the T-SBI xret back to the test (the interrupt is raised through T-SBI because
    ``priv`` cannot reach its pending bit). Mirrors the tsbi ignore_bins of <suite>_coverage.svh.
    """
    lower = priv != suite.boot
    # Below HS, VS-mode and VU-mode reach the interrupt sources as U-mode does, and the VS-level
    # interrupts are raised through T-SBI because only M-mode and HS-mode write hvip.
    below_s = priv in ("U", "VS", "VU")
    if suite.boot == "M":  # InterruptsSm
        tsbi = {
            "cp_trigger": (lower and int_type in ("MSI", "MTI"))
            or (below_s and int_type in ("STI", "LCOFI", "SIP_LCOFIP", *vs_ints))
            or (priv == "S" and int_type in ("LCOFI", "SIP_LCOFIP") and not delegated),
            "cp_trigger_sti_sstc": below_s and int_type == "SSTC_STCE1",
            "cp_enable_one": (lower and int_type in ("MSI", "MTI", "STI", "LCOFI"))
            or (below_s and int_type in vs_ints),
            "cp_priority_mip": lower,
            "cp_priority_mie": lower,
            "cp_priority_mideleg": lower,
        }
    else:  # InterruptsS
        tsbi = {
            "cp_trigger": below_s and int_type in ("STI", "LCOFI", "SIP_LCOFIP", *vs_ints),
            "cp_trigger_sti_sstc": below_s and int_type == "SSTC_STCE1",
            "cp_enable_one": int_type in ("STI", "LCOFI") or (below_s and int_type in vs_ints),
            "cp_priority_sip": lower,
            "cp_priority_sie": lower,
        }
    return f"{coverpoint}_tsbi" if tsbi.get(coverpoint, False) else coverpoint


def guard_symbol(int_type: str) -> str:
    """Preprocessor symbol that must be defined for ``int_type`` to be raised on the target."""
    return int_guard.get(int_type, f"UDB_{int_type}_INTR_IMPL")


# RVTEST_SET/CLR_<name>_INT_<priv> macro name (tests/env/utils.h) for each interrupt type.
# M-mode cases emit RVTEST_SET_*_INT_M alongside RVTEST_CLR_*_INT_M so the platform
# _M hooks (raw csrw, no T-SBI) are used for both raise and claim.
int_macro = {"MEI": "MEXT", "MTI": "MTIME", "MSI": "MSW", "SEI": "SEXT", "STI": "STIME", "SSI": "SSW"}
int_macro |= {name: name for name in ["LCOFI", *reg_ints, *sstc_ints]}
int_macro |= {"VSEI": "VSEXT", "VSTI": "VSTIME", "VSSI": "VSSW"}


def flavor(priv: str) -> str:
    """Mode whose RVTEST_SET/CLR_<name>_INT_<mode> macros and CSR accesses a test running in ``priv`` uses.

    VS-mode and VU-mode act as U-mode: the S-level CSR names reach the VS CSRs there, so the HS-mode
    and M-mode interrupt CSRs are reached through T-SBI.
    """
    return "U" if priv in ("VS", "VU") else priv


@dataclass(frozen=True)
class InterruptSuite:
    """Per-suite setup shared by the interrupt coverpoint generators."""

    name: str
    boot: str  # mode the suite boots into and returns to after each case
    types: list[str]  # interrupts raised by cp_enable
    priority_types: list[str]  # interrupts paired by cp_priority
    ip: str  # pending CSR
    ie: str  # enable CSR
    status: dict  # global enable written in the boot mode: csr, mask, field
    wfi: dict  # cp_wfi timer: guard, timer macro, ie (name, mask), ip (csr, name, mask), stce
    deleg: list[str]  # default delegation setup before each case
    hie: bool = False  # also write the enables to hie, which holds the VS-level enables that sie cannot reach

    @property
    def covergroup(self) -> str:
        """Covergroup that samples this suite's testcases."""
        return f"{self.name}_cg"


Generator = Callable[[TestData, list[TestChunk], InterruptSuite, str], None]


def write_ie(suite: InterruptSuite, reg: int, comment: str) -> list[str]:
    """Write x``reg`` to the suite's enable CSR and, with H, to hie, whose VS-level bits share their positions."""
    lines = [f"csrw {suite.ie}, x{reg} # {suite.ie} = {comment}"]
    if suite.hie:
        lines += ["#ifdef H_SUPPORTED", f"csrw hie, x{reg} # hie = {comment}", "#endif // H_SUPPORTED"]
    return lines


def mode_enter(suite: InterruptSuite, priv: str) -> list[str]:
    """Switch from the suite's boot mode into ``priv``.

    Emitted at the start of every chunk because chunks may be split into separate files,
    each of which boots afresh. Clobbers a0 only.
    """
    if priv == suite.boot:
        return []
    return [f"RVTEST_TSBI_GOTO_{priv}MODE # enter {priv}-mode"]


def mode_exit(suite: InterruptSuite, priv: str) -> list[str]:
    """Return from ``priv`` to the suite's boot mode at the end of a chunk. Clobbers a0 only."""
    if priv == suite.boot:
        return []
    return [f"RVTEST_TSBI_GOTO_{suite.boot}MODE # return to {suite.boot}-mode"]


def int_xepc_arm(reg: int) -> list[str]:
    """Make the trap handler record xEPC in the trap signature entry of each interrupt.

    Emit right before the CSR write or xRET that enables an interrupt that is already pending (or the
    CSR write that raises an enabled one). Such an interrupt must be taken before the next instruction
    (norm:intr_mip_mie_xret_csrwr), so its xEPC is the same on every hart. Interrupts that arrive after
    an unspecified delay must not be taken while armed. The rule is new in Priv 1.12, so earlier harts
    may take the interrupt a few instructions later and are not checked.
    """
    return [
        "#ifdef SM1P12P0_OR_LATER_SUPPORTED",
        f"LA(x{reg}, rvtest_int_xepc)",
        f"SREG x{reg}, 0(x{reg}) # arm: the trap handler records the xEPC of interrupts",
        "#endif // SM1P12P0_OR_LATER_SUPPORTED",
    ]


def int_xepc_disarm(label: str, reg: int) -> list[str]:
    """Stop recording xEPC (see int_xepc_arm). ``label`` is the instruction after the CSR write or xRET,
    where the interrupts it enables are taken; the handler of one returns there and its xRET enables the
    next, which is taken there too. An interrupt taken in the two instructions before the disarming store
    records its late xEPC, and a later one records 0, so both mismatch.
    """
    return [
        f"{label}: # an interrupt enabled by the previous instruction is taken here",
        "#ifdef SM1P12P0_OR_LATER_SUPPORTED",
        f"LA(x{reg}, rvtest_int_xepc)",
        f"SREG x0, 0(x{reg}) # disarm",
        "#endif // SM1P12P0_OR_LATER_SUPPORTED",
    ]


def generate_cp_enable(test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str) -> None:
    """Raise each interrupt with only its enable bit set, then with every enable bit but its own."""

    ######################################
    banner = "cp_enable_one / cp_enable_zero"
    ######################################
    ie = suite.ie
    status = suite.status
    tc = test_data.new_test_chunk(test_chunks, f"enable_{priv}")
    tc.section_header = comment_banner(
        banner,
        f"Enable each interrupt in {priv} mode with {status['csr']}.{status['field']} = 1, {ie} = only/others",
    )
    tmp_reg = test_data.int_regs.get_register()

    for int_type in suite.types:
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        bit = int_bit[int_type]
        # enable only this interrupt (fires), then every interrupt except this one (does not fire)
        for enable, ie_val in [("only", 1 << bit), ("others", ~(1 << bit))]:
            # A CSR write raises these, so an enabled one is taken right after it: check its xEPC
            checked = enable == "only" and int_type in csr_raised_ints
            tc.code += [
                f"#ifdef {guard}",
                *suite.deleg,
                f"LI(x{tmp_reg}, {status['mask']:#x})",
                f"csrs {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 1",
                f"LI(x{tmp_reg}, {ie_val})",
                *write_ie(suite, tmp_reg, f"{int_type} {enable}"),
                test_data.add_testcase(
                    f"priv_{priv}_{int_type}_{ie}_{enable}",
                    label_coverpoint(suite, "cp_enable_one", priv, int_type) if enable == "only" else "cp_enable_zero",
                    suite.covergroup,
                ),
                *mode_enter(suite, priv),
                *(int_xepc_arm(tmp_reg) if checked else []),
                f"RVTEST_SET_{macro}_INT_{flavor(priv)} # Set the interrupt",
                *(int_xepc_disarm(f"cp_enable_priv_{priv}_{int_type}_{ie}_{enable}_xepc", tmp_reg) if checked else []),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupt to fire",
                f"RVTEST_CLR_{macro}_INT_{flavor(priv)} # Clear the interrupt if the interrupt handler hasn't done so",
                *mode_exit(suite, priv),
                f"#endif // {guard}",
                "",
            ]

    test_data.int_regs.return_register(tmp_reg)


def _raise(raised: list[str], pair: list[str], op: str, priv: str) -> list[str]:
    """RVTEST_<op>_<int>_INT_<priv> lines (op = SET or CLR) for every interrupt in ``raised``.

    The case that calls this is already wrapped in the guard symbols of both members of ``pair``,
    so their lines need no guard. In the ie flavor ``raised`` also includes every other interrupt,
    and each of those is wrapped in its own guard so a target that lacks it (for example S-level
    interrupts without S-mode) does not reference a macro or trap-handler routine it does not have.
    """
    lines = []
    for int_type in raised:
        line = f"RVTEST_{op}_{int_macro[int_type]}_INT_{flavor(priv)} # {op} {int_type}"
        if int_type in pair:
            lines.append(line)
        else:
            lines += [f"#ifdef {guard_symbol(int_type)}", line, f"#endif // {guard_symbol(int_type)}"]
    return lines


def _enable_pair(suite: InterruptSuite, reg: int, value: int, pair: list[str], priv: str) -> list[str]:
    """Write x``reg`` to the enable CSR from ``priv`` and, with H in the S suite, to hie.

    Both members of the pair must be enabled by one write so that they are arbitrated together. When
    they share a CSR, the other CSR is written first and theirs last. When one is in sie and the other
    in hie, a single T-SBI set of mie (which holds both) enables them; sie and hie are 0 beforehand.
    """
    ie_line = tsbi_call_or_direct(f"csrw {suite.ie}, x{reg} # {suite.ie} = {value:#x}", flavor(priv))
    if not suite.hie:
        return [ie_line]
    if _split_pair(suite, pair):
        # the case is already inside the H_SUPPORTED guard of its VS-level member
        mask = value & sum(1 << int_bit[int_type] for int_type in suite.types)
        return [
            f"LI(x{reg}, {mask:#x})",
            tsbi_call(f"csrs mie, x{reg} # mie |= {mask:#x}: sie and hie at once"),
        ]
    hie_lines = [
        "#ifdef H_SUPPORTED",
        tsbi_call_or_direct(f"csrw hie, x{reg} # hie = {value:#x}", flavor(priv)),
        "#endif // H_SUPPORTED",
    ]
    return [ie_line, *hie_lines] if pair[0] in vs_ints else [*hie_lines, ie_line]


def _split_pair(suite: InterruptSuite, pair: list[str]) -> bool:
    """With H in the S suite, whether one member of ``pair`` is enabled in sie and the other in hie."""
    in_hie = [int_type in vs_ints for int_type in pair]
    return suite.hie and any(in_hie) and not all(in_hie)


def _priority_label(suite: InterruptSuite, coverpoint: str, priv: str, pair: list[str]) -> str:
    """Coverpoint a priority testcase label names. An S-mode test enables a split pair through T-SBI
    (_enable_pair), so the coverage model records it on the mret in <coverpoint>_split_tsbi.
    """
    if priv == suite.boot and _split_pair(suite, pair):
        return f"{coverpoint}_split_tsbi"
    return label_coverpoint(suite, coverpoint, priv)


def generate_cp_priority(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str, vary: str
) -> None:
    """Raise pairs of interrupts so the higher priority one is taken first.

    ``vary`` is the CSR that distinguishes the pair: "ip" (pair pending, all enabled), "ie" (all pending,
    pair enabled), or "mideleg" (pair pending and enabled, one of the pair delegated).
    """
    ie = suite.ie
    status = suite.status
    csr = {"ip": suite.ip, "ie": ie, "mideleg": "mideleg"}[vary]
    ######################################
    coverpoint = f"cp_priority_{csr}"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, f"priority_{csr}_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"Priority of pairs of interrupts distinguished by {csr} in {priv} mode that are otherwise enabled and pending",
    )
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)

    types = suite.priority_types
    if vary == "mideleg":
        # H makes the VS-level bits of mideleg read-only one, so only pairs of other interrupts vary it
        types = [int_type for int_type in types if int_type not in vs_ints]
    # delegated interrupts are only taken in S-mode with sstatus.SIE set
    status_mask = status["mask"] | 0x22 if vary == "mideleg" else status["mask"]
    # Only S-level interrupts can be delegated; the register-triggered ones share their bit positions
    supervisor_bits = supervisor_ints.values()
    delegatable = []
    for int_type in types:
        if int_bit[int_type] in supervisor_bits:
            delegatable.append(int_type)
    for first, second in combinations(types, 2):
        pair = [first, second]
        # ie: everything is pending and only the pair is enabled; otherwise only the pair is pending
        raised = types if vary == "ie" else pair
        # ie: enable only the pair; otherwise enable everything
        ie_after = (1 << int_bit[first]) | (1 << int_bit[second]) if vary == "ie" else -1
        raised_mask = sum({1 << int_bit[int_type] for int_type in raised})
        # mideleg: one case per delegatable member of the pair, delegating that member;
        # otherwise a single case with nothing delegated
        delegations: list[str | None] = [None]
        if vary == "mideleg":
            delegations = []
            for member in pair:
                if member in delegatable:
                    delegations.append(member)
        for deleg in delegations:
            deleg_lines = suite.deleg
            bin_name = f"priv_{priv}_{first}_{second}"
            if deleg is not None:
                deleg_lines = [
                    "#ifdef S_SUPPORTED",
                    f"LI(x{tmp_reg}, {1 << int_bit[deleg]:#x})",
                    f"csrw mideleg, x{tmp_reg} # mideleg = {deleg}",
                    "#endif // S_SUPPORTED",
                ]
                bin_name += f"_deleg_{deleg}"
            # The instruction that enables the pending pair is last, so they are arbitrated together and
            # taken in priority order, before the next instruction. It is the write to the enable CSR
            # (through T-SBI below the CSR's mode, so the T-SBI xRET enables them). In the boot mode,
            # the pending flavor also runs with the global enable (mstatus.MIE or sstatus.SIE) written last.
            for last in ["ie", "status"] if vary == "ip" and priv == suite.boot else ["ie"]:
                case_name = bin_name if last == "ie" else f"{bin_name}_status_last"
                if last == "ie":
                    setup = [
                        f"LI(x{tmp_reg}, {status_mask:#x})",
                        f"csrs {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 1",
                        f"LI(x{tmp_reg}, 0)",
                        *write_ie(suite, tmp_reg, "0"),
                    ]
                    enable = [
                        f"LI(x{tmp_reg}, {ie_after})",
                        *_enable_pair(suite, tmp_reg, ie_after, pair, priv),
                    ]
                else:
                    setup = [
                        f"LI(x{tmp_reg}, {status_mask:#x})",
                        f"csrc {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 0",
                        f"LI(x{tmp_reg}, {ie_after})",
                        *write_ie(suite, tmp_reg, f"{ie_after:#x}"),
                    ]
                    enable = [
                        f"LI(x{tmp_reg}, {status_mask:#x})",
                        f"csrs {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 1",
                    ]
                tc.code += [
                    f"#ifdef {guard_symbol(first)}",
                    f"#ifdef {guard_symbol(second)}",
                    *deleg_lines,
                    *setup,
                    *mode_enter(suite, priv),
                    *_raise(raised, pair, "SET", priv),
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait until every raised interrupt is pending",
                    test_data.add_testcase(case_name, _priority_label(suite, coverpoint, priv, pair), suite.covergroup),
                    tsbi_call_or_direct(f"csrr x{check_reg}, {suite.ip}", flavor(priv)),
                    *(
                        [
                            "#ifdef H_SUPPORTED",
                            tsbi_call_or_direct(f"csrr x{tmp_reg}, hip", flavor(priv)),
                            f"or x{check_reg}, x{check_reg}, x{tmp_reg} # the VS-level pending bits are in hip",
                            "#endif // H_SUPPORTED",
                        ]
                        if suite.hie
                        else []
                    ),
                    f"LI(x{tmp_reg}, {raised_mask:#x})",
                    f"and x{check_reg}, x{check_reg}, x{tmp_reg} # raised interrupts that are pending",
                    write_sigupd(check_reg, test_data),
                    *int_xepc_arm(tmp_reg),
                    *enable,
                    *int_xepc_disarm(f"{coverpoint}_{case_name}_xepc", tmp_reg),
                    *_raise(raised, pair, "CLR", priv),
                    *mode_exit(suite, priv),
                    f"#endif // {guard_symbol(second)}",
                    f"#endif // {guard_symbol(first)}",
                    "",
                ]

    test_data.int_regs.return_registers([tmp_reg, check_reg])


def generate_cp_priority_pending(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """Priority of pending interrupts: pair pending, all enabled."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "ip")


def generate_cp_priority_enable(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """Priority of enabled interrupts: all pending, pair enabled."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "ie")


def generate_cp_xret_same_mode(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """xRET from the boot mode back to itself restores the global enable from xPIE.

    One interrupt is pending and enabled in the enable CSR, but masked by mstatus.MIE = 0 (sstatus.SIE = 0).
    With xPIE = 1 the xRET enables it, so it is taken at the xRET's target, the next instruction
    (norm:intr_mip_mie_xret_csrwr). With xPIE = 0 it stays masked. VS-level interrupts are never taken
    in M-mode, so InterruptsSm records no interrupt for them.
    """

    ######################################
    coverpoint = "cp_xret_same_mode"
    ######################################
    m = suite.boot == "M"
    csr = suite.status["csr"]
    xie, xpie, xpp = ("MIE", "MPIE", "MPP") if m else ("SIE", "SPIE", "SPP")
    xepc, xret = ("mepc", "mret") if m else ("sepc", "sret")
    ie_bit, pie_bit, pp_bits = (0x8, 0x80, 0x1800) if m else (0x2, 0x20, 0x100)
    tc = test_data.new_test_chunk(test_chunks, f"xret_same_mode_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"{xret} to {priv}-mode with {csr}.{xie} = 0, {xpie} = 0/1 and one pending interrupt enabled in {suite.ie}",
    )
    tmp_reg = test_data.int_regs.get_register()

    for int_type in suite.types:
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        for pie in [0, 1]:
            case_name = f"priv_{priv}_{int_type}_{xpie.lower()}_{pie}"
            label = f"{coverpoint}_{case_name}_xepc"
            tc.code += [
                f"#ifdef {guard}",
                *suite.deleg,
                f"LI(x{tmp_reg}, {ie_bit:#x})",
                f"csrc {csr}, x{tmp_reg} # {csr}.{xie} = 0",
                f"LI(x{tmp_reg}, {1 << int_bit[int_type]:#x})",
                *write_ie(suite, tmp_reg, f"{int_type} only"),
                test_data.add_testcase(case_name, coverpoint, suite.covergroup),
                f"RVTEST_SET_{macro}_INT_{priv} # pending, masked by {csr}.{xie} = 0",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait until the interrupt is pending",
                f"LI(x{tmp_reg}, {pie_bit:#x})",
                f"{'csrs' if pie else 'csrc'} {csr}, x{tmp_reg} # {csr}.{xpie} = {pie}",
                f"LI(x{tmp_reg}, {pp_bits:#x})",
                f"csrs {csr}, x{tmp_reg} # {csr}.{xpp} = {priv}",
                *(
                    []
                    if m
                    else [
                        "#ifdef H_SUPPORTED",
                        f"LI(x{tmp_reg}, 0x80)",
                        f"csrc hstatus, x{tmp_reg} # hstatus.SPV = 0: sret stays in HS-mode",
                        "#endif // H_SUPPORTED",
                    ]
                ),
                f"LA(x{tmp_reg}, {label})",
                f"csrw {xepc}, x{tmp_reg} # {xret} to the next instruction",
                *int_xepc_arm(tmp_reg),
                f"{xret} # {csr}.{xie} = {xpie} = {pie}",
                *int_xepc_disarm(label, tmp_reg),
                f"RVTEST_CLR_{macro}_INT_{priv} # Clear the interrupt if the handler hasn't done so",
                f"#endif // {guard}",
                "",
            ]

    test_data.int_regs.return_register(tmp_reg)


def generate_cp_undeleg(test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str) -> None:
    """A delegation write that takes back a pending, enabled interrupt.

    InterruptsSm in M-mode delegates one S-level interrupt with mideleg, and InterruptsS in HS-mode one
    VS-level interrupt with hideleg, so the pending interrupt is not taken in the current mode. Clearing
    the delegation bit makes it a pending, enabled interrupt of the current mode, which is taken before
    the next instruction (norm:intr_mip_mie_xret_csrwr).
    """

    m = suite.boot == "M"
    deleg_csr, deleg_guard = ("mideleg", "S_SUPPORTED") if m else ("hideleg", "H_SUPPORTED")
    ######################################
    coverpoint = f"cp_undeleg_{deleg_csr}"
    ######################################
    csr = suite.status["csr"]
    xie, ie_bit = ("MIE", 0x8) if m else ("SIE", 0x2)
    # mideleg delegates the S-level interrupts (SEI raised through mip.SEIP, as in cp_priority);
    # hideleg delegates the VS-level ones
    types = ["MIP_SEIP", "STI", "SSI", "LCOFI"] if m else list(vs_ints)
    tc = test_data.new_test_chunk(test_chunks, f"undeleg_{deleg_csr}_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"Clear the {deleg_csr} bit of a pending interrupt enabled by {suite.ie} = 1s and {csr}.{xie} = 1 in {priv}-mode",
    )
    tmp_reg = test_data.int_regs.get_register()

    tc.code.append(f"#ifdef {deleg_guard}")
    for int_type in types:
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        case_name = f"priv_{priv}_{int_type}"
        label = f"{coverpoint}_{case_name}_xepc"
        tc.code += [
            f"#ifdef {guard}",
            f"LI(x{tmp_reg}, {1 << int_bit[int_type]:#x})",
            f"csrw {deleg_csr}, x{tmp_reg} # {deleg_csr} = {int_type}",
            f"LI(x{tmp_reg}, -1)",
            *write_ie(suite, tmp_reg, "1s"),
            f"LI(x{tmp_reg}, {ie_bit:#x})",
            f"csrs {csr}, x{tmp_reg} # {csr}.{xie} = 1",
            test_data.add_testcase(case_name, coverpoint, suite.covergroup),
            f"RVTEST_SET_{macro}_INT_{priv} # pending, but delegated below {priv}-mode",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait until the interrupt is pending",
            *int_xepc_arm(tmp_reg),
            f"csrw {deleg_csr}, zero # {int_type} is now taken in {priv}-mode",
            *int_xepc_disarm(label, tmp_reg),
            f"RVTEST_CLR_{macro}_INT_{priv} # Clear the interrupt if the handler hasn't done so",
            f"#endif // {guard}",
            "",
        ]
    tc.code.append(f"#endif // {deleg_guard}")

    test_data.int_regs.return_register(tmp_reg)


def generate_cp_wfi(test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str) -> None:
    """WFI waits for a timer interrupt whether or not the interrupt is globally enabled.

    Not for U-mode when S-mode is implemented: U-mode WFI then traps after a bounded time (cp_wfi_timeout).
    Not for VU-mode either, where WFI with mstatus.TW = 0 always raises a virtual-instruction exception.
    VS-mode WFI waits with hstatus.VTW = 0 (cp_wfi_vs).
    """

    ######################################
    coverpoint = "cp_wfi"
    ######################################
    wfi = suite.wfi
    boot = suite.boot
    status = suite.status
    ie_name, ie_mask = wfi["ie"]
    ip_csr, _, ip_mask = wfi["ip"]
    tc = test_data.new_test_chunk(test_chunks, f"wfi_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"WFI until the timer interrupt in {priv} mode with {status['csr']}.{status['field']} = 0/1",
    )
    if priv == "U":
        tc.code.append("#ifndef S_SUPPORTED // U-mode WFI only waits when S-mode is not implemented")
    addr_reg, tmp_reg = test_data.int_regs.get_registers(2)

    # mstatus.TW only affects modes below M, so sweep it in M-mode where it must not matter
    for tw in [0, 1] if priv == "M" else [0]:
        for enable in [0, 1]:
            twcmd = "csrs" if tw == 1 else "csrc"
            enablecmd = "csrs" if enable == 1 else "csrc"
            # The interrupt is taken unless it is masked in the boot mode itself (M with MIE = 0, or the
            # S-mode suite with SIE = 0); lower modes take it regardless of the global enable.
            taken = enable == 1 or priv != boot
            tc.code += [
                f"#ifdef {wfi['guard']}",
                *suite.deleg,
                *(write_stce(test_data, True, boot) if wfi["stce"] else []),
                f"LI(x{tmp_reg}, 0x200000)",
                tsbi_call_or_direct(f"{twcmd} mstatus, x{tmp_reg} # mstatus.TW = {tw}", boot),
                *(_write_vtw(tmp_reg, False, boot) if priv == "VS" else []),
                f"LI(x{tmp_reg}, {status['mask']:#x})",
                f"{enablecmd} {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = {enable}",
                f"LI(x{tmp_reg}, {ie_mask:#x})",
                f"csrw {suite.ie}, x{tmp_reg} # {suite.ie}.{ie_name} = 1",
                test_data.add_testcase(
                    f"priv_{priv}_tw_{tw}_{status['field']}_{enable}",
                    # InterruptsSm records M-mode WFI in cp_wfi_m; both suites record VS-mode WFI in cp_wfi_vs
                    {"M": "cp_wfi_m", "VS": "cp_wfi_vs"}.get(priv, coverpoint),
                    suite.covergroup,
                ),
                *mode_enter(suite, priv),
                *wait_loop_arm(test_data, addr_reg, tmp_reg),
                f"RVTEST_SET_{wfi['timer']}_INT_SOON_{flavor(priv)} # timer interrupt after RVMODEL_TIMER_INT_SOON_DELAY",
                # WFI may return before the timer fires (it may even be a no-op), so repeat it until the
                # interrupt has arrived. Masked here, the interrupt is never taken, but WFI still wakes once
                # it is pending, which is the only observable sign that it fired.
                *wait_loop(test_data, tmp_reg, ["wfi"], None if taken else (ip_csr, ip_mask)),
                f"RVTEST_CLR_{wfi['timer']}_INT_{flavor(priv)} # Clear the timer interrupt",
                *mode_exit(suite, priv),
                f"#endif // {wfi['guard']}",
                "",
            ]

    test_data.int_regs.return_registers([addr_reg, tmp_reg])
    if priv == "U":
        tc.code.append("#endif // S_SUPPORTED")


def generate_cp_trigger_vsti_sstc(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """VSTI through vstimecmp, armed like STI in cp_trigger_sti_sstc: vstimecmp = 0 fires at once.

    With hie.VSTIE = 1, VS-mode takes STI when hideleg.VSTI = 1, and HS-mode takes VSTI otherwise.  The boot mode
    (HS or M) writes vstimecmp, and VS-mode writes its own timer through stimecmp, which is vstimecmp there.  For
    U-mode and VU-mode, HS-mode writes vstimecmp and then enters them.  HS-mode takes an undelegated VSTI in place
    with sstatus.SIE = 1; M-mode never takes VSTI, so InterruptsSm enters VS-mode.  U-mode never takes a delegated
    VSTI, since V = 0.
    """

    ######################################
    coverpoint = "cp_trigger_vsti_sstc"
    ######################################
    boot = suite.boot
    in_vs = priv == "VS"
    tc = test_data.new_test_chunk(test_chunks, f"trigger_vsti_sstc_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        "With menvcfg.STCE = henvcfg.STCE = 1 and hie.VSTIE = 1, set "
        + ("stimecmp = 0 in VS-mode" if in_vs else f"vstimecmp = 0 in {boot}-mode, then run in {priv}-mode")
        + " x hideleg.VSTI = 0/1",
    )
    tmp_reg = test_data.int_regs.get_register()
    tc.code += [
        "#ifdef H_SUPPORTED",
        "#ifdef SSTC_SUPPORTED",
        *write_stce(test_data, True, boot),
        *write_stce(test_data, True, boot, henvcfg=True),
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrs vsstatus, x{tmp_reg} # vsstatus.SIE = 1",
        # vstimecmp has no reset value; all 1s keeps VSTIP clear until a case arms it
        f"RVTEST_CLR_VSSTC_INT_{boot}",
    ]
    for deleg in (0, 1):
        # Mode the test runs in while VSTIP is pending
        target = priv if priv != boot else "S" if boot == "S" and not deleg else "VS"
        enable = [f"LI(x{tmp_reg}, MIP_VSTIP)", f"csrw hie, x{tmp_reg} # hie.VSTIE = 1"]
        tc.code += [
            f"LI(x{tmp_reg}, {'MIP_VSTIP' if deleg else 0})",
            f"csrw hideleg, x{tmp_reg} # hideleg.VSTI = {deleg}",
        ]
        if in_vs:
            # vstimecmp is all 1s here, so enabling before VS-mode arms it cannot fire
            tc.code += [
                *enable,
                *mode_enter(suite, "VS"),
                test_data.add_testcase(f"priv_{priv}_hideleg_{deleg}", f"{coverpoint}_vs", suite.covergroup),
                "#if __riscv_xlen == 32",
                "csrw stimecmph, zero",
                "#endif",
                "csrw stimecmp, zero # stimecmp is vstimecmp in VS-mode",
            ]
        else:
            tc.code += [
                test_data.add_testcase(
                    f"priv_{priv}_hideleg_{deleg}",
                    coverpoint if priv == boot else f"{coverpoint}_tsbi",
                    suite.covergroup,
                ),
                f"RVTEST_SET_VSSTC_INT_{boot} # vstimecmp = 0",
                *enable,
                *(["csrsi sstatus, SSTATUS_SIE"] if target == "S" else []),
                *mode_enter(suite, target),
            ]
        tc.code += [
            f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupt to fire",
            *mode_exit(suite, target),
            *(["csrci sstatus, SSTATUS_SIE"] if target == "S" else []),
            "csrw hie, zero",
            f"RVTEST_CLR_VSSTC_INT_{boot}",
            "",
        ]
    tc.code += [
        "csrw hideleg, zero",
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrc vsstatus, x{tmp_reg} # vsstatus.SIE = 0",
        *write_stce(test_data, False, boot, henvcfg=True),
        *write_stce(test_data, False, boot),
        "#endif // SSTC_SUPPORTED",
        "#endif // H_SUPPORTED",
        "",
    ]
    test_data.int_regs.return_register(tmp_reg)


def _write_vtw(reg: int, vtw: bool, boot: str) -> list[str]:
    """Set or clear hstatus.VTW from the boot mode."""
    return [
        f"LI(x{reg}, HSTATUS_VTW)",
        tsbi_call_or_direct(f"{'csrs' if vtw else 'csrc'} hstatus, x{reg} # hstatus.VTW = {int(vtw)}", boot),
    ]


# (mstatus.TW, hstatus.VTW) cases of cp_wfi_timeout in each mode, and the coverpoint of each case.  None leaves
# VTW alone.  Below M, TW = 1 makes WFI time out and raise illegal instruction.  U-mode WFI also times out with
# TW = 0 when S-mode is implemented.  VS-mode WFI with TW = 0 and VTW = 1 times out and raises virtual
# instruction; with VTW = 0 it waits (cp_wfi_vs).  VU-mode WFI with TW = 0 raises virtual instruction whatever
# VTW is.
_WFI_TIMEOUT_CASES = {
    "S": [(1, None, "cp_wfi_timeout")],
    "U": [(1, None, "cp_wfi_timeout"), (0, None, "cp_wfi_timeout_tw_zero")],
    "VS": [(1, False, "cp_wfi_timeout_vs"), (1, True, "cp_wfi_timeout_vs"), (0, True, "cp_wfi_timeout_vs_vtw_one")],
    "VU": [
        (1, False, "cp_wfi_timeout_vu"),
        (1, True, "cp_wfi_timeout_vu"),
        (0, False, "cp_wfi_timeout_vu"),
        (0, True, "cp_wfi_timeout_vu"),
    ],
}


def generate_cp_wfi_timeout(
    test_data: TestData, test_chunks: list[TestChunk], suite: InterruptSuite, priv: str
) -> None:
    """With nothing pending, WFI below M-mode times out and traps (see _WFI_TIMEOUT_CASES)."""

    ######################################
    coverpoint = "cp_wfi_timeout"
    ######################################
    status = suite.status
    ie_name, ie_mask = suite.wfi["ie"]
    tc = test_data.new_test_chunk(test_chunks, f"wfi_timeout_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"WFI timeout in {priv} mode with {status['csr']}.{status['field']} = 0/1 x {suite.ie}.{ie_name} = 0/1",
    )
    tmp_reg = test_data.int_regs.get_register()

    for tw, vtw, case_coverpoint in _WFI_TIMEOUT_CASES[priv]:
        twcmd = "csrs" if tw == 1 else "csrc"
        # U-mode WFI only times out with TW = 0 when S-mode exists
        guard = priv == "U" and tw == 0
        vtw_name = "" if vtw is None else f"_vtw_{int(vtw)}"
        for enable in [0, 1]:
            for ie in [0, 1]:
                enablecmd = "csrs" if enable == 1 else "csrc"
                tc.code += [
                    *(["#ifdef S_SUPPORTED"] if guard else []),
                    f"LI(x{tmp_reg}, 0x200000)",
                    tsbi_call_or_direct(f"{twcmd} mstatus, x{tmp_reg} # mstatus.TW = {tw}", suite.boot),
                    *([] if vtw is None else _write_vtw(tmp_reg, vtw, suite.boot)),
                    f"LI(x{tmp_reg}, {status['mask']:#x})",
                    f"{enablecmd} {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = {enable}",
                    f"LI(x{tmp_reg}, {ie * ie_mask:#x})",
                    f"csrw {suite.ie}, x{tmp_reg} # {suite.ie}.{ie_name} = {ie}",
                    test_data.add_testcase(
                        f"priv_{priv}_tw_{tw}{vtw_name}_{status['field']}_{enable}_{ie_name}_{ie}",
                        case_coverpoint,
                        suite.covergroup,
                    ),
                    *mode_enter(suite, priv),
                    "wfi # nothing is pending, so this times out and traps",
                    *mode_exit(suite, priv),
                    *([] if vtw is None else _write_vtw(tmp_reg, False, suite.boot)),
                    *(["#endif // S_SUPPORTED"] if guard else []),
                    "",
                ]

    test_data.int_regs.return_register(tmp_reg)


def emit_interrupts(
    test_data: TestData, suite: InterruptSuite, priv: str, generators: list[Generator]
) -> list[TestChunk]:
    """Run each coverpoint generator for one privilege mode."""
    test_chunks: list[TestChunk] = []
    for generate in generators:
        generate(test_data, test_chunks, suite, priv)

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
