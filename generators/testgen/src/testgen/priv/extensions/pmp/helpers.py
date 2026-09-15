##################################
# priv/extensions/pmp/helpers.py
#
# Shared assembly building blocks for PMP test generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP configuration, walk, and region helpers."""

from collections.abc import Callable, Iterable

from testgen.data.state import TestData
from testgen.priv.extensions.pmp.probes import ProbeGenerator

#####################################################################
# PMP CSR helpers
#####################################################################


def zero_pmp_regs() -> list[str]:
    """Clear every implemented pmpcfg and pmpaddr CSR."""
    return [
        "// Clear every pmpcfg and pmpaddr CSR",
        ".set pmpcfgi, CSR_PMPCFG0",
        ".rept UDB_NUM_PMP_ENTRIES / (UDB_MXLEN / 8)",
        "csrw pmpcfgi, x0",
        ".set pmpcfgi, pmpcfgi + (UDB_MXLEN / 32)",
        ".endr",
        ".set pmpaddri, CSR_PMPADDR0",
        ".rept UDB_NUM_PMP_ENTRIES",
        "csrw pmpaddri, x0",
        ".set pmpaddri, pmpaddri + 1",
        ".endr",
    ]


def cfg_shift(entry: int) -> str:
    """Expression for the XLEN-aware shift of ``entry`` inside its pmpcfg CSR."""
    return f"PMP_CFG_SHIFT({entry})"


_AMODE_CONST = {"off": None, "na4": "PMP_NA4", "napot": "PMP_NAPOT", "tor": "PMP_TOR"}


def lxwr_expr(lxwr: str, amode: str | None) -> str:
    """``PMP_L|PMP_R|PMP_W|PMP_X|PMP_<amode>`` for a four-character L/X/W/R bit string."""
    bits = [name for index, name in ((0, "PMP_L"), (3, "PMP_R"), (2, "PMP_W"), (1, "PMP_X")) if lxwr[index] == "1"]
    if amode and (mode := _AMODE_CONST[amode]):
        bits.append(mode)
    return " | ".join(bits) or "0"


def cfg_byte(lxwr: str, amode: str | None, shift: str) -> str:
    """The pmpcfg CSR value that places one configuration byte at ``shift``."""
    return f"((({lxwr_expr(lxwr, amode)}) & 0xFF) << {shift})"


_LXWR_PERM_NAMES: dict[str, str] = {
    "000": "No",
    "001": "R",
    "011": "WR",
    "100": "X",
    "101": "XR",
    "111": "XWR",
}


NAPOT_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "#define PMP_MASK        ~((1 << (UDB_PMP_GRANULARITY - 3)) - 1)",
    "#define PMP_REGION_SIZE ((1 << (UDB_PMP_GRANULARITY - 3)) - 1)",
    "#else",
    "#define PMP_MASK        ~0",
    "#define PMP_REGION_SIZE 0",
    "#endif",
]


def set_pmpaddr(amode: str, entry: int, region: str = "REGIONSTART") -> list[str]:
    """Program the pmpaddr CSR(s) that make ``entry`` cover the smallest region at ``region``.

    NAPOT encodes the region size into the low address bits; TOR bounds
    ``[region, region + PMP_TOR_REGION_BYTES)`` with ``pmpaddr<entry-1>``/``pmpaddr<entry>``.
    """
    lines = [f"LA(x5, {region})", "srl x5, x5, PMP_SHIFT"]
    if amode == "napot":
        lines += ["LI(x6, PMP_MASK)", "and x5, x5, x6", "LI(x6, PMP_REGION_SIZE)", "or x5, x5, x6"]
    if amode == "tor":
        lines += [
            f"csrw pmpaddr{entry - 1}, x5",
            "LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)",
            "add x5, x5, x6",
        ]
    lines.append(f"csrw pmpaddr{entry}, x5")
    return lines


