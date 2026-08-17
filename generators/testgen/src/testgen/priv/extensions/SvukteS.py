##################################
# priv/extensions/SvukteS.py
#
# SvukteS test generator: U-mode Svukte behavior driven by senvcfg.UKTE.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvukteS - Tests U-mode behavior of Svukte- and Non-Svukte-qualified accesses."""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SvukteCommon import (
    PTE_INVALID,
    PTE_USER_RWX,
    SV_MODES,
    SvMode,
    SvukteRegs,
    access_test,
    allocate_regs,
    bump_store_value,
    data_payload,
    deferred_sigupds,
    disable_translation,
    enable_s_stage,
    init_store_value,
    mode_guarded,
    release_regs,
    s_stage_pte,
    set_ukte,
    target_va,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "SvukteS_cg"

_ACCESS_KINDS = (
    "store",
    "load",
    "exec",
)

_QUALIFIED = (
    "cp_svukte_qualified_write_fault",
    "cp_svukte_qualified_read_fault",
    "cp_svukte_qualified_exec_fault",
)

_NOT_QUALIFIED_DISABLED = (
    "cp_not_svukte_qualified_disabled",
    "cp_not_svukte_qualified_disabled",
    "cp_not_svukte_qualified_disabled_i",
)

_NOT_QUALIFIED_ADDR = (
    "cp_not_svukte_qualified_addr",
    "cp_not_svukte_qualified_addr",
    "cp_not_svukte_qualified_addr_i",
)


_BASELINE_MAPPED_LOW = (
    "cp_not_svukte_qualified_addr_clear",
    "cp_not_svukte_qualified_addr_clear",
    "cp_not_svukte_qualified_addr_clear_i",
)


def _unmapped(half: str, ukte: bool) -> tuple[str, str, str]:
    """Name data and instruction faults for one unmapped page."""
    prefix = f"cp_unmapped_{half}_ukte_{'set' if ukte else 'clear'}"
    return (f"{prefix}_write", f"{prefix}_read", f"{prefix}_i")


@dataclass(frozen=True)
class _Case:
    """One UKTE setting and its access coverpoints."""

    bin_name: str
    ukte: bool
    coverpoints: tuple[str, str, str]


_UNMAPPED_HIGH_CASES = (
    _Case(
        "ukte_clear_unmapped_high",
        False,
        _unmapped("high", False),
    ),
    _Case(
        "ukte_set_unmapped_high",
        True,
        _unmapped("high", True),
    ),
)

_MAPPED_HIGH_CASES = (
    _Case(
        "ukte_clear_mapped_high",
        False,
        _NOT_QUALIFIED_DISABLED,
    ),
    _Case(
        "ukte_set_mapped_high",
        True,
        _QUALIFIED,
    ),
)

_UNMAPPED_LOW_CASES = (
    _Case(
        "ukte_clear_unmapped_low",
        False,
        _unmapped("low", False),
    ),
    _Case(
        "ukte_set_unmapped_low",
        True,
        _unmapped("low", True),
    ),
)

_MAPPED_LOW_CASES = (
    _Case(
        "ukte_clear_mapped_low",
        False,
        _BASELINE_MAPPED_LOW,
    ),
    _Case(
        "ukte_set_mapped_low",
        True,
        _NOT_QUALIFIED_ADDR,
    ),
)


def _umode_case(
    test_data: TestData,
    mode: SvMode,
    regs: SvukteRegs,
    va: int,
    case: _Case,
) -> list[str]:
    """Emit one U-mode case."""
    lines = [
        "",
        (f"# {case.bin_name}: senvcfg.UKTE {'set' if case.ukte else 'clear'}, {mode.name}"),
        *set_ukte(
            regs,
            qualified=case.ukte,
        ),
        *target_va(
            mode,
            va,
            regs,
        ),
        *bump_store_value(regs),
        "RVTEST_TSBI_GOTO_UMODE",
    ]

    results: list[tuple[str, int]] = []

    for kind, coverpoint in zip(
        _ACCESS_KINDS,
        case.coverpoints,
        strict=True,
    ):
        asm, label, check_reg = access_test(
            test_data,
            regs,
            covergroup=covergroup,
            coverpoint=coverpoint,
            bin_name=f"{mode.name}_{case.bin_name}_{kind}",
            kind=kind,
        )
        lines.extend(asm)
        results.append((label, check_reg))

    lines.append("RVTEST_TSBI_GOTO_MMODE")
    lines.extend(
        deferred_sigupds(
            test_data,
            results,
        )
    )

    return lines


def _mode_block(
    test_data: TestData,
    mode: SvMode,
    regs: SvukteRegs,
) -> list[str]:
    """Emit every U-mode case for one translation mode."""
    lines = [
        (f"# ---- {mode.name}: U-mode accesses qualified by senvcfg.UKTE ----"),
        *enable_s_stage(mode),
        # Page faults from U-mode are delegated to S-mode by the standard boot.
        # Clear those delegation bits so the M-mode handler can resume the test.
        "# Clear medeleg for instruction, load, and store/AMO page faults.",
        f"LI(x{regs.scratch}, 0xb000)",
        f"csrc medeleg, x{regs.scratch}",
    ]

    for va, perms, cases, description in (
        (
            mode.va_data,
            PTE_INVALID,
            _UNMAPPED_HIGH_CASES,
            "unmapped supervisor-half address",
        ),
        (
            mode.va_data,
            PTE_USER_RWX,
            _MAPPED_HIGH_CASES,
            "permissive RWXU supervisor-half address",
        ),
        (
            mode.va_data_lower,
            PTE_INVALID,
            _UNMAPPED_LOW_CASES,
            "unmapped lower-half address",
        ),
        (
            mode.va_data_lower,
            PTE_USER_RWX,
            _MAPPED_LOW_CASES,
            "permissive RWXU lower-half address",
        ),
    ):
        lines.extend(
            [
                "",
                f"# {description}",
            ]
        )

        lines.extend(
            s_stage_pte(
                mode,
                "rvtest_data_1",
                perms,
                va,
            )
        )

        for case in cases:
            lines.extend(
                _umode_case(
                    test_data,
                    mode,
                    regs,
                    va,
                    case,
                )
            )

    lines.extend(
        [
            "",
            *disable_translation(),
        ]
    )

    return mode_guarded(
        mode,
        lines,
    )


@add_priv_test_generator(
    "SvukteS",
    required_extensions=["Svukte", "S", "Sm"],
    march_extensions=[],
    params=["MXLEN: 64"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svuktes(test_data: TestData) -> list[TestChunk]:
    """Generate SvukteS U-mode tests for every supported RV64 mode."""
    tc = test_data.begin_test_chunk()
    regs = allocate_regs(test_data)

    body = [
        "main:",
        *data_payload(regs),
        *init_store_value(regs),
    ]

    for mode in SV_MODES:
        body.extend(
            [
                "",
                *_mode_block(
                    test_data,
                    mode,
                    regs,
                ),
            ]
        )

    tc.code.append(
        comment_banner(
            "SvukteS",
            make_svuktes.__doc__,
        )
    )
    tc.code.extend(body)
    tc.trap_sigupd_count = 160

    release_regs(
        test_data,
        regs,
    )

    return [test_data.end_test_chunk()]
