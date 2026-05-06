##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU — user-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. Switch to U-mode via RVTEST_GOTO_LOWER_MODE Umode.
2. CSR sweep from U-mode (user-privilege CSRs only: 0x000-0x0FF,
   0x400-0x4FF, 0xC00-0xCBF).
   - All S/H/M CSRs raise illegal-instruction from U-mode.
   - Custom and reserved ranges are skipped.
3. Return to M-mode, then run the illegal instruction and compressed
   sweeps (from M-mode so the fast handler handles every trap correctly).
"""

from random import seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

from .SsstrictCommon import SAFE_REGS, generate_csr_sweep_body, generate_compressed_instr, generate_illegal_instr

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

    # Switch to U-mode — no trailing blank so the splitter cannot cut between
    # this and the first CSR instruction.
    lines.extend(
        [
            "",
            "# Switch to user mode for CSR sweep",
            "\tRVTEST_GOTO_LOWER_MODE Umode",
        ]
    )

    # The U-mode CSR sweep stays in U-mode continuously from the opening
    # RVTEST_GOTO_LOWER_MODE Umode to the closing RVTEST_GOTO_MMODE.
    # No intra-sweep mode switches are emitted — same rationale as SsstrictS.py:
    # RVTEST_GOTO_MMODE is a no-op on some configs, so any intra-sweep
    # GOTO Umode would execute from U-mode, crashing identically.
    # All CSR accesses from U-mode either trap as illegal (handled by fast handler)
    # or execute silently — Mtrampoline is never fired, save area sp stays valid.
    all_csrs = sorted(_U_CSR_ACCESSIBLE)
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))

    # Final return to M-mode after last batch
    lines.extend(
        [
            "",
            "# Return to machine mode after U-mode CSR sweep",
            "\tRVTEST_GOTO_MMODE",
            "",
        ]
    )

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictU",
    required_extensions=["Sm", "U", "Zicsr"],
    march_extensions=[
        # Zcf excluded — RV32-only.
        # Vector excluded — covered by SsstrictV.
        # Zbc/Zacas/Zcb excluded: not in non-max configs, not supported by GCC < 14.
        "I",
        "M",
        "A",
        "F",
        "D",
        "C",
        "Zicsr",
        "Zba",
        "Zbb",
        "Zbs",
        "Zca",
        "Zcd",
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
