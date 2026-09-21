##################################
# priv/extensions/InterruptsCommon.py
#
# Shared interrupt test generation for InterruptsS and InterruptsSm.
# David_Harris@hmc.edu 6 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""Shared interrupt test generators"""

from collections.abc import Callable
from itertools import combinations

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

machine_ints = {"MEI": 11, "MTI": 7, "MSI": 3}
supervisor_ints = {"LCOFI": 13, "SEI": 9, "STI": 5, "SSI": 1, "VSEI": 10, "VSTI": 6, "VSSI": 2}
# Interrupts raised by writing a pending bit directly instead of through the platform (cp_trigger_reg)
reg_ints = {"MIP_SEIP": 9, "MIP_SSIP": 1, "SIP_SSIP": 1}
# STI raised through stimecmp with menvcfg.STCE = 0 or 1 (cp_trigger_sti_sstc)
sstc_ints = {"SSTC_STCE0": 5, "SSTC_STCE1": 5}
# mip/mie bit position of every interrupt type
int_bit = machine_ints | supervisor_ints | reg_ints | sstc_ints
# Guard symbol and coverpoint for types that do not use the UDB_<int>_INTR_IMPL / cp_trigger defaults
int_guard = {"MIP_SEIP": "UDB_SEI_INTR_IMPL", "MIP_SSIP": "UDB_SSI_INTR_IMPL", "SIP_SSIP": "UDB_SSI_INTR_IMPL"}
int_guard |= {name: "SSTC_SUPPORTED" for name in sstc_ints}
int_coverpoint = {name: "cp_trigger_reg" for name in reg_ints}
int_coverpoint |= {name: "cp_trigger_sti_sstc" for name in sstc_ints}


def guard_symbol(int_type: str) -> str:
    """Preprocessor symbol that must be defined for ``int_type`` to be raised on the target."""
    return int_guard.get(int_type, f"UDB_{int_type}_INTR_IMPL")


# TODO: remove once https://github.com/riscv/riscv-unified-db/pull/1963 is merged and UDB emits these
# from the MEI/MTI/MSI/SEI/STI/SSI_INTR_IMPL parameters. UDB_LCOFI_INTR_IMPL stays derived from
# SSCOFPMF_SUPPORTED in tests/env/derived_config.h.  VS*I_INTR_IMPL also need to be added to UDB.
# These defines precede the riscv_arch_test.h include, so rvtest_config.h (include-guarded) is pulled
# in first to make S_SUPPORTED and H_SUPPORTED visible to the guards below.
INTR_IMPL_DEFINES = [
    '#include "rvtest_config.h"',
    "#define UDB_MEI_INTR_IMPL",
    "#define UDB_MTI_INTR_IMPL",
    "#define UDB_MSI_INTR_IMPL",
    "#ifdef S_SUPPORTED",
    "#define UDB_SEI_INTR_IMPL",
    "#define UDB_STI_INTR_IMPL",
    "#define UDB_SSI_INTR_IMPL",
    "#endif // S_SUPPORTED",
    "#ifdef H_SUPPORTED",
    "#define UDB_VSEI_INTR_IMPL",
    "#define UDB_VSTI_INTR_IMPL",
    "#define UDB_VSSI_INTR_IMPL",
    "#endif // H_SUPPORTED",
]

# RVTEST_SET/CLR_<name>_INT_<priv> macro name (tests/env/utils.h) for each interrupt type.
# Types missing here have no trigger macros yet; their UDB_<int>_INTR_IMPL guard is never defined.
int_macro = {"MEI": "MEXT", "MTI": "MTIME", "MSI": "MSW", "SEI": "SEXT", "STI": "STIME", "SSI": "SSW"}
int_macro |= {name: name for name in ["LCOFI", *reg_ints, *sstc_ints]}

