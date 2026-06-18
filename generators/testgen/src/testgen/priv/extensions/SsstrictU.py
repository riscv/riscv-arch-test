##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU — user-mode strict/negative compliance tests.

The fast trap handlers are NOT emitted here — every split file defines
RVTEST_USE_FAST_TRAP_HANDLER, which instantiates RVTEST_FAST_TRAP_HANDLER
(rvtest_trap_handler.h: mtvec → fast M-mode handler, stvec →
strap_handler_fastillegalinstr); generate/priv.py prepends
_SPLIT_FILE_UMODE_GPR_INIT (which issues RVTEST_GOTO_LOWER_MODE Umode)
to every split file.

Structure
---------
1. Per-split-file prefix switches to U-mode; the body stays in U-mode.
2. CSR sweep from U-mode (user-level CSRs only: bits[9:8]=00).
   - S/H/M CSRs are higher privilege and always trap from U-mode; that is
     an architecturally known fact covered elsewhere, so they are excluded.
   - Custom and reserved ranges are skipped (undefined behaviour).
3. Illegal instruction and compressed encoding sweeps.
"""

from random import seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

from .SsstrictCommon import (
    generate_compressed_instr,
    generate_csr_sweep_body,
    generate_illegal_instr,
    generate_vector_illegal_instr,
)

# ── CSR sweep set (U-mode) ────────────────────────────────────────────────

# Sweep only user-level CSRs (bits[9:8]=00) from U-mode.
# S/H/M CSRs are higher privilege and always raise illegal-instruction from
# U-mode — that is an architecturally known fact, so testing them here adds
# no value.  Custom and reserved ranges are skipped (undefined behaviour).

_U_CSR_SWEEP: frozenset[int] = frozenset(
    a
    for a in range(4096)
    if ((a >> 8) & 3) == 0  # user-privilege level only (bits[9:8]=00)
    and a not in range(0x800, 0x900)  # skip user custom2
    and a not in range(0xCC0, 0xD00)  # skip user custom3
)


# ── U-mode CSR sweep ──────────────────────────────────────────────────────


def _generate_csr_tests_u(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs from U-mode.

    Switches to U-mode, sweeps all user-accessible CSRs, then returns
    to M-mode via ecall.
    """
    covergroup = "SsstrictU_ucsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (U-mode)",
            "Read, write 0s/1s, set, clear every user-level CSR from U-mode.\n"
            "S/H/M CSRs are higher privilege and always trap from U-mode;\n"
            "that is architecturally known, so they are excluded here.\n"
            "Custom and reserved CSR ranges skipped.",
        )
    )

    # Mode switch is handled by _SPLIT_FILE_UMODE_GPR_INIT prepended to every
    # split file by generate/priv.py: each file starts from M-mode, runs
    # RVTEST_GOTO_LOWER_MODE Umode, then reloads GPRs before entering the body.
    # The body stays entirely in U-mode — all CSR accesses either trap as illegal
    # (caught by strap_handler_fastillegalinstr which writes scause/sepc/stval to
    # the signature and advances sepc) or execute silently.  RVTEST_CODE_END's
    # ecall from U-mode is not delegated, so it goes to Mtrampoline which restores
    # the saved M-mode sp and ends the test cleanly.
    all_csrs = sorted(_U_CSR_SWEEP)
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))
    lines.append("")

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictU",
    required_extensions=["Sm", "U", "Zicsr", "Ssstrict"],
    march_extensions=[
        "I",
        "V",
        "Zicsr",
    ],
)
def make_ssstrictu(test_data: TestData) -> list[str]:
    """SsstrictU — user-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_u(test_data))
    lines.extend(generate_illegal_instr(test_data, "SsstrictU_instr_cg"))
    lines.extend(generate_compressed_instr(test_data, "SsstrictU_comp_instr_cg"))
    lines.extend(generate_vector_illegal_instr(test_data, "SsstrictU_instr_cg"))
    return lines