def set_pmpcfg(entry: int, value: str) -> list[str]:
    """Write ``value`` in the pmpcfg CSR that contains ``entry``."""
    rv32_csr = entry // 4
    rv64_csr = (entry // 8) * 2
    lines = [f"LI(x4, {value})"]
    if rv32_csr == rv64_csr:
        lines.append(f"csrw pmpcfg{rv32_csr}, x4")
    else:
        lines.extend(
            [
                "#if __riscv_xlen == 32",
                f"csrw pmpcfg{rv32_csr}, x4",
                "#else",
                f"csrw pmpcfg{rv64_csr}, x4",
                "#endif",
            ]
        )
    return lines


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

#: TOR regions need two pmpaddr CSRs, so the six cases use every other entry.
TOR_ENTRIES = ((11, 9, 7), (5, 3, 1))


def lxwr_walk_body(
    test_data: TestData,
    cases: list[tuple[str, int]],
    amode: str,
    probe_generator: ProbeGenerator | dict[str, ProbeGenerator],
    coverpoint: str,
    *,
    first: int = 1,
    lower_mode: str | None = None,
    extra_setup: list[str] | None = None,
    napot_mask: list[str] = NAPOT_MASK_DEFINES,
) -> list[str]:
    """Walk LXWR encodings against one region: clear the PMPs, define one
    ``PMPREGION_LXWR_*`` per case, set the background, then configure and probe each
    case. ``probe_generator`` emits and registers the access probes."""
    defines = [f"#define PMPREGION_LXWR_{lxwr} {cfg_byte(lxwr, amode, cfg_shift(entry))}" for lxwr, entry in cases]
    lines = [*zero_pmp_regs(), "", *defines, "", "#define REGIONSTART TEST_FOR_EXECUTION"]
    if amode == "napot":
        lines.extend(napot_mask)
    lines.extend(["", "RVTEST_PMP_SET_BACKGROUND x4"])
    if extra_setup:
        lines.extend(["", *extra_setup])
    for n, (lxwr, entry) in enumerate(cases, start=first):
        permission = _LXWR_PERM_NAMES[lxwr[1:]]
        lines.extend(["", f"// PMP configuration {n}: L = {lxwr[0]}, {permission} permissions, entry {entry}"])
        lines.extend(set_pmpaddr(amode, entry))
        lines.extend(set_pmpcfg(entry, f"PMPREGION_LXWR_{lxwr}"))
        lines.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
        if lower_mode:
            lines.append(f"RVTEST_TSBI_GOTO_{lower_mode}MODE")
        generator = probe_generator[lxwr] if isinstance(probe_generator, dict) else probe_generator
        lines.extend(generator(test_data, f"entry{entry}_lxwr{lxwr}", coverpoint, "TEST_FOR_EXECUTION"))
        if lower_mode:
            lines.append("RVTEST_TSBI_GOTO_MMODE")
    return lines


def entry_walk(
    test_data: TestData,
    entries: Iterable[int],
    amode: str,
    cfg: Callable[[int], str],
    probe_generator: ProbeGenerator,
    coverpoint: str,
    *,
    region: str = "TEST_FOR_EXECUTION",
    first: int = 1,
    case_prefix: str = "entry",
) -> list[str]:
    """Program ``entries`` one at a time with ``cfg(entry)`` at REGIONSTART and probe each."""
    lines = []
    for n, entry in enumerate(entries, start=first):
        lines.extend(["", f"// PMP configuration {n}: entry {entry}", *set_pmpaddr(amode, entry)])
        lines.extend(set_pmpcfg(entry, cfg(entry)))
        lines.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
        lines.extend(probe_generator(test_data, f"{case_prefix}{entry}", coverpoint, region))
    return lines


#####################################################################
# Data section
#####################################################################

#: Uncompressed encodings, so the pad and trampoline keep their word layout under Zca.
_NORVC = [".option push", ".option norvc"]
_RVC_POP = [".option pop"]

RETURN_TRAMPOLINE = [*_NORVC, "RETURN_INSTRUCTION:", "nop", "nop", "jr ra", *_RVC_POP]

TOR_REGION_WORDS = "(PMP_TOR_REGION_BYTES / 4)"
NAPOT_REGION_WORDS = "PMP_NAPOT_REGION_PAD_WORDS"


def make_exec_region(
    region: tuple[str, str] = (TOR_REGION_WORDS, "nop"),
    *,
    pad: tuple[str, str] | None = (TOR_REGION_WORDS, "jr ra"),
    label: str = "TEST_FOR_EXECUTION",
) -> list[str]:
    """The executable blob in the data section: an optional pad, the region under test, and
    the return trampoline. ``pad`` and ``region`` are (.rept count, instruction)."""
    lines = [".p2align 12", ".p2align (UDB_PMP_GRANULARITY)"]
    if pad:
        lines.extend([*_NORVC, f"{label}_0:", f".rept {pad[0]}", f"{pad[1]}", ".endr", *_RVC_POP])
    lines.extend([f"{label}:", f".rept {region[0]}", f"{region[1]}", ".endr", *RETURN_TRAMPOLINE])
    return lines


#: Data-section blob per address mode: TOR and NA4 regions are made of return
#: instructions so that any probed word returns; NAPOT regions are padded so the
#: region starts at the coverage model's PMP_NAPOT_REGION_START.
_TOR_REGION = make_exec_region((TOR_REGION_WORDS, "jr ra"), pad=(TOR_REGION_WORDS, "jr ra"))

REGION_BLOBS = {
    "off": make_exec_region(),
    "na4": _TOR_REGION,
    "napot": make_exec_region((NAPOT_REGION_WORDS, "jr ra"), pad=(NAPOT_REGION_WORDS, "jr ra")),
    "tor": _TOR_REGION,
    "napot_pad": make_exec_region(pad=(NAPOT_REGION_WORDS, "jr ra")),
}