# RVTEST_SET/CLR_<name>_INT_<priv> for the register-triggered interrupts. M-mode writes mip and sip
# directly, S-mode writes sip directly and mip through T-SBI, and U-mode uses T-SBI for both.
REG_TRIGGER_DEFINES = [
    "#define RVTEST_SET_MIP_SEIP_INT_M li a1, 1<<9; csrs mip, a1",
    "#define RVTEST_CLR_MIP_SEIP_INT_M li a1, 1<<9; csrc mip, a1",
    "#define RVTEST_SET_MIP_SSIP_INT_M csrsi mip, 1<<1",
    "#define RVTEST_CLR_MIP_SSIP_INT_M csrci mip, 1<<1",
    "#define RVTEST_SET_SIP_SSIP_INT_M csrsi sip, 1<<1",
    "#define RVTEST_CLR_SIP_SSIP_INT_M csrci sip, 1<<1",
    "#define RVTEST_SET_MIP_SEIP_INT_S RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<9)",
    "#define RVTEST_CLR_MIP_SEIP_INT_S RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<9)",
    "#define RVTEST_SET_MIP_SSIP_INT_S RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<1)",
    "#define RVTEST_CLR_MIP_SSIP_INT_S RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<1)",
    "#define RVTEST_SET_SIP_SSIP_INT_S csrsi sip, 1<<1",
    "#define RVTEST_CLR_SIP_SSIP_INT_S csrci sip, 1<<1",
    "#define RVTEST_SET_MIP_SEIP_INT_U RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<9)",
    "#define RVTEST_CLR_MIP_SEIP_INT_U RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<9)",
    "#define RVTEST_SET_MIP_SSIP_INT_U RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<1)",
    "#define RVTEST_CLR_MIP_SSIP_INT_U RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<1)",
    "#define RVTEST_SET_SIP_SSIP_INT_U RVTEST_TSBI_CSR_SET(CSR_SIP, 1<<1)",
    "#define RVTEST_CLR_SIP_SSIP_INT_U RVTEST_TSBI_CSR_CLEAR(CSR_SIP, 1<<1)",
    # LCOFI has no platform source; raise and clear it through mip.LCOFIP
    "#define RVTEST_SET_LCOFI_INT_M li a1, 1<<13; csrs mip, a1",
    "#define RVTEST_CLR_LCOFI_INT_M li a1, 1<<13; csrc mip, a1",
    "#define RVTEST_SET_LCOFI_INT_S RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<13)",
    "#define RVTEST_CLR_LCOFI_INT_S RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<13)",
    "#define RVTEST_SET_LCOFI_INT_U RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<13)",
    "#define RVTEST_CLR_LCOFI_INT_U RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<13)",
]

# RVTEST_SET/CLR_SSTC_STCE<n>_INT_<priv>: write menvcfg.STCE, then raise STI through stimecmp; clearing
# also restores STCE = 0. stimecmp is written from M-mode (directly or through T-SBI) because S-mode
# access traps when STCE = 0. On RV32 the STCE bit is in menvcfgh.
SSTC_TRIGGER_DEFINES = [
    "#if __riscv_xlen == 64",
    "#define RVTEST_SET_SSTC_STCE0_INT_M li a1, 1<<63; csrc menvcfg, a1; RVTEST_SET_SSTC_INT_M",
    "#define RVTEST_SET_SSTC_STCE1_INT_M li a1, 1<<63; csrs menvcfg, a1; RVTEST_SET_SSTC_INT_M",
    "#define RVTEST_CLR_SSTC_STCE0_INT_M RVTEST_CLR_SSTC_INT_M; li a1, 1<<63; csrc menvcfg, a1",
    "#define RVTEST_CLR_SSTC_STCE1_INT_M RVTEST_CLR_SSTC_INT_M; li a1, 1<<63; csrc menvcfg, a1",
    "#define RVTEST_SET_SSTC_STCE0_INT_S RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFG, 1<<63); RVTEST_SET_SSTC_INT_U",
    "#define RVTEST_SET_SSTC_STCE1_INT_S RVTEST_TSBI_CSR_SET(CSR_MENVCFG, 1<<63); RVTEST_SET_SSTC_INT_U",
    "#define RVTEST_CLR_SSTC_STCE0_INT_S RVTEST_CLR_SSTC_INT_U; RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFG, 1<<63)",
    "#define RVTEST_CLR_SSTC_STCE1_INT_S RVTEST_CLR_SSTC_INT_U; RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFG, 1<<63)",
    "#else",
    "#define RVTEST_SET_SSTC_STCE0_INT_M li a1, 1<<31; csrc menvcfgh, a1; RVTEST_SET_SSTC_INT_M",
    "#define RVTEST_SET_SSTC_STCE1_INT_M li a1, 1<<31; csrs menvcfgh, a1; RVTEST_SET_SSTC_INT_M",
    "#define RVTEST_CLR_SSTC_STCE0_INT_M RVTEST_CLR_SSTC_INT_M; li a1, 1<<31; csrc menvcfgh, a1",
    "#define RVTEST_CLR_SSTC_STCE1_INT_M RVTEST_CLR_SSTC_INT_M; li a1, 1<<31; csrc menvcfgh, a1",
    "#define RVTEST_SET_SSTC_STCE0_INT_S RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFGH, 1<<31); RVTEST_SET_SSTC_INT_U",
    "#define RVTEST_SET_SSTC_STCE1_INT_S RVTEST_TSBI_CSR_SET(CSR_MENVCFGH, 1<<31); RVTEST_SET_SSTC_INT_U",
    "#define RVTEST_CLR_SSTC_STCE0_INT_S RVTEST_CLR_SSTC_INT_U; RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFGH, 1<<31)",
    "#define RVTEST_CLR_SSTC_STCE1_INT_S RVTEST_CLR_SSTC_INT_U; RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFGH, 1<<31)",
    "#endif",
    "#define RVTEST_SET_SSTC_STCE0_INT_U RVTEST_SET_SSTC_STCE0_INT_S",
    "#define RVTEST_SET_SSTC_STCE1_INT_U RVTEST_SET_SSTC_STCE1_INT_S",
    "#define RVTEST_CLR_SSTC_STCE0_INT_U RVTEST_CLR_SSTC_STCE0_INT_S",
    "#define RVTEST_CLR_SSTC_STCE1_INT_U RVTEST_CLR_SSTC_STCE1_INT_S",
]

