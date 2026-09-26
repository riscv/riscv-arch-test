##################################
# priv/extensions/Smpmpind.py
#
# Smpmpind indirect PMP CSR access-path test generator.
# Copyright (C) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smpmpind indirect PMP CSR access-path test generator.

Smpmpind exposes the PMP configuration registers through the Smcsrind indirect
window. miselect selects a PMP entry, mireg aliases that entry's pmpaddr,
and mireg2 aliases its configuration byte plus an enable bit E at MXLEN-1.
The direct pmpcfg CSRs alias only the low configuration byte, so they carry no
encoding for E and a direct write must leave it untouched.
"""

from __future__ import annotations

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

covergroup = "Smpmpind_cg"
coverpoint = "cp_pmp_indirect_access"

# miselect value selecting a PMP entry in the Smcsrind indirect window.
_MISELECT_PMPIND_BASE = 0x300

# The entry under test. It shares its packed direct pmpcfg CSR with other
# entries, so a direct write to that CSR also rewrites its neighbours.
_ENTRY = 4
_MISELECT_ENTRY = _MISELECT_PMPIND_BASE | _ENTRY


def _direct_cfg_view(xlen: int) -> tuple[str, int]:
    """Return the packed direct CSR holding the entry's configuration byte and its shift.

    RV64 packs eight entries per pmpcfg CSR and numbers those CSRs evenly, so
    entry 4 lives in pmpcfg0 bits[39:32]. RV32 packs four per CSR and numbers
    them consecutively, so the same entry lives in pmpcfg1 bits[7:0]. The direct
    view therefore differs by XLEN even though the indirect view does not.
    """
    entries_per_csr = xlen // 8
    csr_index = _ENTRY // entries_per_csr
    if xlen == 64:
        csr_index *= 2  # RV64 uses only even-numbered pmpcfg CSRs
    return f"pmpcfg{csr_index}", 8 * (_ENTRY % entries_per_csr)


# Configuration byte under test: NAPOT, readable, writable (0x1B).
_CFG = "(PMP_NAPOT | PMP_R | PMP_W)"

_PAGE = 4096

# Backing region for the pmpaddr value. Never accessed, so only alignment matters.
_REGION = "smpmpind_pmp_region"


def _select_entry(reg: int) -> list[str]:
    """Point miselect at the entry under test."""
    return [
        (
            f"{INDENT}li x{reg}, {_MISELECT_ENTRY:#x}"
            f"    # miselect = PMP indirect base {_MISELECT_PMPIND_BASE:#x} | entry {_ENTRY}"
        ),
        f"{INDENT}csrw CSR_MISELECT, x{reg}",
    ]


def _read_direct_cfg_byte(dest: int) -> list[str]:
    """Extract the entry's configuration byte from the packed direct CSR."""
    lines: list[str] = []
    for xlen, guard in ((64, "#if __riscv_xlen == 64"), (32, "#else")):
        csr, shift = _direct_cfg_view(xlen)
        lines.append(guard)
        lines.append(f"{INDENT}csrr x{dest}, {csr}")
        if shift:
            lines.append(
                f"{INDENT}srli x{dest}, x{dest}, {shift}"
                f"    # entry {_ENTRY} occupies bits[{shift + 7}:{shift}] of {csr}"
            )
        else:
            lines.append(f"{INDENT}# entry {_ENTRY} occupies bits[7:0] of {csr}")
    lines.append("#endif")
    lines.append(f"{INDENT}andi x{dest}, x{dest}, 0xFF")
    return lines


def _round_trip_direct_cfg(reg: int) -> list[str]:
    """Read the packed direct CSR and write it straight back, unmodified."""
    lines: list[str] = []
    for xlen, guard in ((64, "#if __riscv_xlen == 64"), (32, "#else")):
        csr, _ = _direct_cfg_view(xlen)
        lines.extend(
            [
                guard,
                f"{INDENT}csrr x{reg}, {csr}",
                f"{INDENT}csrw {csr}, x{reg}    # round-trip the packed register",
            ]
        )
    lines.append("#endif")
    return lines


