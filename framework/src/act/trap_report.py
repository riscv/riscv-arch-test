##################################
# trap_report.py
#
# Jordan Carlin jcarlin@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
#
# Decode trap signature region and generate a human-readable trap report
##################################

from __future__ import annotations

import subprocess
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

# Exception cause codes
EXCEPTION_CAUSES: dict[int, str] = {
    0: "Instruction address misaligned",
    1: "Instruction access fault",
    2: "Illegal instruction",
    3: "Breakpoint",
    4: "Load address misaligned",
    5: "Load access fault",
    6: "Store/AMO address misaligned",
    7: "Store/AMO access fault",
    8: "U-mode ecall",
    9: "S-mode ecall",
    10: "VS-mode ecall",
    11: "M-mode ecall",
    12: "Instruction page fault",
    13: "Load page fault",
    14: "Reserved Exception",
    15: "Store/AMO page fault",
    16: "Double trap",
    17: "Reserved Exception",
    18: "Software check",
    19: "Hardware error",
    20: "Instruction guest-page fault",
    21: "Load guest-page fault",
    22: "Virtual instruction",
    23: "Store/AMO guest-page fault",
}

# Interrupt cause codes without MSB
INTERRUPT_CAUSES: dict[int, str] = {
    0: "Reserved Interrupt",
    1: "Supervisor software interrupt",
    2: "Virtual supervisor software interrupt",
    3: "Machine software interrupt",
    4: "Reserved Interrupt",
    5: "Supervisor timer interrupt",
    6: "Virtual supervisor timer interrupt",
    7: "Machine timer interrupt",
    8: "Reserved Interrupt",
    9: "Supervisor external interrupt",
    10: "Virtual supervisor external interrupt",
    11: "Machine external interrupt",
    12: "Supervisor guest external interrupt",
    13: "Counter-overflow interrupt",
}

# Mode encoding from signature
MODE_NAMES: dict[int, str] = {
    0: "VS",
    1: "S/HS",
    2: "VS",
    3: "M",
}

# MPP field encoding
MPP_NAMES: dict[int, str] = {
    0: "U",
    1: "S",
    2: "reserved",
    3: "M",
}

# Canary values
TRAP_CANARY_32 = 0xD3A91F6C
TRAP_CANARY_64 = 0xD3A91F6C8B47E25D
END_CANARY_32 = 0x6F5CA309
END_CANARY_64 = 0x6F5CA309E7D4B281
DEADBEEF_32 = 0xDEADBEEF
DEADBEEF_64 = 0xDEADBEEFDEADBEEF


@dataclass(frozen=True)
class TrapEntry:
    """A single decoded trap from the signature region."""

    index: int
    mode: str
    is_interrupt: bool
    cause: int
    cause_name: str
    xepc: int | None
    xip: int | None
    xtval: int | None
    int_id: int | None
    mtval2: int | None
    mtinst: int | None
    xstatus_bits: int
    xie_bit: bool
    xip_bit: bool
    test_label: str | None


