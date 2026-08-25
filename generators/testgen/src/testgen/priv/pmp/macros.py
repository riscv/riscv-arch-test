##################################
# priv/pmp/macros.py
#
# Shared assembly building blocks for the pure PMP suite generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly fragments shared by the ``tests/priv/pmp`` suites.

The verification macros themselves live in ``tests/env/rvtest_pmp_macros.h``; this
module knows how many probes each one records and how they are named, and builds the
surrounding region setup.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from testgen.priv.pmp.model import PmpFile, Xlen

TITLE = "Comprehensive PMP (Physical Memory Protection) Verification"

AUTHORS = ("Umer Shahid, Allen Baum, David Harris", "Muhammad Abdullah, Hamza Ali, Muhammad Zain")

DESCRIPTION = """\
This test verifies the functionality and enforcement of
Physical Memory Protection (PMP) configurations in RISC-V
systems. It specifically tests the Read, Write, and Execute
permissions for a designated memory region, ensuring that
the PMP settings are correctly applied and that the system
behaves as expected when accessing this region."""

QUALCOMM = ("// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.",)

NUM_PMP_ENTRIES_PARAM = "NUM_PMP_ENTRIES: '>0'"


def banner(
    coverpoints: str,
    test_cases: str,
    *,
    title: str = TITLE,
    description: str = DESCRIPTION,
    authors: tuple[str, ...] = AUTHORS,
) -> str:
    """The Title / Authors / Description / Coverpoints / Test Cases comment block."""

    def block(label: str, text: str) -> list[str]:
        first, *rest = text.strip("\n").splitlines() or [""]
        return [f"// {label:<12}: {first}", *(f"//{'':<15}{line}" for line in rest)]

    lines = [f"// {'Title':<12}: {title}", f"// {'Authors':<12}: {authors[0]}"]
    lines.extend(f"//{'':<15}{author}" for author in authors[1:])
    for label, text in (("Description", description), ("Coverpoints", coverpoints), ("Test Cases", test_cases)):
        lines.append("//")
        lines.extend(block(label, text))
    return "\n".join(lines)


def amode_params(amode: str | None) -> tuple[str, ...]:
    """The NUM_PMP_ENTRIES gate every file carries, plus the address-mode gate."""
    if amode is None:
        return (NUM_PMP_ENTRIES_PARAM,)
    return (NUM_PMP_ENTRIES_PARAM, f"PMP_{amode.upper()}_SUPPORTED: true")


#####################################################################
# Verification macros (tests/env/rvtest_pmp_macros.h)
#####################################################################

_OFFSETS = ("address", "address-4", "address+4", "address+g-4", "address+g")
_AMOS = ("amoadd", "amoand", "amoor", "amoxor", "amomax", "amomaxu", "amomin", "amominu", "amoswap")

#: Probe names each verification macro records, in test-case order.
PROBES: dict[str, dict[int, tuple[str, ...]]] = {
    "RWX": {32: ("jalr", "sw", "lw")},
    "LW": {32: ("lw",)},
    "LW_BOUNDS": {32: ("lw_address", "lw_address-4", "lw_beyond")},
    "RWX_ALL": {
        32: ("sb", "sh", "sw", "lb", "lbu", "lh", "lhu", "lw", "jalr"),
        64: ("sb", "sh", "sw", "sd", "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld", "jalr"),
    },
    "RWX_NA4": {
        32: tuple(f"{op}_{off}" for op in ("jalr",) for off in _OFFSETS[:3])
        + tuple(f"{op}_{off}" for off in _OFFSETS[:3] for op in ("sw", "lw")),
    },
    "RWX_LEGAL": {32: tuple(f"{op}_{off}" for op in ("jalr", "sw", "lw") for off in _OFFSETS)},
    "RWX_NAPOT": {
        32: ("sb_address", "sh_address", *(f"sw_{off}" for off in _OFFSETS))
        + ("lb_address", "lbu_address", "lh_address", "lhu_address", *(f"lw_{off}" for off in _OFFSETS))
        + tuple(f"jalr_{off}" for off in _OFFSETS),
        64: ("sb_address", "sh_address", *(f"sw_{off}" for off in _OFFSETS))
        + ("lb_address", "lbu_address", "lh_address", "lhu_address", *(f"lw_{off}" for off in _OFFSETS))
        + tuple(f"jalr_{off}" for off in _OFFSETS)
        + ("sd_address", "ld_address", "lwu_address"),
    },
    "RWX_TOR_BOT": {
        32: tuple(f"{op}_{where}" for op in ("sw", "lw", "jalr") for where in ("bot-4", "bot", "top-4", "top")),
    },
    "RWX_TOR_ZERO": {32: tuple(f"{op}_{where}" for op in ("sw", "lw", "jalr") for where in ("top", "top-4"))},
    "F": {32: ("fsh", "fsw", "fsd", "flh", "flw", "fld")},
    "AMO": {
        32: tuple(f"{amo}_w" for amo in _AMOS),
        64: tuple(f"{amo}_{w}" for amo in _AMOS for w in ("w", "d")),
    },
    "LRSC": {32: ("lr_w", "sc_w"), 64: ("lr_w", "sc_w", "lr_d", "sc_d")},
    "ZCA": {32: ("c.sw", "c.lw", "c.jalr"), 64: ("c.sw", "c.lw", "c.jalr", "c.sd", "c.ld")},
    "ZCB": {32: ("c.sb", "c.lbu", "c.sh", "c.lhu", "c.sh", "c.lh")},
    "ZCD": {32: ("c.fsd", "c.fld")},
    "ZCF": {32: ("c.fsw", "c.flw")},
    "CBO": {32: ("cbo.zero", "cbo.clean", "cbo.flush", "cbo.inval")},
    "PREFETCH": {32: ("prefetch.i", "prefetch.r", "prefetch.w")},
    "X_C": {32: ("c.jalr",)},
}


