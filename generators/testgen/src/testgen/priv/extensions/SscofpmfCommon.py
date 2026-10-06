##################################
# priv/extensions/SscofpmfCommon.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf (HPM counter overflow/interrupt) shared helpers.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Helpers shared by the Sscofpmf test generators: CSR access for a mode and counter 3 setup."""

import re

from testgen.asm.tsbi import tsbi_call

_FIXED_TSBI_ALIASES = {
    "RVMODEL_MHPMEVENT": "0x323",  # mhpmevent3
    "RVMODEL_MHPMCOUNTER": "0xb03",  # mhpmcounter3
    "scountovf": "0xda0",
}

# The S/U suites reach the counter through T-SBI calls encoded at generation time, and
# the RV32 high halves are named directly, so counter 3 is the only supported choice.
MACRO_CHECKS = [
    "#if !defined(RVMODEL_MHPMEVENT) || !defined(RVMODEL_MHPMCOUNTER) || \\",
    "    !defined(RVMODEL_MHPMEVENT_VAL) || !defined(RVMODEL_MHPMEVENT_CODE)",
    '  #error "Sscofpmf tests need RVMODEL_MHPMEVENT, RVMODEL_MHPMCOUNTER, RVMODEL_MHPMEVENT_VAL and RVMODEL_MHPMEVENT_CODE in rvmodel_macros.h"',
    "#endif",
    "#if (RVMODEL_MHPMEVENT != CSR_MHPMEVENT3) || (RVMODEL_MHPMCOUNTER != CSR_MHPMCOUNTER3)",
    '  #error "Sscofpmf tests only support counter 3: define RVMODEL_MHPMEVENT as CSR_MHPMEVENT3 and RVMODEL_MHPMCOUNTER as CSR_MHPMCOUNTER3"',
    "#endif",
    "",
]

_MHPMEVENT_RE = re.compile(r"\bCSR_MHPMEVENT(\d+)(H)?\b")
_MHPMCOUNTER_RE = re.compile(r"\bCSR_MHPMCOUNTER(\d+)(H)?\b")


def _resolve_tsbi_csr(instr: str) -> str:
    """Substitute Sscofpmf CSR names/macros with literal hex addresses for tsbi_call()."""
    for macro, hexaddr in _FIXED_TSBI_ALIASES.items():
        instr = instr.replace(macro, hexaddr)

    def _sub_mhpmevent(m: re.Match) -> str:
        n = int(m.group(1))
        base = 0x720 if m.group(2) else 0x320  # ...H = mhpmeventh (RV32 OF-bit high half)
        return hex(base + n)

    def _sub_mhpmcounter(m: re.Match) -> str:
        n = int(m.group(1))
        base = 0xB80 if m.group(2) else 0xB00  # ...H = mhpmcounterh (RV32 counter high half)
        return hex(base + n)

    instr = _MHPMEVENT_RE.sub(_sub_mhpmevent, instr)
    return _MHPMCOUNTER_RE.sub(_sub_mhpmcounter, instr)


_S_ACCESSIBLE_CSRS = ("sip", "sie", "sstatus", "scountovf")


def csr_access(instr: str, mode: str) -> str:
    """Direct at Sm, and at S for sip/sie/sstatus/scountovf. Everything else via T-SBI."""
    if mode == "Sm":
        return instr
    code = instr.split("#", 1)[0]
    if mode == "S" and any(re.search(rf"\b{name}\b", code) for name in _S_ACCESSIBLE_CSRS):
        return instr
    return tsbi_call(_resolve_tsbi_csr(instr))


def clear_lcofip(r_tmp: int, priv_mode: str) -> list[str]:
    """Clear a pending LCOFIP left by an earlier real overflow: through sip when S exists
    and the suite runs below M, else through mip."""
    set_bit = f"LI(x{r_tmp}, {hex(1 << 13)})"
    if priv_mode == "Sm":
        return [set_bit, f"csrc mip, x{r_tmp}   # clear LCOFIP"]
    if priv_mode == "S":
        return [set_bit, f"csrc sip, x{r_tmp}   # clear LCOFIP"]
    return [
        set_bit,
        "#ifdef S_SUPPORTED",
        csr_access(f"csrc sip, x{r_tmp}   # clear LCOFIP", priv_mode),
        "#else",
        csr_access(f"csrc mip, x{r_tmp}   # clear LCOFIP", priv_mode),
        "#endif",
    ]