# Privilege needed to access a CSR, keyed by name prefix, and privilege held by each test mode.
# HS-mode can reach h* and vs* CSRs directly; VS-mode reaches only its own s* aliases.
_CSR_LEVEL = {"m": 3, "h": 2, "vs": 2, "s": 1}
_MODE_LEVEL = {"M": 3, "S": 2, "VS": 1, "U": 0, "VU": 0}

# Mode each suite boots into, and the preprocessor symbol required for each test mode.
# InterruptsS requires S and therefore U, so only the virtualized modes need a guard there.
_BOOT_MODE = {"InterruptsSm": "M", "InterruptsS": "S"}
_MODE_GUARD = {
    "InterruptsSm": {"M": None, "S": "S_SUPPORTED", "U": "U_SUPPORTED", "VS": "H_SUPPORTED", "VU": "H_SUPPORTED"},
    "InterruptsS": {"S": None, "U": None, "VS": "H_SUPPORTED", "VU": "H_SUPPORTED"},
}

Generator = Callable[[TestData, list[TestChunk], str, str], None]


def _csr_level(instr: str) -> int:
    """Privilege level of the CSR named in a csr* instruction (0 for unprivileged CSRs)."""
    mnemonic, operands = instr.split("#", 1)[0].split(None, 1)
    fields = [f.strip() for f in operands.split(",")]
    csr = fields[1] if mnemonic.startswith("csrr") else fields[0]
    for prefix, level in _CSR_LEVEL.items():
        if csr.startswith(prefix):
            return level
    return 0


def csr_access(instr: str, mode: str) -> str:
    """A CSR instruction issued directly when ``mode`` can access the CSR, otherwise through T-SBI.

    U-mode reaches m*, s*, h*, and vs* CSRs through T-SBI; S-mode reaches m* CSRs through T-SBI.
    """
    return instr if _MODE_LEVEL[mode] >= _csr_level(instr) else tsbi_call(instr)


def guard_open(suite: str, priv: str) -> list[str]:
    """#ifdef line for tests that run in ``priv``, or nothing when the mode is always present."""
    guard = _MODE_GUARD[suite][priv]
    return [f"#ifdef {guard}"] if guard else []


def guard_close(suite: str, priv: str) -> list[str]:
    """Matching #endif for guard_open; must be emitted in the same test chunk."""
    guard = _MODE_GUARD[suite][priv]
    return [f"#endif // {guard}"] if guard else []