def probes(macro: str, xlen: Xlen) -> tuple[str, ...]:
    """Probe names ``PMP_VERIFICATION_<macro>`` records on this XLEN."""
    table = PROBES[macro]
    return table.get(xlen.bits, table[32])


def sig_strs(macro: str, xlen: Xlen, prefix: str) -> tuple[tuple[str, str], ...]:
    """One reporting string per probe of ``macro``, named ``<prefix>_<probe>``."""
    return tuple(
        (f"test_{n}", f"test: {n}; cp: {prefix}_{probe}") for n, probe in enumerate(probes(macro, xlen), start=1)
    )


#: Slack added to every computed SIGUPD_COUNT before rounding.
_SIGUPD_MARGIN = 10


def sigupd_count(updates: int) -> int:
    """Signature-region size for a test that performs ``updates`` RVTEST_SIGUPD calls."""
    return ((updates + _SIGUPD_MARGIN + 9) // 10) * 10


#####################################################################
# PMP CSR helpers
#####################################################################


def zero_pmp_regs(xlen: Xlen) -> list[str]:
    """Clear every implemented pmpcfg and pmpaddr CSR."""
    return [
        "    // Clear every pmpcfg and pmpaddr CSR",
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {xlen.cfg_rept}",
        "    csrw pmpcfgi, x0",
        f"    .set pmpcfgi, pmpcfgi+{xlen.cfg_step}",
        "    .endr",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "    csrw pmpaddri, x0",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
    ]


def cfg_csr(xlen: Xlen, entry: int) -> str:
    """Name of the pmpcfg CSR holding ``entry``'s configuration byte."""
    return f"pmpcfg{(entry // xlen.cfgs_per_reg) * xlen.cfg_step}"


def cfg_shift(xlen: Xlen, entry: int) -> str:
    """Name of the shift constant placing ``entry``'s byte inside its pmpcfg CSR."""
    return f"PMP{entry % xlen.cfgs_per_reg}_CFG_SHIFT"


_LXWR_BITS = ("PMP_L", "PMP_X", "PMP_W", "PMP_R")

AMODE_CONST = {"off": None, "na4": "PMP_NA4", "napot": "PMP_NAPOT", "tor": "PMP_TOR"}


def lxwr_expr(lxwr: str, amode: str | None) -> str:
    """``PMP_L|PMP_R|PMP_W|PMP_X|PMP_<amode>`` for a four-character L/X/W/R bit string."""
    bits = [bit for bit, ch in zip(_LXWR_BITS, lxwr, strict=True) if ch == "1"]
    bits = [b for b in ("PMP_L", "PMP_R", "PMP_W", "PMP_X") if b in bits]
    const = AMODE_CONST[amode] if amode else None
    if const:
        bits.append(const)
    return "|".join(bits) if bits else "0"


def cfg_byte(lxwr: str, amode: str | None, shift: str) -> str:
    """The pmpcfg CSR value that places one configuration byte at ``shift``."""
    return f"((({lxwr_expr(lxwr, amode)})&0xFF) << {shift})"


def lxwr_defines(xlen: Xlen, cases: list[tuple[str, int]], amode: str) -> list[str]:
    """``#define PMPREGION_LXWR_<bits>`` lines, one per (LXWR code, PMP entry) case."""
    return [f"#define PMPREGION_LXWR_{lxwr} {cfg_byte(lxwr, amode, cfg_shift(xlen, entry))}" for lxwr, entry in cases]


LXWR_PERM_NAMES: dict[str, str] = {
    "000": "No",
    "001": "R",
    "011": "WR",
    "100": "X",
    "101": "XR",
    "111": "XWR",
}


def case_banner(index: int, lxwr: str, entry: int) -> str:
    """The ``// Test Case`` comment for one LXWR walk step."""
    return (
        f"// Test Case: {index} : L -> {lxwr[0]} and {LXWR_PERM_NAMES[lxwr[1:]]} Permissions given to PMP entry {entry}"
    )


NAPOT_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "#endif",
]


