##################################
# priv/extensions/pmp/partial.py
#
# PMP entries that match only part of a memory access.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Cases where the PMP entry that decides an access matches only some of its bytes.

The deciding entry is the lowest-numbered entry that matches any byte of the access. An aligned access of at
most XLEN bits, an aligned AMO, and a misaligned access inside a misaligned atomicity granule are each one
memory operation, so the access fails when the deciding entry does not match all of its bytes, whatever L, R,
W and X are.

A misaligned access that the hart performs in hardware fails when any of its bytes fails the PMP check. With a
region the access may not use on one side of it and no entry on the other, it faults whether or not the hart
splits it. The address in xtval depends on how the hart splits it, so these tests do not record it.

Each partial-match case uses its own 16-byte slot of PMP_PARTIAL_BASE and its own PMP entries, all below the
background entry, so an entry locked by one case never matches another case's slot.
coverpoints/priv/PMP_partial.svh classifies each access by the entries that match its bytes.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import cfg_byte, cfg_shift, set_pmpcfg, zero_pmp_regs

SLOT_BYTES = 16
_SLOTS = 40

#: Size of a TOR region of one grain.
GRAIN = "PMP_TOR_REGION_BYTES"

#: The cases use entries 0-13, and the background entry (with pmpaddr below it for a TOR background) the top two.
ENTRIES_PARAM = "NUM_USABLE_PMP_ENTRIES: '>=16'"

#: Trap handler switch that leaves xtval out of the trap record of a load or store access fault.
IMPRECISE_XTVAL = "#define IMPRECISE_ACCESS_FAULT_XTVAL"


@dataclass(frozen=True)
class Entry:
    """One PMP entry of a case. ``offset`` is the byte offset from PMP_PARTIAL_BASE written to pmpaddr."""

    index: int
    amode: str  # "off", "na4", "napot" (an 8-byte region) or "tor"
    offset: str
    lxwr: str


@dataclass(frozen=True)
class Case:
    name: str
    slot: int
    entries: tuple[Entry, ...]
    coverpoint: str | None = None  # overrides the chunk's coverpoint

    @property
    def base(self) -> int:
        return SLOT_BYTES * self.slot


def _placement(name: str, slot: int, first: int, lock: int, amode: str, center: int, size: str) -> Case:
    """Entries over the region below ``center``, the region above it, or both.

    ``name`` is ``lower``, ``upper`` or ``both``; the regions are ``size`` bytes, and ``center`` is a byte offset
    within the slot.
    """
    c = SLOT_BYTES * slot + center
    lxwr = f"{lock}111"
    if amode == "tor":
        regions = {
            "lower": [Entry(first, "off", f"{c} - {size}", "0000"), Entry(first + 1, "tor", f"{c}", lxwr)],
            "upper": [Entry(first, "off", f"{c}", "0000"), Entry(first + 1, "tor", f"{c} + {size}", lxwr)],
            "both": [
                Entry(first, "off", f"{c} - {size}", "0000"),
                Entry(first + 1, "tor", f"{c}", lxwr),
                Entry(first + 2, "tor", f"{c} + {size}", lxwr),
            ],
        }
    else:
        regions = {
            "lower": [Entry(first, amode, f"{c} - {size}", lxwr)],
            "upper": [Entry(first, amode, f"{c}", lxwr)],
            "both": [Entry(first, amode, f"{c} - {size}", lxwr), Entry(first + 1, amode, f"{c}", lxwr)],
        }
    return Case(f"{amode}_{name}_L{lock}", slot, tuple(regions[name]))


def _placements(first_slot: int, amode: str, center: int, size: str) -> list[Case]:
    """lower, upper and both, unlocked and then locked, each with fresh entries and its own slot."""
    cases, entry, slot = [], 0, first_slot
    for lock in (0, 1):
        for name in ("lower", "upper", "both"):
            case = _placement(name, slot, entry, lock, amode, center, size)
            cases.append(case)
            entry = case.entries[-1].index + 1
            slot += 1
    return cases


