##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU — user-mode strict/negative compliance tests.

The fast S-mode trap handler is NOT emitted here — generate/priv.py prepends
_FAST_SMODE_HANDLER_PREFIX (which installs strap_handler_fastillegalinstr at
stvec and delegates illegal instructions to S-mode via medeleg) plus
_SPLIT_FILE_UMODE_GPR_INIT (which issues RVTEST_GOTO_LOWER_MODE Umode) to
every split file.

Structure
---------
1. Per-split-file prefix switches to U-mode; the body stays in U-mode.
2. CSR sweep from U-mode (user-privilege CSRs only: 0x000-0x0FF,
   0x400-0x4FF, 0xC00-0xCBF).
   - All S/H/M CSRs raise illegal-instruction from U-mode, trapped by
     strap_handler_fastillegalinstr which records scause/sepc/stval.
   - Custom and reserved ranges are skipped.
3. Illegal instruction and compressed sweeps (appended by make_ssstrictu;
   still run under the S-mode delegation so traps are handled correctly).
"""

from random import seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

from .SsstrictCommon import generate_compressed_instr, generate_csr_sweep_body, generate_illegal_instr

# ── CSR skip set (U-mode) ─────────────────────────────────────────────────

# U-mode can only access CSRs with privilege bits[9:8]=00 (user-level):
#   0x000-0x0FF: user standard (all accessible)
#   0x400-0x4FF: user standard (performance counter shadows)
#   0x800-0x8FF: user custom2 — skip: undefined behaviour
#   0xC00-0xCBF: user read-only counters (cycle, time, instret, hpmcounterN)
#   0xCC0-0xCFF: user custom3 — skip
#
# All S/H/M CSRs (priv bits != 00) raise illegal-instruction from U-mode.
# Those are swept by SsstrictSm/S so we do not duplicate them here.

# Build the accessible set positively: only CSRs with bits[9:8]=00
_U_CSR_ACCESSIBLE: frozenset[int] = frozenset(
    a
    for a in range(4096)
    if ((a >> 8) & 3) == 0  # user-privilege level
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
            "Read, write 0s/1s, set, clear every user-accessible CSR from U-mode.\n"
            "S/H/M CSRs all raise illegal-instruction from U-mode.\n"
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
    all_csrs = sorted(_U_CSR_ACCESSIBLE)
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))
    lines.append("")

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictU",
    required_extensions=["Sm", "U", "Zicsr"],
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
    return lines