def set_pmpaddr(amode: str, entry: int, region: str = "REGIONSTART") -> list[str]:
    """Program the pmpaddr CSR(s) that make ``entry`` cover the smallest region at ``region``.

    NAPOT encodes the region size into the low address bits; TOR bounds
    ``[region, region + PMP_TOR_REGION_BYTES)`` with ``pmpaddr<entry-1>``/``pmpaddr<entry>``.
    """
    lines = [f"    LA(x5, {region})", "    srl x5, x5, PMP_SHIFT"]
    if amode == "napot":
        lines += ["    LI(x6, PMP_MASK)", "    and x5, x5, x6", "    LI(x6, PMP_REGION_SIZE)", "    or x5, x5, x6"]
    if amode == "tor":
        lines += [
            f"    csrw pmpaddr{entry - 1}, x5",
            "    LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)",
            "    add x5, x5, x6",
        ]
    lines.append(f"    csrw pmpaddr{entry}, x5")
    return lines


def set_pmpcfg(xlen: Xlen, entry: int, value: str) -> list[str]:
    """Write ``value`` (a full CSR value) to the pmpcfg CSR holding ``entry``."""
    return [f"    LI(x4, {value})", f"    csrw {cfg_csr(xlen, entry)}, x4"]


#: The six legal (L=1) LXWR encodings, each parked in its own PMP entry so that the
#: most permissive one has the highest priority.
LOCKED_LXWR_CASES: list[tuple[str, int]] = [
    ("1000", 5),
    ("1001", 4),
    ("1011", 3),
    ("1100", 2),
    ("1101", 1),
    ("1111", 0),
]

#: The same six encodings with L=0.
UNLOCKED_LXWR_CASES: list[tuple[str, int]] = [(f"0{lxwr[1:]}", entry) for lxwr, entry in LOCKED_LXWR_CASES]

VERIFICATION_SECTION = "// ---------------------------- Verification Section ----------------------------"

EXIT = ["", "    j exit", "", "exit:"]


def run_case(
    macro: str, index: int, region: str = "TEST_FOR_EXECUTION", lower_mode: str | None = None, extra: str = ""
) -> list[str]:
    """Run ``PMP_VERIFICATION_<macro>`` for test case ``index``, from ``lower_mode`` if given."""
    lines = ["    RVTEST_SFENCE_VMA_IF_SUPPORTED"]
    if lower_mode:
        lines.append(f"    RVTEST_TSBI_GOTO_{lower_mode}MODE")
    lines.append(f"    PMP_VERIFICATION_{macro}    {region}, test_{index}{extra}")
    if lower_mode:
        lines.append("    RVTEST_TSBI_GOTO_MMODE")
    return lines


def lxwr_walk_body(
    xlen: Xlen,
    cases: list[tuple[str, int]],
    amode: str,
    macro: str | Callable[[str], str],
    *,
    first: int = 1,
    lower_mode: str | None = None,
    extra_setup: list[str] | None = None,
    napot_mask: list[str] = NAPOT_MASK_DEFINES,
) -> list[str]:
    """Walk LXWR encodings against one region: clear the PMPs, define one
    ``PMPREGION_LXWR_*`` per case, set the background, then configure and probe each
    case. ``macro`` names the verification macro, or maps each LXWR code to one."""
    lines = [*zero_pmp_regs(xlen), "", *lxwr_defines(xlen, cases, amode), "", "#define REGIONSTART TEST_FOR_EXECUTION"]
    if amode == "napot":
        lines.extend(napot_mask)
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4"])
    if extra_setup:
        lines.extend(["", *extra_setup])
    lines.extend(["", VERIFICATION_SECTION])
    for n, (lxwr, entry) in enumerate(cases, start=first):
        lines.extend(["", case_banner(n, lxwr, entry)])
        lines.extend(set_pmpaddr(amode, entry))
        lines.extend(set_pmpcfg(xlen, entry, f"PMPREGION_LXWR_{lxwr}"))
        lines.extend(run_case(macro if isinstance(macro, str) else macro(lxwr), n, lower_mode=lower_mode))
    lines.extend(EXIT)
    return lines