#: Aligned doublewords (slot base) partly matched by 4-byte NA4 entries.
ALIGNED_NA4: list[Case] = _placements(0, "na4", 4, "4")
#: A lower-numbered read-only NAPOT entry covers the whole doubleword, so it decides, not the NA4 entry.
COVERING: list[Case] = [
    Case(
        "napot_covers",
        6,
        (Entry(8, "napot", f"{SLOT_BYTES * 6}", "1001"), Entry(9, "na4", f"{SLOT_BYTES * 6}", "1111")),
        "cp_partial_covered",
    )
]
#: Aligned doublewords partly matched by 4-byte TOR entries (G = 0).
ALIGNED_TOR: list[Case] = _placements(8, "tor", 4, "4")
#: Aligned quadwords (slot base) partly matched by 8-byte NAPOT entries.
QUAD_NAPOT: list[Case] = _placements(16, "napot", 8, "8")
#: Aligned quadwords partly matched by 8-byte TOR entries (G <= 1).
QUAD_TOR: list[Case] = _placements(24, "tor", 8, "8")
#: Misaligned accesses that cross the middle of a 16-byte granule, partly matched by one-grain TOR entries.
GRANULE_TOR: list[Case] = _placements(32, "tor", 8, GRAIN)


def _check_layout() -> None:
    """Cases tested together use distinct entries, and all of them stay below the background entry."""
    for group in (ALIGNED_NA4 + COVERING, ALIGNED_TOR, QUAD_NAPOT, QUAD_TOR, GRANULE_TOR):
        indices = [e.index for case in group for e in case.entries]
        assert len(indices) == len(set(indices)) and max(indices) <= 13


_check_layout()


def _set_pmpaddr(entry: Entry) -> list[str]:
    lines = ["LA(x5, PMP_PARTIAL_BASE)", f"LI(x6, {entry.offset})", "add x5, x5, x6", "srl x5, x5, PMP_SHIFT"]
    return [*lines, f"csrw pmpaddr{entry.index}, x5"]


def _or_pmpcfg(index: int, value: str) -> list[str]:
    """Set one entry's configuration byte without touching the other entries in its pmpcfg CSR."""
    rv32_csr, rv64_csr = index // 4, (index // 8) * 2
    if rv32_csr == rv64_csr:
        return [f"LI(x4, {value})", f"csrs pmpcfg{rv32_csr}, x4"]
    return [
        f"LI(x4, {value})",
        "#if __riscv_xlen == 32",
        f"csrs pmpcfg{rv32_csr}, x4",
        "#else",
        f"csrs pmpcfg{rv64_csr}, x4",
        "#endif",
    ]


def case_setup(case: Case) -> list[str]:
    """Program a case's pmpaddr CSRs, then its configuration bytes."""
    lines = [f"// {case.name}: slot {case.slot}, entries {', '.join(str(e.index) for e in case.entries)}"]
    for entry in case.entries:
        lines.extend(_set_pmpaddr(entry))
    for entry in case.entries:
        if entry.amode != "off":
            lines.extend(_or_pmpcfg(entry.index, cfg_byte(entry.lxwr, entry.amode, cfg_shift(entry.index))))
    lines.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
    return lines


#: A probe emits the testcases for one case.
Probe = Callable[[TestData, Case, str, str], list[str]]

#: An instruction to probe and the preprocessor condition it needs, if any.
Access = tuple[str, str | None]

RV64 = "__riscv_xlen == 64"
RV64_D = "__riscv_xlen == 64 && defined(D_SUPPORTED)"

_FP_MOVES = {
    "flw": ("fmv.w.x", "fmv.x.w"),
    "fld": ("fmv.d.x", "fmv.x.d"),
    "fsw": ("fmv.w.x", ""),
    "fsd": ("fmv.d.x", ""),
}


def _access(instruction: str) -> tuple[list[str], tuple[int, ...]]:
    """Assembly for one access at (a5), and the registers to check afterwards.

    a4 is the load destination or store data. Compressed forms use the same registers, which are all in x8-x15
    and f8-f15.
    """
    fp = instruction.removeprefix("c.")
    if fp in _FP_MOVES:
        to_fp, from_fp = _FP_MOVES[fp]
        # f14 starts from a4 so that a faulting load leaves a known value.
        return [f"{to_fp} f14, a4", f"{instruction} f14, 0(a5)", *([f"{from_fp} a4, f14"] if from_fp else [])], (14,)
    if instruction.startswith("amocas."):
        # rd and rs2 are the x8/x9 and x14/x15 pairs when the operand is wider than XLEN.
        lines = ["LI(x8, RVTEST_PMP_RET_ENCODING)", "LI(x9, RVTEST_PMP_RET_ENCODING)", f"{instruction} x8, x14, (a5)"]
        return lines, (8, 9)
    if instruction.startswith("lr."):
        return [f"{instruction} a4, (a5)"], (14,)
    if instruction.startswith("sc."):
        # a3 receives the result only if the sc retires.
        return ["LI(a3, RVTEST_PMP_RET_ENCODING)", f"{instruction} a3, a4, (a5)", "mv a4, a3"], (14,)
    if instruction.startswith("amo"):
        return ["LI(a3, RVTEST_PMP_RET_ENCODING)", f"{instruction} a4, a3, (a5)"], (14,)
    return [f"{instruction} a4, 0(a5)"], (14,)


