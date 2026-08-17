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
    CODE_VA_IDENTITY,
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
    rv64_only,
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


def _same(name: str) -> tuple[str, str, str]:
    """Return one coverpoint repeated for all access kinds."""
    return (
        name,
        name,
        name,
    )


_BASELINE_UNMAPPED = _same("cp_baseline_unmapped")
_BASELINE_MAPPED_LOW = _same("cp_baseline_mapped_low")


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
        _BASELINE_UNMAPPED,
    ),
    _Case(
        "ukte_set_unmapped_high",
        True,
        _QUALIFIED,
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
        _BASELINE_UNMAPPED,
    ),
    _Case(
        "ukte_set_unmapped_low",
        True,
        _BASELINE_UNMAPPED,
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
        "RVTEST_GOTO_LOWER_MODE Umode",
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

    lines.append("RVTEST_GOTO_MMODE")
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
        *enable_s_stage(
            mode,
            code_va=CODE_VA_IDENTITY,
        ),
        # Page faults from U-mode are delegated to S-mode. Keep them in M-mode
        # so the framework can record the trap and resume the test body.
        "# Clear medeleg for instruction, load, and store/AMO page faults.",
        "LI(x8, 0xb000)",
        "csrc medeleg, x8",
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
    required_extensions=["Svukte"],
    march_extensions=["S"],
)
def make_svuktes(test_data: TestData) -> list[TestChunk]:
    """Generate SvukteS U-mode tests for every supported RV64 mode."""
    tc = test_data.begin_test_chunk()
    regs = allocate_regs(test_data)

    body = [
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
    tc.code.extend(rv64_only(body))

    release_regs(
        test_data,
        regs,
    )

    return [test_data.end_test_chunk()]