def mode_enter(suite: str, priv: str) -> list[str]:
    """Switch from the suite's boot mode into ``priv``.

    Emitted at the start of every chunk because chunks may be split into separate files,
    each of which boots afresh. Clobbers a0 only.
    """
    if priv == _BOOT_MODE[suite]:
        return []
    return [f"RVTEST_TSBI_GOTO_{priv}MODE # enter {priv}-mode"]


def mode_exit(suite: str, priv: str) -> list[str]:
    """Return from ``priv`` to the suite's boot mode at the end of a chunk. Clobbers a0 only."""
    boot = _BOOT_MODE[suite]
    if priv == boot:
        return []
    return [f"RVTEST_TSBI_GOTO_{boot}MODE # return to {boot}-mode"]


# Per-suite setup shared by cp_enable and cp_priority: the interrupts to raise, the pending and enable
# CSRs, the global enable written in the suite's boot mode, and the default delegation setup.
# InterruptsSm clears mideleg so every interrupt is enabled by mie alone.
_SETUP = {
    "InterruptsSm": {
        "types": [*machine_ints, *supervisor_ints],
        # MEI and SEI usually share one PLIC source, so priority pairs raise SEI through mip.SEIP instead
        "priority_types": ["MEI", "MTI", "MSI", "MIP_SEIP", "STI", "SSI", "LCOFI"],
        "ip": "mip",
        "ie": "mie",
        "status": {"csr": "mstatus", "mask": 0x88, "field": "MIE"},
        # cp_wfi: wake on the machine timer, enabled by mie.MTIE, pending in mip.MTIP
        "wfi": {
            "guard": "UDB_MTI_INTR_IMPL",
            "timer": "MTIME",
            "ie": ("MTIE", 0x80),
            "ip": ("mip", "MTIP", 0x80),
            "stce": False,
        },
        "deleg": ["#ifdef S_SUPPORTED", "csrw mideleg, zero # mideleg = zeros", "#endif // S_SUPPORTED"],
    },
    "InterruptsS": {
        "types": [*supervisor_ints],
        "priority_types": ["SEI", "STI", "SSI", "LCOFI"],
        "ip": "sip",
        "ie": "sie",
        "status": {"csr": "sstatus", "mask": 0x22, "field": "SIE"},
        # cp_wfi: wake on the Sstc supervisor timer, enabled by sie.STIE, pending in sip.STIP
        "wfi": {
            "guard": "SSTC_SUPPORTED",
            "timer": "SSTC",
            "ie": ("STIE", 0x20),
            "ip": ("sip", "STIP", 0x20),
            "stce": True,
        },
        "deleg": [],
    },
}


