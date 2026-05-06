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

from random import seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

from .SsstrictCommon import generate_compressed_instr, generate_csr_sweep_body, generate_illegal_instr

# ── CSR skip set ──────────────────────────────────────────────────────────

_M_CSR_SKIP: frozenset[int] = frozenset(
    list(range(0x3A0, 0x3F0))  # PMP regs
    + list(range(0x7A0, 0x7B0))  # debug trigger regs
    + list(range(0x7C0, 0x800))  # M-mode custom1
    + list(range(0xBC0, 0xC00))  # M-mode custom2
    + list(range(0xF00, 0x1000))  # M-mode read-only (includes custom3 0xFC0-0xFFF)
    + list(range(0x5C0, 0x600))  # S-mode custom1
    + list(range(0x6C0, 0x700))  # H-mode custom1
    + list(range(0x9C0, 0xA00))  # S-mode custom2
    + list(range(0xAC0, 0xB00))  # H-mode custom2
    + list(range(0xDC0, 0xE00))  # S-mode custom3
    + list(range(0xEC0, 0xF00))  # H-mode custom3
    + list(range(0x800, 0x900))  # user custom2
    + list(range(0xCC0, 0xD00))  # user custom3
    + [
        0x340,
        0x747,
    ]  # mscratch, mseccfg — skip to avoid enabling epmp and PMP troubles in M-mode & to overwrite mscratch with random values in the sweep
)


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
    required_extensions=["Sm", "Zicsr"],
    march_extensions=[
        # Zcf excluded — RV32-only.
        # Vector excluded — covered by SsstrictV.
        # Zbc/Zacas/Zcb excluded: not needed as assembler mnemonics,
        # not in non-max configs, not supported by GCC < 14.
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
def make_ssstrictsm(test_data: TestData) -> list[str]:
    """SsstrictSm — machine-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_m(test_data))
    lines.extend(generate_illegal_instr(test_data, "SsstrictSm_instr_cg"))
    lines.extend(generate_compressed_instr(test_data, "SsstrictSm_comp_instr_cg"))
    return lines
