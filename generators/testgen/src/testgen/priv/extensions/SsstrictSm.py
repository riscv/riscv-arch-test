##################################
# priv/extensions/SsstrictSm.py
#
# Ssstrict machine-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from M-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictSm — machine-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SsstrictCommon import (
    H_CUSTOM_CSR_RANGES,
    M_CUSTOM_CSR_RANGES,
    S_CUSTOM_CSR_RANGES,
    USER_CUSTOM_CSR_RANGES,
    csr_range_set,
    generate_ssstrict_suite,
)
from testgen.priv.registry import add_priv_test_generator

# ── CSR skip set ──────────────────────────────────────────────────────────

_M_CSR_SKIP: frozenset[int] = frozenset(
    csr_range_set(
        range(0x3A0, 0x3F0),  # PMP regs
        range(0x7A0, 0x7B0),  # debug trigger regs
        range(0xFC0, 0x1000),  # M-mode read-only
        *M_CUSTOM_CSR_RANGES,
        *S_CUSTOM_CSR_RANGES,
        *H_CUSTOM_CSR_RANGES,
        *USER_CUSTOM_CSR_RANGES,
    )
    | {
        0x340,  # mscratch: corrupts trap stack
        0x305,  # mtvec: corrupts trap stack
        0x747,  # mseccfg: confuses M-mode
        0x5A8,  # scontext ignore, sail does not support it but other sims do
    }
)

<<<<<<< HEAD
=======

# ── M-mode CSR sweep ─────────────────────────────────────────────────────


def _generate_csr_tests_m(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs.

    Registers r1, r2, r3 are always chosen from SAFE_REGS (x7..x31).
    This prevents the sweep from corrupting framework-reserved registers
    (sp, gp, tp) or the fast handler's scratch registers (t0, t1).
    """
    covergroup = "SsstrictSm_mcsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (M-mode)",
            "Read, write 0s/1s, set, clear every non-skipped CSR from M-mode.\n"
            "All scratch registers chosen from x7-x31 only to preserve\n"
            "framework-reserved regs (x2/sp, x3/gp, x4/tp) and fast-handler\n"
            "scratch regs (x5/t0, x6/t1).",
        )
    )

    lines.extend(
        [
            "",
            "# Lock PMP region 0 (TOR RWX) so PMP CSR reads do not corrupt config",
            "\tli t2, 0x8F",  # t2=x7, safe
            "\tcsrw pmpcfg0, t2",
            "",
        ]
    )

    all_csrs = [a for a in range(4096) if a not in _M_CSR_SKIP]
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))

    return lines

# ── Entry point ────────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictSm",
    required_extensions=["Sm", "Zicsr", "Ssstrict"],
    march_extensions=[
        "I",
        "V",
        "Zicsr",
    ],
    extra_defines=["#define RVTEST_USE_FAST_TRAP_HANDLER"],
)
def make_ssstrictsm(test_data: TestData) -> list[TestChunk]:
    """SsstrictSm — machine-mode strict compliance tests."""
    return generate_ssstrict_suite(test_data, "SsstrictSm", "M", _M_CSR_SKIP)