# Every T-SBI call runs the M-mode handler, and a call from U is delegated through S
# first, so counting must be inhibited in every mode above the one under test or the
# counter would also count the round trip instead of just the workload.
HIGHER_MODE_INHIBITS = {"Sm": 0, "S": 1 << 62, "U": (1 << 62) | (1 << 61)}
HIGHER_MODE_INHIBITS_32 = {mode: bits >> 32 for mode, bits in HIGHER_MODE_INHIBITS.items()}

# On RV32, mhpmevent3h[23:0] holds RVMODEL_MHPMEVENT_VAL[55:32].
EVENT_VAL_HI = "(((RVMODEL_MHPMEVENT_VAL) >> 32) & 0xFFFFFF)"


def counted_since_all_ones(reg: int) -> list[str]:
    """Reduce x{reg}, a counter read after it was preset to all 1s, to 1 if it counted
    at least one event (it is no longer all 1s) and 0 if it did not. The count itself
    is not recorded, since how many events a workload generates is implementation-specific;
    one or more events always leaves the counter somewhere other than all 1s."""
    return [
        f"addi x{reg}, x{reg}, 1            # x{reg} = val + 1 (0 iff val is still all 1s)",
        f"snez x{reg}, x{reg}               # x{reg} = counted at least one event",
    ]


def write_event_pattern(r_val: int, r_hval: int, inhibit_pattern: int, priv_mode: str) -> list[str]:
    """Write RVMODEL_MHPMEVENT_VAL with the MINH/SINH/UINH/VSINH/VUINH pattern at bits
    62:58, OF=0. LI truncates to 32 bits on RV32, so the pattern never reaches the event
    high half through the RV64 form -- split the write across both halves there."""
    return [
        "#if __riscv_xlen == 32",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
        csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
        f"LI(x{r_hval}, {EVENT_VAL_HI} | ({inhibit_pattern} << 26))   # 58-32 = 26",
        csr_access(f"csrw CSR_MHPMEVENT3H, x{r_hval}", priv_mode),
        "#else",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({inhibit_pattern} << 58))   # OF starts at 0",
        csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
        "#endif",
    ]


def write_counter_all_ones(r_temp: int, priv_mode: str) -> list[str]:
    """Preload the logical 64-bit counter to all-1s so the next counted event overflows.
    On RV32 the counter is really two 32-bit halves; the high half must also be set or
    the 64-bit counter can't wrap."""
    return [
        f"LI(x{r_temp}, -1)",
        csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows", priv_mode),
        "#if __riscv_xlen == 32",
        csr_access(f"csrw CSR_MHPMCOUNTER3H, x{r_temp}   # high half must also be all 1s", priv_mode),
        "#endif",
    ]


def prime_counter_overflow(r_val: int, r_hval: int, r_temp: int, r_addr: int, priv_mode: str) -> list[str]:
    """Overflow RVMODEL_MHPMCOUNTER (OF 0 -> 1, raising LCOFIP). The counter is left at
    all 1s, so one counted event wraps it; the workload is what supplies that event on a
    model that counts. These coverpoints require an all-zero inhibit pattern, so below M
    the T-SBI round trip that writes the counter is counted too and may itself supply the
    wrapping event -- either way OF is set and LCOFIP pends before the sample point."""
    return [
        *write_event_pattern(r_val, r_hval, 0, priv_mode),
        *write_counter_all_ones(r_temp, priv_mode),
        f"LA(x{r_addr}, scratch)",
        f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
    ]


def stop_counter(mode: str) -> list[str]:
    """Stop counter 3 so it cannot overflow and set OF in a test file that starts from reset."""
    return [
        csr_access("csrw RVMODEL_MHPMEVENT, zero", mode),
        "#if __riscv_xlen == 32",
        csr_access("csrw CSR_MHPMEVENT3H, zero", mode),
        "#endif",
        "",
    ]