def _generate_cp_enable(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Raise each interrupt with only its enable bit set, then with every enable bit but its own."""

    ######################################
    coverpoint = "cp_enable"
    ######################################
    setup = _SETUP[suite]
    ie = setup["ie"]
    status = setup["status"]
    tc = test_data.new_test_chunk(test_chunks, "enable")
    tc.section_header = comment_banner(
        coverpoint,
        f"Enable each interrupt in {priv} mode with {status['csr']}.{status['field']} = 1, {ie} = only/others",
    )
    tc.code += guard_open(suite, priv)
    tmp_reg = test_data.int_regs.get_register()

    for int_type in setup["types"]:
        if int_type not in int_macro:
            continue  # no RVTEST_SET/CLR macros for this interrupt yet
        macro = int_macro[int_type]
        guard = guard_symbol(int_type)
        bit = int_bit[int_type]
        # enable only this interrupt (fires), then every interrupt except this one (does not fire)
        for enable, ie_val in [("only", 1 << bit), ("others", ~(1 << bit))]:
            tc.code += [
                f"#ifdef {guard}",
                *setup["deleg"],
                f"LI(x{tmp_reg}, {status['mask']:#x})",
                f"csrs {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 1",
                f"LI(x{tmp_reg}, {ie_val})",
                f"csrw {ie}, x{tmp_reg} # {ie} = {int_type} {enable}",
                test_data.add_testcase(f"priv_{priv}_{int_type}_{ie}_{enable}", coverpoint, f"{suite}_cg"),
                *mode_enter(suite, priv),
                f"RVTEST_SET_{macro}_INT_{priv} # Set the interrupt",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupt to fire",
                f"RVTEST_CLR_{macro}_INT_{priv} # Clear the interrupt if the interrupt handler hasn't done so",
                *mode_exit(suite, priv),
                f"#endif // {guard}",
                "",
            ]

    test_data.int_regs.return_register(tmp_reg)
    tc.code += guard_close(suite, priv)


def _raise(raised: list[str], pair: list[str], op: str, priv: str) -> list[str]:
    """RVTEST_<op>_<int>_INT_<priv> lines (op = SET or CLR) for every interrupt in ``raised``.

    The case that calls this is already wrapped in the guard symbols of both members of ``pair``,
    so their lines need no guard. In the ie flavor ``raised`` also includes every other interrupt,
    and each of those is wrapped in its own guard so a target that lacks it (for example S-level
    interrupts without S-mode) does not reference a macro or trap-handler routine it does not have.
    """
    lines = []
    for int_type in raised:
        line = f"RVTEST_{op}_{int_macro[int_type]}_INT_{priv} # {op} {int_type}"
        if int_type in pair:
            lines.append(line)
        else:
            lines += [f"#ifdef {guard_symbol(int_type)}", line, f"#endif // {guard_symbol(int_type)}"]
    return lines


def generate_cp_priority(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str, vary: str) -> None:
    """Raise pairs of interrupts so the higher priority one is taken first.

    ``vary`` is the CSR that distinguishes the pair: "ip" (pair pending, all enabled), "ie" (all pending,
    pair enabled), or "mideleg" (pair pending and enabled, one of the pair delegated).
    """
    setup = _SETUP[suite]
    ie = setup["ie"]
    status = setup["status"]
    csr = {"ip": setup["ip"], "ie": ie, "mideleg": "mideleg"}[vary]
    ######################################
    coverpoint = f"cp_priority_{csr}"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, f"priority_{csr}")
    tc.section_header = comment_banner(
        coverpoint,
        f"Priority of pairs of interrupts distinguished by {csr} in {priv} mode that are otherwise enabled and pending",
    )
    tc.code += guard_open(suite, priv)
    tmp_reg = test_data.int_regs.get_register()

    types = setup["priority_types"]
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
        # mideleg: one case per delegatable member of the pair, delegating that member;
        # otherwise a single case with nothing delegated
        delegations: list[str | None] = [None]
        if vary == "mideleg":
            delegations = []
            for member in pair:
                if member in delegatable:
                    delegations.append(member)
        for deleg in delegations:
            deleg_lines = setup["deleg"]
            bin_name = f"priv_{priv}_{first}_{second}"
            if deleg is not None:
                deleg_lines = [
                    "#ifdef S_SUPPORTED",
                    f"LI(x{tmp_reg}, {1 << int_bit[deleg]:#x})",
                    f"csrw mideleg, x{tmp_reg} # mideleg = {deleg}",
                    "#endif // S_SUPPORTED",
                ]
                bin_name += f"_deleg_{deleg}"
            tc.code += [
                f"#ifdef {guard_symbol(first)}",
                f"#ifdef {guard_symbol(second)}",
                *deleg_lines,
                f"LI(x{tmp_reg}, {status_mask:#x})",
                f"csrs {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = 1",
                f"LI(x{tmp_reg}, 0)",
                f"csrw {ie}, x{tmp_reg} # {ie} = 0",
                test_data.add_testcase(bin_name, coverpoint, f"{suite}_cg"),
                *mode_enter(suite, priv),
                *_raise(raised, pair, "SET", priv),
                # enable after everything is pending so the pair is arbitrated together, not raced by latency
                f"LI(x{tmp_reg}, {ie_after})",
                csr_access(f"csrw {ie}, x{tmp_reg} # {ie} = {ie_after:#x}", priv),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg}) # Wait for interrupts to fire in priority order",
                *_raise(raised, pair, "CLR", priv),
                *mode_exit(suite, priv),
                f"#endif // {guard_symbol(second)}",
                f"#endif // {guard_symbol(first)}",
                "",
            ]

    test_data.int_regs.return_register(tmp_reg)
    tc.code += guard_close(suite, priv)


def _generate_cp_priority_pending(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Priority of pending interrupts: pair pending, all enabled."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "ip")


def _generate_cp_priority_enable(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """Priority of enabled interrupts: all pending, pair enabled."""
    generate_cp_priority(test_data, test_chunks, suite, priv, "ie")


def write_stce(enable: bool, mode: str, tmp_reg: int) -> list[str]:
    """Set or clear menvcfg.STCE (menvcfgh on RV32) from ``mode``, through T-SBI when below M."""
    op = "csrs" if enable else "csrc"
    return [
        f"LI(x{tmp_reg}, 1)",
        "#if __riscv_xlen == 64",
        f"slli x{tmp_reg}, x{tmp_reg}, 63 # STCE in msb",
        csr_access(f"{op} menvcfg, x{tmp_reg} # menvcfg.STCE = {int(enable)}", mode),
        "#else",
        f"slli x{tmp_reg}, x{tmp_reg}, 31 # STCE in msb",
        csr_access(f"{op} menvcfgh, x{tmp_reg} # menvcfgh.STCE = {int(enable)}", mode),
        "#endif",
    ]


def _generate_cp_wfi(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """WFI waits for a timer interrupt whether or not the interrupt is globally enabled."""

    ######################################
    coverpoint = "cp_wfi"
    ######################################
    setup = _SETUP[suite]
    wfi = setup["wfi"]
    boot = _BOOT_MODE[suite]
    # With S-mode implemented, U-mode WFI traps after a bounded time (cp_wfi_timeout), so it cannot wait
    if priv == "U" and boot == "S":
        return
    status = setup["status"]
    ie_name, ie_mask = wfi["ie"]
    ip_csr, ip_name, ip_mask = wfi["ip"]
    tc = test_data.new_test_chunk(test_chunks, f"wfi_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"WFI until the timer interrupt in {priv} mode with {status['csr']}.{status['field']} = 0/1",
    )
    tc.code += guard_open(suite, priv)
    if priv == "U":
        tc.code.append("#ifndef S_SUPPORTED // U-mode WFI only waits when S-mode is not implemented")
    count_reg, tmp_reg = test_data.int_regs.get_registers(2)

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
                *setup["deleg"],
                *(write_stce(True, boot, tmp_reg) if wfi["stce"] else []),
                f"LI(x{tmp_reg}, 0x200000)",
                csr_access(f"{twcmd} mstatus, x{tmp_reg} # mstatus.TW = {tw}", boot),
                f"LI(x{tmp_reg}, {status['mask']:#x})",
                f"{enablecmd} {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = {enable}",
                f"LI(x{tmp_reg}, {ie_mask:#x})",
                f"csrw {setup['ie']}, x{tmp_reg} # {setup['ie']}.{ie_name} = 1",
                test_data.add_testcase(f"priv_{priv}_tw_{tw}_{status['field']}_{enable}", coverpoint, f"{suite}_cg"),
                *mode_enter(suite, priv),
                # Below M-mode the SOON macro reaches the timer through T-SBI traps; RVMODEL_TIMER_INT_SOON_DELAY
                # is sized so the interrupt cannot fire before those return and the trap count is sampled.
                f"RVTEST_SET_{wfi['timer']}_INT_SOON_{priv} # timer interrupt after RVMODEL_TIMER_INT_SOON_DELAY",
                # Every trap, including the interrupt, bumps rvtest_trap_count. Sample it after the last
                # trap of the setup so that any later change means the timer interrupt was taken.
                f"LA(x{count_reg}, rvtest_trap_count)",
                f"LREG x{count_reg}, 0(x{count_reg}) # trap count before waiting",
                # WFI may return before the timer fires (it may even be a no-op), so repeat it until the interrupt
                # has arrived. Check before each WFI: if the interrupt was already taken, a WFI would sleep with
                # nothing left to wake it.
                "1:",
                f"LA(x{tmp_reg}, rvtest_trap_count)",
                f"LREG x{tmp_reg}, 0(x{tmp_reg})",
                f"bne x{tmp_reg}, x{count_reg}, 2f # timer interrupt taken",
                *(
                    []
                    if taken
                    # Masked here, the interrupt is never taken, so the trap count never changes; WFI still
                    # wakes once it is pending, which is the only observable sign that it fired.
                    else [
                        f"csrr x{tmp_reg}, {ip_csr}",
                        f"andi x{tmp_reg}, x{tmp_reg}, {ip_mask:#x} # {ip_csr}.{ip_name}",
                        f"bnez x{tmp_reg}, 2f # timer interrupt pending but masked",
                    ]
                ),
                "wfi",
                "j 1b",
                "2:",
                f"RVTEST_CLR_{wfi['timer']}_INT_{priv} # Clear the timer interrupt",
                *mode_exit(suite, priv),
                f"#endif // {wfi['guard']}",
                "",
            ]

    test_data.int_regs.return_registers([count_reg, tmp_reg])
    if priv == "U":
        tc.code.append("#endif // S_SUPPORTED")
    tc.code += guard_close(suite, priv)


def _generate_cp_wfi_timeout(test_data: TestData, test_chunks: list[TestChunk], suite: str, priv: str) -> None:
    """With nothing pending, WFI below M-mode times out and traps as an illegal instruction.

    mstatus.TW = 1 makes any lower mode trap; with S-mode implemented, U-mode traps even with TW = 0.
    """

    ######################################
    coverpoint = "cp_wfi_timeout"
    ######################################
    if priv == "M":
        return  # the timeout does not apply to M-mode
    setup = _SETUP[suite]
    boot = _BOOT_MODE[suite]
    status = setup["status"]
    ie_name, ie_mask = setup["wfi"]["ie"]
    tc = test_data.new_test_chunk(test_chunks, f"wfi_timeout_{priv}")
    tc.section_header = comment_banner(
        coverpoint,
        f"WFI timeout in {priv} mode with {status['csr']}.{status['field']} = 0/1 x {setup['ie']}.{ie_name} = 0/1",
    )
    tc.code += guard_open(suite, priv)
    tmp_reg = test_data.int_regs.get_register()

    for tw in [1, 0] if priv == "U" else [1]:
        twcmd = "csrs" if tw == 1 else "csrc"
        for enable in [0, 1]:
            for ie in [0, 1]:
                enablecmd = "csrs" if enable == 1 else "csrc"
                tc.code += [
                    *(
                        ["#ifdef S_SUPPORTED // U-mode WFI also times out with TW = 0 when S-mode exists"]
                        if tw == 0
                        else []
                    ),
                    f"LI(x{tmp_reg}, 0x200000)",
                    csr_access(f"{twcmd} mstatus, x{tmp_reg} # mstatus.TW = {tw}", boot),
                    f"LI(x{tmp_reg}, {status['mask']:#x})",
                    f"{enablecmd} {status['csr']}, x{tmp_reg} # {status['csr']}.{status['field']} = {enable}",
                    f"LI(x{tmp_reg}, {ie * ie_mask:#x})",
                    f"csrw {setup['ie']}, x{tmp_reg} # {setup['ie']}.{ie_name} = {ie}",
                    test_data.add_testcase(
                        f"priv_{priv}_tw_{tw}_{status['field']}_{enable}_{ie_name}_{ie}", coverpoint, f"{suite}_cg"
                    ),
                    *mode_enter(suite, priv),
                    "wfi # nothing is pending, so this times out and traps as an illegal instruction",
                    *mode_exit(suite, priv),
                    *(["#endif // S_SUPPORTED"] if tw == 0 else []),
                    "",
                ]

    test_data.int_regs.return_register(tmp_reg)
    tc.code += guard_close(suite, priv)


# Coverpoints common to both suites, in emission order; each suite prepends its own cp_trigger.
SHARED_GENERATORS: list[Generator] = [
    _generate_cp_enable,
    _generate_cp_priority_pending,
    _generate_cp_priority_enable,
    _generate_cp_wfi,
    _generate_cp_wfi_timeout,
]


def emit_interrupts(
    test_data: TestData, test_chunks: list[TestChunk], suite: str, privs: list[str], generators: list[Generator]
) -> list[TestChunk]:
    """Run each coverpoint generator for every privilege mode, keeping each coverpoint's chunks contiguous."""

    for generate in generators:
        for priv in privs:
            generate(test_data, test_chunks, suite, priv)

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
