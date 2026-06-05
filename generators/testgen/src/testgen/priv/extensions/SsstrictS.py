##################################
# priv/extensions/SsstrictS.py
#
# Ssstrict supervisor-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from S-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictS — supervisor-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. CSR sweep from S-mode (only CSRs accessible from S/HS and below).
2. Illegal instruction and compressed encoding sweeps.
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

# ── CSR skip set (S-mode) ─────────────────────────────────────────────────

_S_CSR_SKIP: frozenset[int] = frozenset(
    [0x180]  # satp     — skip: TLB flush / address-translation mode change
    + [0x105]  # stvec  — skip: overwriting stvec breaks the delegated-trap handler itself
    + [0x140]  # sscratch — skip: avoid corrupting framework save area
    + [0x5A8]  # scontext — skip: Sail traps (unimplemented Sdtrig), Spike does not; diverges signature
    # M-mode CSRs (bits[9:8]=11): skip — higher privilege than S-mode; already covered by S_coverage.svh
    + list(range(0x300, 0x400))  # M-mode standard (mstatus, misa, medeleg, mtvec, ...)
    + list(range(0x700, 0x800))  # M-mode debug/custom (dcsr, dpc, tselect, ...)
    + list(range(0xB00, 0xC00))  # M-mode counters (mcycle, minstret, mhpmcounterN, ...)
    + list(range(0xF00, 0x1000))  # M-mode info (mvendorid, marchid, mimpid, mhartid, ...)
    # Custom / reserved ranges: skip — undefined / implementation-specific behaviour
    + list(range(0x5C0, 0x600))  # S-mode custom1
    + list(range(0x6C0, 0x700))  # Hypervisor custom1
    + list(range(0x800, 0x900))  # user custom2
    + list(range(0x9C0, 0xA00))  # S-mode custom2
    + list(range(0xAC0, 0xB00))  # Hypervisor custom2
    + list(range(0xCC0, 0xD00))  # user custom3
    + list(range(0xDC0, 0xE00))  # S-mode custom3
    + list(range(0xEC0, 0xF00))  # Hypervisor custom3
)


# ── S-mode CSR sweep ──────────────────────────────────────────────────────


def _generate_csr_tests_s(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs from S-mode.

    Switches to S-mode, sweeps all non-skipped CSRs, then returns to
    M-mode via ecall so subsequent sections can use the fast handler.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (S-mode)",
            "Read, write 0s/1s, set, clear every S-mode CSR (priv=01).\n"
            "H-mode and M-mode CSRs are higher privilege and always trap from S-mode;\n"
            "that is architecturally known, so they are excluded here.\n"
            "satp skipped — TLB flush / address-translation side effects.",
        )
    )

    # Mode switch is handled by _SPLIT_FILE_SMODE_GPR_INIT prepended to every
    # split file by generate/priv.py: each file starts from M-mode, runs
    # RVTEST_GOTO_LOWER_MODE Smode (writing a valid M-mode sp into the framework
    # save area), then reloads GPRs before entering the body.  The body itself
    # stays entirely in S-mode — illegal accesses to M-mode CSRs are caught by
    # the S-mode strap handler (stvec) which writes scause/sepc/stval to the
    # signature and advances sepc.  RVTEST_CODE_END's ecall from S-mode is not
    # delegated (medeleg bit 9 is 0), so it goes to Mtrampoline which restores
    # the saved M-mode sp and ends the test cleanly.
    all_csrs = [a for a in range(4096) if a not in _S_CSR_SKIP]
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))
    lines.append("")

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictS",
    required_extensions=["S", "Zicsr", "Ssstrict"],
    march_extensions=[
        "I",
        "V",  # V included: sets vl/vtype for vector loads and stores in the encoding sweep
        "Zicsr",
    ],
)
def make_ssstrictss(test_data: TestData) -> list[str]:
    """SsstrictS — supervisor-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_s(test_data))
    lines.extend(generate_illegal_instr(test_data, "SsstrictS_instr_cg"))
    lines.extend(generate_compressed_instr(test_data, "SsstrictS_comp_instr_cg"))
    lines.extend(generate_vector_illegal_instr(test_data, "SsstrictS_instr_cg"))
    return lines