def gen_accesses(accesses: Sequence[Access], offset: str = "0", base: str = "PMP_PARTIAL_BASE") -> Probe:
    """Each access at ``base`` plus the case's slot plus ``offset``.

    a4 is preset so that a faulting access leaves a known value.
    """

    def probe(test_data: TestData, case: Case, coverpoint: str, suite: str) -> list[str]:
        lines = [f"LA(a5, {base})", f"LI(x6, {case.base} + {offset})", "add a5, a5, x6"]
        for instruction, condition in accesses:
            code, checked = _access(instruction)
            body = [
                "LI(a4, RVTEST_PMP_RET_ENCODING)",
                test_data.add_testcase(f"{case.name}_{instruction.replace('.', '_')}", coverpoint, suite),
                *code,
                *(write_sigupd(reg, test_data) for reg in checked),
            ]
            lines.extend([f"#if {condition}", *body, "#endif"] if condition else body)
        return lines

    return probe


def chain(*probes: Probe) -> Probe:
    """Run several probes for each case, in order."""

    def probe(test_data: TestData, case: Case, coverpoint: str, suite: str) -> list[str]:
        return [line for each in probes for line in each(test_data, case, coverpoint, suite)]

    return probe


def partial_blob() -> list[str]:
    """The slots, at the first 4 KiB boundary of .data like the other PMP regions."""
    return [".p2align 12", "PMP_PARTIAL_BASE:", f".rept {SLOT_BYTES * _SLOTS // 8}", ".dword 0", ".endr"]


def make_partial_chunk(
    test_data: TestData, name: str, cases: Sequence[Case], probe: Probe, coverpoint: str, description: str
) -> TestChunk:
    """One test file: clear the PMP, set the background entry, then set up and probe each case."""
    chunk = test_data.begin_test_chunk(name)
    chunk.section_header = comment_banner(coverpoint, description)
    chunk.code.extend([*zero_pmp_regs(), "", "RVTEST_PMP_SET_BACKGROUND x4", ""])
    for case in cases:
        case_coverpoint = case.coverpoint or coverpoint
        chunk.code.extend([*case_setup(case), *probe(test_data, case, case_coverpoint, test_data.testsuite), ""])
    chunk.raw_data.extend(partial_blob())
    return test_data.end_test_chunk()


#####################################################################
# Accesses inside a 16-byte granule (Zama16b)
#####################################################################

# GRANULE_TOR puts the region boundary at slot offset 8. Each access crosses it and stays in the slot.


def granule_accesses(
    halves: Sequence[Access] = (), words: Sequence[Access] = (), doubles: Sequence[Access] = ()
) -> Probe:
    """2-, 4- and 8-byte accesses that start 1, 2 and 4 bytes below the middle of the granule."""
    return chain(
        *(gen_accesses(group, offset) for group, offset in ((halves, "7"), (words, "6"), (doubles, "4")) if group)
    )


GRANULE_LDST = granule_accesses(
    [("lh", None), ("lhu", None), ("sh", None)],
    [("lw", None), ("sw", None), ("lwu", RV64)],
    [("ld", RV64), ("sd", RV64)],
)


#####################################################################
# Misaligned accesses performed in hardware (MISALIGNED_LDST)
#####################################################################

_MISALIGNED_REGION = "PMP_MISALIGNED_REGION"

_MISALIGNED_DEFINES = [
    "// Gaps of at least 8 bytes, so an 8-byte access that crosses into a gap reaches no entry beyond it.",
    "#if UDB_PMP_GRANULARITY > 2",
    "#define PMP_MISALIGNED_GAP PMP_TOR_REGION_BYTES",
    "#else",
    "#define PMP_MISALIGNED_GAP 8",
    "#endif",
]


def _boundary_ldst(boundary: str, double: str) -> Probe:
    """Loads and stores that cross the boundary ``boundary`` bytes above PMP_MISALIGNED_REGION.

    ld and sd start ``double`` bytes below it, so they cross only that boundary.
    """
    return chain(
        gen_accesses([("lh", None), ("lhu", None), ("sh", None)], f"{boundary} - 1", _MISALIGNED_REGION),
        gen_accesses([("lw", None), ("sw", None), ("lwu", RV64)], f"{boundary} - 2", _MISALIGNED_REGION),
        gen_accesses([("ld", RV64), ("sd", RV64)], f"{boundary} - {double}", _MISALIGNED_REGION),
    )