def _region_data_section() -> list[str]:
    return [
        "",
        "# Backing region for the pmpaddr value under test. Injected into .data via",
        "# .pushsection. Page-aligned so the address is a legal NAPOT base.",
        ".pushsection .data",
        ".p2align 12",
        f"{_REGION}:",
        f"{INDENT}.fill {_PAGE}, 1, 0",
        ".popsection",
        "",
    ]


def _generate_indirect_pmpcfg(test_data: TestData) -> TestChunk:
    """Indirect PMP configuration access path, no traps."""
    tc = test_data.begin_test_chunk("indirect_pmpcfg")

    addr_reg, cfg_reg, tmp_reg, check_reg = test_data.int_regs.get_registers(4)

    tc.code.extend(_region_data_section())

    tc.code.append(
        comment_banner(
            coverpoint,
            "Write a PMP entry through the indirect window with the enable bit set, then read it back.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, {_REGION})",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2    # address -> pmpaddr encoding",
            "",
            f"{INDENT}li x{cfg_reg}, {_CFG}    # configuration byte",
            "#if __riscv_xlen == 64",
            f"{INDENT}li x{tmp_reg}, 0x8000000000000000    # E occupies bit MXLEN-1",
            "#else",
            f"{INDENT}li x{tmp_reg}, 0x80000000",
            "#endif",
            f"{INDENT}or x{cfg_reg}, x{cfg_reg}, x{tmp_reg}    # mireg2 value = E | cfg",
            "",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg))
    tc.code.extend(
        [
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}     # mireg aliases pmpaddr",
            f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}     # mireg2 aliases cfg | E",
            "",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg))
    tc.code.append(test_data.add_testcase("indirect_readback_e1", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MIREG2", None), test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "The direct pmpcfg CSR aliases the low configuration byte of the same entry.",
        )
    )
    tc.code.extend(_read_direct_cfg_byte(check_reg))
    tc.code.append(test_data.add_testcase("direct_byte_matches", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "A direct pmpcfg round-trip must preserve E, which has no direct encoding.",
        )
    )
    tc.code.extend(_round_trip_direct_cfg(check_reg))
    tc.code.append("")
    tc.code.extend(_select_entry(tmp_reg))
    tc.code.append(test_data.add_testcase("e_preserved_across_direct_write", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MIREG2", None), test_data))

    tc.code.extend(_read_direct_cfg_byte(check_reg))
    tc.code.append(test_data.add_testcase("direct_byte_after_direct_write", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    for bin_name, e_set, description in (
        ("indirect_readback_e0", False, "Clearing E through mireg2 leaves the configuration byte in place."),
        ("indirect_readback_e1_again", True, "Setting E again round-trips through the indirect window."),
    ):
        tc.code.append(comment_banner(coverpoint, description))
        tc.code.extend(_select_entry(tmp_reg))
        tc.code.append(f"{INDENT}li x{cfg_reg}, {_CFG}")
        if e_set:
            tc.code.extend(
                [
                    "#if __riscv_xlen == 64",
                    f"{INDENT}li x{tmp_reg}, 0x8000000000000000",
                    "#else",
                    f"{INDENT}li x{tmp_reg}, 0x80000000",
                    "#endif",
                    f"{INDENT}or x{cfg_reg}, x{cfg_reg}, x{tmp_reg}",
                ]
            )
        tc.code.append(f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}")
        tc.code.append("")
        tc.code.extend(_select_entry(tmp_reg))
        tc.code.append(test_data.add_testcase(bin_name, coverpoint, covergroup))
        tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MIREG2", None), test_data))

    test_data.int_regs.return_registers([addr_reg, cfg_reg, tmp_reg, check_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Smpmpind",
    required_extensions=["Sm", "Smpmpind"],
    march_extensions=[],
    params=[
        # Entry 4, encoded as NAPOT. Usable, not implemented: an entry whose
        # registers read as zero cannot be configured.
        f"NUM_USABLE_PMP_ENTRIES: '>={_ENTRY + 1}'",
        "PMP_NAPOT_SUPPORTED: true",
    ],
    extra_defines=[
        "#define BOOT_TO_MMODE",
        "#define TRAP_SIGUPD_COUNT 0",
    ],
)
def make_smpmpind(test_data: TestData) -> list[TestChunk]:
    return [_generate_indirect_pmpcfg(test_data)]