def _parse_symbol_table(nm_exe: Path, elf_path: Path) -> tuple[dict[int, str], int]:
    """Run nm on the ELF and return (address->label mapping, code_begin address).

    Returns symbols for text section and the rvtest_code_begin address (needed to
    convert relocated XEPC offsets back to absolute addresses for label lookup).
    """
    result = subprocess.run(
        [str(nm_exe), "--numeric-sort", str(elf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}, 0

    symbols: dict[int, str] = {}
    code_begin = 0
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("t", "T"):
            addr = int(parts[0], 16)
            name = parts[2]
            symbols[addr] = name
            if name == "rvtest_code_begin":
                code_begin = addr
    return symbols, code_begin


def _find_nearest_label(address: int, sorted_addrs: list[int], symbols: dict[int, str]) -> str | None:
    """Find the nearest preceding symbol for a given address."""
    if not sorted_addrs:
        return None
    idx = bisect_right(sorted_addrs, address) - 1
    if idx < 0:
        return None
    return symbols[sorted_addrs[idx]]


def _decode_cause(cause: int, xlen: int) -> tuple[bool, str]:
    """Decode xcause into (is_interrupt, cause_name)."""
    msb = 1 << (xlen - 1)
    is_interrupt = (cause & msb) != 0
    cause_code = cause & ~msb
    if is_interrupt:
        name = INTERRUPT_CAUSES.get(cause_code, f"Unknown interrupt ({cause_code:#x})")
    else:
        name = EXCEPTION_CAUSES.get(cause_code, f"Unknown exception ({cause_code:#x})")
    return is_interrupt, name


def _parse_trap_words(sig_path: Path, xlen: int) -> list[int] | None:
    """Parse the trap signature region from a .sig file. Returns None if no trap canary found."""
    trap_canary = TRAP_CANARY_32 if xlen == 32 else TRAP_CANARY_64
    end_canary = END_CANARY_32 if xlen == 32 else END_CANARY_64
    deadbeef = DEADBEEF_32 if xlen == 32 else DEADBEEF_64

    sig_text = sig_path.read_text()
    lines = [line.strip() for line in sig_text.splitlines() if line.strip()]
    values = [int(line, 16) for line in lines]

    # Find trap canary if present. Unpriv tests have no trap canary, so return None.
    try:
        trap_start = values.index(trap_canary)
    except ValueError:
        return None

    # Extract words after trap canary, up to end canary or end of file.
    # Note: deadbeef values may appear as unfilled padding within valid entries
    # (e.g., the 4th word of a timer interrupt entry), so we cannot stop at deadbeef.
    # Instead, stop at the end canary or when only deadbeef values remain.
    raw_region = values[trap_start + 1 :]

    # Find end canary
    try:
        end_idx = raw_region.index(end_canary)
        raw_region = raw_region[:end_idx]
    except ValueError:
        raise ValueError("End canary not found in trap signature region")

    # Trim trailing deadbeef padding
    while raw_region and raw_region[-1] == deadbeef:
        raw_region.pop()

    return raw_region


def _decode_all_traps(
    raw_words: list[int],
    xlen: int,
    sorted_addrs: list[int],
    symbols: dict[int, str],
    code_begin: int = 0,
) -> list[TrapEntry]:
    """Walk through raw trap signature words and decode each variable-length entry."""
    deadbeef = DEADBEEF_32 if xlen == 32 else DEADBEEF_64
    entries: list[TrapEntry] = []
    pos = 0
    index = 0

    while pos < len(raw_words):
        word0 = raw_words[pos]

        # Decode word 0 bitfields
        mode_raw = word0 & 0x3
        # Bits 5:2 hold the entry byte count. Convert to word count (REGWIDTH units).
        entry_bytes = word0 & 0x3C  # mask bits 5:2, keeping positional value = actual byte count
        regwidth = xlen // 8
        entry_size = entry_bytes // regwidth
        xie_bit = bool((word0 >> 11) & 1)
        xip_bit = bool((word0 >> 12) & 1)
        xstatus_bits = (word0 >> 13) & 0x3FFFF  # bits 30:13

        mode = MODE_NAMES.get(mode_raw, f"Unknown({mode_raw})")

        # Entry size should be 3, 4, or 6 REGWIDTH words
        if entry_size not in (3, 4, 6):
            break
        if pos + entry_size > len(raw_words):
            break

        # Word 1: xcause
        cause = raw_words[pos + 1]
        is_interrupt, cause_name = _decode_cause(cause, xlen)

        # Words 2+ depend on interrupt vs exception and entry size
        xepc: int | None = None
        xip_val: int | None = None
        xtval: int | None = None
        int_id: int | None = None
        mtval2: int | None = None
        mtinst: int | None = None
        test_label: str | None = None

        if is_interrupt:
            xip_val = raw_words[pos + 2]
            # IntID only for external interrupts; skip deadbeef padding
            if entry_size >= 4 and raw_words[pos + 3] != deadbeef:
                int_id = raw_words[pos + 3]
        else:
            # XEPC is a relocated offset from code_begin; convert back to absolute address
            xepc = raw_words[pos + 2] + code_begin
            test_label = _find_nearest_label(xepc, sorted_addrs, symbols)
            if entry_size >= 4:
                xtval = raw_words[pos + 3]
            if entry_size == 6:
                mtval2 = raw_words[pos + 4]
                mtinst = raw_words[pos + 5]

        entries.append(
            TrapEntry(
                index=index,
                mode=mode,
                is_interrupt=is_interrupt,
                cause=cause,
                cause_name=cause_name,
                xepc=xepc,
                xip=xip_val,
                xtval=xtval,
                int_id=int_id,
                mtval2=mtval2,
                mtinst=mtinst,
                xstatus_bits=xstatus_bits,
                xie_bit=xie_bit,
                xip_bit=xip_bit,
                test_label=test_label,
            )
        )

        pos += entry_size
        index += 1

    return entries


def _format_hex(value: int, xlen: int) -> str:
    """Format a value as a hex string with appropriate width."""
    width = xlen // 4
    return f"0x{value:0{width}x}"


def _decode_xstatus(status_bits: int) -> str:
    """Decode the xstatus field from word0 bits 30:13 into named fields.

    The xstatus field contains mstatus[17:0] shifted into position, with bits 2, 3,
    and 8 cleared by the trap handler mask. Additionally, bits 16:14 are OR'd with
    SPVP/MPV/GVA from mstatush/hstatus (overlapping with FS/XS when H-ext is present).
    """
    sie = (status_bits >> 1) & 1
    spie = (status_bits >> 5) & 1
    mpie = (status_bits >> 7) & 1
    spp = (status_bits >> 8) & 1
    mpp = (status_bits >> 11) & 0x3
    gva = (status_bits >> 14) & 1
    mpv = (status_bits >> 15) & 1
    spvp = (status_bits >> 16) & 1
    mprv = (status_bits >> 17) & 1

    return (
        f"SIE={sie}, MIE=0, SPIE={spie}, MPIE={mpie}, "
        f"SPP={'S' if spp else 'U'}, MPP={MPP_NAMES.get(mpp, '?')}, "
        f"GVA={gva}, MPV={mpv}, MPRV={mprv}, SPVP={spvp}"
    )


def _format_trap_report(entries: list[TrapEntry], test_name: str, xlen: int) -> str:
    """Format decoded trap entries into a human-readable report."""
    lines: list[str] = []
    lines.append(f"Trap Report: {test_name} (RV{xlen})")
    lines.append("=" * len(lines[0]))
    lines.append(f"Total traps recorded in signature: {len(entries)}")

    for entry in entries:
        lines.append("")
        kind = "Interrupt" if entry.is_interrupt else "Exception"
        lines.append(f"Trap #{entry.index}: {kind}")

        lines.append(f"  Mode:    {entry.mode}")
        lines.append(f"  XCAUSE:  {_format_hex(entry.cause, xlen)}  ({entry.cause_name})")

        if entry.xepc is not None:
            label_str = f"  ({entry.test_label})" if entry.test_label else ""
            lines.append(f"  XEPC:    {_format_hex(entry.xepc, xlen)}{label_str}")
        if entry.xtval is not None:
            lines.append(f"  XTVAL:   {_format_hex(entry.xtval, xlen)}")
        if entry.xip is not None:
            lines.append(f"  XIP:     {_format_hex(entry.xip, xlen)}")
        if entry.int_id is not None:
            lines.append(f"  IntID:   {_format_hex(entry.int_id, xlen)}")
        if entry.mtval2 is not None:
            lines.append(f"  MTVAL2:  {_format_hex(entry.mtval2, xlen)}")
        if entry.mtinst is not None:
            lines.append(f"  MTINST:  {_format_hex(entry.mtinst, xlen)}")

        lines.append(f"  Status:  {_decode_xstatus(entry.xstatus_bits)}")
        lines.append(f"  XIE[cause]: {int(entry.xie_bit)}  XIP[cause]: {int(entry.xip_bit)}")

    lines.append("")
    return "\n".join(lines)


def generate_trap_report(sig_path: Path, xlen: int, elf_path: Path | None, nm_exe: Path | None) -> None:
    """Generate a trap report from a signature file.

    Decodes the trap signature region and writes a human-readable report.
    Silently skips if no trap canary is found (unprivileged tests).

    Args:
        sig_path: Path to the .sig file from the Sail reference model.
        xlen: XLEN (32 or 64).
        elf_path: Path to the .sig.elf for symbol table extraction.
        nm_exe: Path to the nm executable for reading the symbol table.
    """
    trap_words = _parse_trap_words(sig_path, xlen)
    if trap_words is None:
        return  # No trap canary — unprivileged test

    report_path = Path(f"{sig_path}.trap_report")
    test_name = sig_path.stem

    if not trap_words:
        report_path.write_text(f"Trap Report: {test_name} (RV{xlen})\nNo traps occurred.\n")
        return

    # Parse symbol table if elf is available
    symbols: dict[int, str] = {}
    code_begin = 0
    if elf_path is not None and elf_path.exists() and nm_exe is not None:
        symbols, code_begin = _parse_symbol_table(nm_exe, elf_path)

    sorted_addrs = sorted(symbols.keys())

    entries = _decode_all_traps(trap_words, xlen, sorted_addrs, symbols, code_begin)
    report = _format_trap_report(entries, test_name, xlen)
    report_path.write_text(report)