#: The region holds the upper bytes of each access (the boundary is its start) or the lower bytes (its end).
_MISALIGNED_CASES: list[tuple[Case, Probe]] = [
    (Case("upper", 0, ()), _boundary_ldst("0", "6")),
    (Case("lower", 0, ()), _boundary_ldst(GRAIN, "2")),
]


def misaligned_setup_m() -> list[str]:
    """Entry 1 is a locked TOR region of one grain without permissions. No other entry matches."""
    return [
        "// Entry 0: OFF, bottom of entry 1. Entry 1: TOR over one grain at PMP_MISALIGNED_REGION, L=1, XWR=000.",
        "// No background entry, so the rest of memory matches no entry and M-mode may access it.",
        f"LA(x5, {_MISALIGNED_REGION})",
        "srl x5, x5, PMP_SHIFT",
        "csrw pmpaddr0, x5",
        "LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)",
        "add x5, x5, x6",
        "csrw pmpaddr1, x5",
        *set_pmpcfg(1, cfg_byte("1000", "tor", cfg_shift(1))),
    ]


def misaligned_setup_lower() -> list[str]:
    """Entry 2 is a TOR region of one grain with XWR=111, and a gap that matches no entry lies on each side."""
    return [
        "// Entry 0: TOR [0, PMP_MISALIGNED_BASE). Entry 2: TOR over one grain at PMP_MISALIGNED_REGION.",
        "// Entry 4: TOR from PMP_MISALIGNED_GAP above the region to the top. All L=0, XWR=111. No background entry,",
        "// so the gap below the region and the gap above it match no entry.",
        "LA(x5, PMP_MISALIGNED_BASE)",
        "srl x5, x5, PMP_SHIFT",
        "csrw pmpaddr0, x5",
        f"LA(x5, {_MISALIGNED_REGION})",
        "srl x5, x5, PMP_SHIFT",
        "csrw pmpaddr1, x5",
        "LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)",
        "add x5, x5, x6",
        "csrw pmpaddr2, x5",
        "LI(x6, PMP_MISALIGNED_GAP >> PMP_SHIFT)",
        "add x5, x5, x6",
        "csrw pmpaddr3, x5",
        "LI(x5, -1)",
        "csrw pmpaddr4, x5",
        *set_pmpcfg(0, f"{cfg_byte('0111', 'tor', cfg_shift(0))} | {cfg_byte('0111', 'tor', cfg_shift(2))}"),
        *_or_pmpcfg(4, cfg_byte("0111", "tor", cfg_shift(4))),
    ]


def _misaligned_blob() -> list[str]:
    """A gap, the one-grain region and another gap, grain-aligned at the first 4 KiB boundary of .data."""
    zeros = [".word 0", ".endr"]
    return [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "PMP_MISALIGNED_BASE:",
        ".rept PMP_MISALIGNED_GAP / 4",
        *zeros,
        f"{_MISALIGNED_REGION}:",
        ".rept PMP_TOR_REGION_BYTES / 4",
        *zeros,
        ".rept PMP_MISALIGNED_GAP / 4",
        *zeros,
    ]


def make_misaligned_chunk(
    test_data: TestData, setup: list[str], coverpoint: str, description: str, *, lower_mode: str | None = None
) -> TestChunk:
    """Misaligned loads and stores across each end of one region, from M-mode or ``lower_mode``."""
    chunk = test_data.begin_test_chunk("misaligned_partial")
    chunk.section_header = comment_banner(coverpoint, description)
    chunk.code.extend([*_MISALIGNED_DEFINES, "", *zero_pmp_regs(), "", *setup, "RVTEST_SFENCE_VMA_IF_SUPPORTED"])
    if lower_mode:
        chunk.code.append(f"RVTEST_TSBI_GOTO_{lower_mode}MODE")
    for case, probe in _MISALIGNED_CASES:
        where = "start" if case.name == "upper" else "end"
        chunk.code.extend(["", f"// Across the {where} of the region: it holds the {case.name} bytes of each access"])
        chunk.code.extend(probe(test_data, case, coverpoint, test_data.testsuite))
    if lower_mode:
        chunk.code.append("RVTEST_TSBI_GOTO_MMODE")
    chunk.raw_data.extend(_misaligned_blob())
    return test_data.end_test_chunk()