def walk_file(
    xlen: Xlen,
    filename: str,
    macro: str,
    cases: list[tuple[str, int]],
    amode: str,
    *,
    banner: str,
    prefix: str,
    required_extensions: tuple[str, ...],
    march: str | None = None,
    params: tuple[str, ...] | None = None,
    data: list[str] | None = None,
    first: int = 1,
    lower_mode: str | None = None,
    extra_setup: list[str] | None = None,
    napot_mask: list[str] = NAPOT_MASK_DEFINES,
    macro_for: Callable[[str], str] | None = None,
) -> PmpFile:
    """A complete file whose body is one :func:`lxwr_walk_body`, reporting ``<prefix>_<probe>``."""
    return PmpFile(
        filename=filename,
        xlen=xlen,
        banner=banner,
        required_extensions=required_extensions,
        params=params or amode_params(None),
        march=march,
        sigupd=sigupd_count(len(cases) * len(probes(macro, xlen))),
        body=tuple(
            lxwr_walk_body(
                xlen,
                cases,
                amode,
                macro_for or macro,
                first=first,
                lower_mode=lower_mode,
                extra_setup=extra_setup,
                napot_mask=napot_mask,
            )
        ),
        sig_strs=sig_strs(macro, xlen, prefix),
        data=tuple(data if data is not None else REGION_BLOBS[amode]),
    )


def entry_walk(
    xlen: Xlen,
    entries: Iterable[int],
    amode: str,
    cfg: Callable[[int], str],
    macro: str,
    *,
    region: str = "TEST_FOR_EXECUTION",
    first: int = 1,
    extra: str = "",
) -> list[str]:
    """Program ``entries`` one at a time with ``cfg(entry)`` at REGIONSTART and probe each."""
    lines = []
    for n, entry in enumerate(entries, start=first):
        lines.extend(["", f"// Test Case: {n} : PMP entry {entry}", *set_pmpaddr(amode, entry)])
        lines.extend(set_pmpcfg(xlen, entry, cfg(entry)))
        lines.extend(run_case(macro, n, region, extra=extra))
    return lines


def csr_write(csr: str, src: str, index: int, label: str) -> list[str]:
    """Write ``src`` to ``csr``, read it back and record the result as test case ``index``."""
    return [f"    test_{index}:", f"        RVTEST_SIGUPD_CSR_WRITE({csr}, {src}, test_{index}, {label}_str)"]


#####################################################################
# Data section
#####################################################################

#: Uncompressed encodings, so the pad and trampoline keep their word layout under Zca.
_NORVC = ["    .option push", "    .option norvc"]
_RVC_POP = ["    .option pop"]

RETURN_TRAMPOLINE = [*_NORVC, "RETURN_INSTRUCTION:", "    nop", "    nop", "    jr ra", *_RVC_POP]

GRANULE_WORDS = "(1 << (UDB_PMP_GRANULARITY - 2))"
TOR_REGION_WORDS = "(PMP_TOR_REGION_BYTES / 4)"
NAPOT_REGION_WORDS = "PMP_NAPOT_REGION_PAD_WORDS"


def exec_region(
    region: tuple[str, str] = (GRANULE_WORDS, "nop"),
    *,
    pad: tuple[str, str] | None = (GRANULE_WORDS, "jr ra"),
    label: str = "TEST_FOR_EXECUTION",
) -> list[str]:
    """The executable blob in the data section: an optional pad, the region under test, and
    the return trampoline. ``pad`` and ``region`` are (.rept count, instruction)."""
    lines = [".p2align 12", ".p2align (UDB_PMP_GRANULARITY)"]
    if pad:
        lines.extend([*_NORVC, f"{label}_0:", f"    .rept {pad[0]}", f"    {pad[1]}", "    .endr", *_RVC_POP])
    lines.extend([f"{label}:", f"    .rept {region[0]}", f"    {region[1]}", "    .endr", *RETURN_TRAMPOLINE])
    return lines


#: Data-section blob per address mode: TOR and NA4 regions are made of return
#: instructions so that any probed word returns; NAPOT regions are padded so the
#: region starts at the coverage model's PMP_NAPOT_REGION_START.
REGION_BLOBS = {
    "off": exec_region(),
    "na4": exec_region((TOR_REGION_WORDS, "jr ra"), pad=(TOR_REGION_WORDS, "jr ra")),
    "napot": exec_region((NAPOT_REGION_WORDS, "jr ra"), pad=(NAPOT_REGION_WORDS, "jr ra")),
    "tor": exec_region((TOR_REGION_WORDS, "jr ra"), pad=(TOR_REGION_WORDS, "jr ra")),
    "napot_pad": exec_region(pad=(NAPOT_REGION_WORDS, "jr ra")),
}
