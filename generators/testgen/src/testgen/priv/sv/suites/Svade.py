##################################
# priv/sv/suites/svade.py
#
# Svade suite: A/D-bit page faults with hardware A/D updates disabled.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svade suite table: PTE.A/PTE.D combinations trap when menvcfg.ADUE is clear."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import HR, RWX_RUNNER_RV32, RWX_RUNNER_RV64, RWX_VERIFICATION
from testgen.priv.sv.model import SVMODES, FileSpec, SvMode, TestCase

# (inline desc, banner desc, extra PTE bits, banner result, inline result, faults)
_DA_CASES = (
    (
        "PTE.D unset and PTE.A set",
        "PTE.D unset, PTE.A set",
        ("PTE_A",),
        "Then, access the page in {mode}-Mode. Expected: Store-page-fault",
        "Store page fault",
        1,
    ),
    (
        "Both PTE.D and PTE.A set",
        "PTE.D set, PTE.A set",
        ("PTE_D", "PTE_A"),
        "Then, access the page in {mode}-Mode. Expected: No fault should occur.",
        "No Fault",
        0,
    ),
    (
        "PTE.D set and PTE.A unset",
        "PTE.D set, PTE.A unset",
        ("PTE_D",),
        "Then access the page in {mode}-Mode. Expected: Store, Load & Fetch page fault",
        "Store, Load & Fetch page fault",
        3,
    ),
    (
        "Both PTE.D and PTE.A unset",
        "PTE.D unset, PTE.A unset",
        (),
        "Then access the page in {mode}-Mode. Expected: Store, Load & Fetch page fault",
        "Store, Load & Fetch page fault",
        3,
    ),
)

_RWXV = ("PTE_X", "PTE_W", "PTE_R", "PTE_V")

# Attribution preserved from the original hand-written files
_BANNER_RV64 = {
    "sv39": "// Developed by: Umer Shahid, Muhammad Abdullah, Muhammad Zain, Hamza Ali and Muhammad Ahmad",
    "sv48": "// Developed by: Umer Shahid & Muhammad Zain",
    "sv57": "// Developed by: Umer Shahid & Muhammad Zain",
}

_BANNER_SV32 = f"""\
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Muhammad Hammad Bashir, Allen Baum, Umer Shahid
{HR}
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
{HR}
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
// This test verifies the functioning of the A (Accessed) and D (Dirty) bits in the SV-32 virtual memory system.
//
// Access and Dirty Bit Test in {{mode}}-Mode with Software Update
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13."""


def _cases(sv: SvMode) -> tuple[TestCase, ...]:
    """All four A/D-bit combinations at every leaf level, top level first."""
    return tuple(
        TestCase(
            inline_desc=inline,
            banner_desc=banner,
            banner_result=result,
            inline_result=inline_result,
            level=level,
            leaf_perms=(*bits, *_RWXV),
            faults=faults,
        )
        for level in range(sv.levels - 1, -1, -1)
        for (inline, banner, bits, result, inline_result, faults) in _DA_CASES
    )


def _adue_clear(sv: SvMode) -> tuple[str, ...]:
    """Clear menvcfg.ADUE (menvcfgh on RV32) so A/D updates raise page faults (Svade)."""
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    return (
        f"  LI(t0, {mask})",
        f"  {f'csrc {csr}, t0':<73}// Enable Svade",
    )


@add_sv_suite("Svade")
def svade_files() -> list[FileSpec]:
    """One file per (satp mode, privilege mode); A/D-bit combinations at every page level."""
    specs: list[FileSpec] = []
    for sv in SVMODES.values():
        banner = _BANNER_SV32 if sv.xlen == 32 else _BANNER_RV64[sv.name]
        runner = RWX_RUNNER_RV32 if sv.xlen == 32 else RWX_RUNNER_RV64
        for mode in ("Smode", "Umode"):
            specs.append(
                FileSpec(
                    filename=f"{sv.name}_Svade_{mode}.S",
                    required_extensions=("I", sv.name.capitalize(), "Svade"),
                    march=sv.march,
                    svmode=sv,
                    priv_mode=mode,
                    banner_prefix=banner,
                    macro_blocks=(RWX_VERIFICATION, runner),
                    cases=_cases(sv),
                    setup_asm=_adue_clear(sv),
                )
            )
    return specs
