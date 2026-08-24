##################################
# priv/sv/suites/Svpbmt.py
#
# Svpbmt suite: page-based memory types in leaf and non-leaf PTEs.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svpbmt suite table: PBMT values in leaf PTEs (PBMT=3 reserved) and non-leaf PTEs."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import RWX_RUNNER_RV64, RWX_VERIFICATION
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase
from testgen.priv.sv.suites.Sv import _leaf, _levels_desc, _sig3, _spec, _u, _walk

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

_PBMT = (("(1 << 61)", "PBMT=1", 0, False), ("(2 << 61)", "PBMT=2", 0, False), ("(3 << 61)", "PBMT=3", 3, True))


def _files() -> list[FileSpec]:
    specs: list[FileSpec] = []
    for name in ("sv39", "sv48", "sv57"):
        sv = SVMODES[name]
        setup = ("  LI(t0, MENVCFG_PBMTE)", "  csrs menvcfg, t0")
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"

            # Leaf PBMT values at every level; PBMT=3 (reserved) is guarded on priv 1.12
            cases: list[SvCase] = []
            n = 0
            for level in _levels_desc(sv):
                for bits, desc, faults, guarded in _PBMT:
                    n += 1
                    perms = f"{bits} | " + _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                    expected = "No fault" if faults == 0 else "Store, load & fetch page fault"
                    body = ["#ifdef S1P12P0_OR_LATER_SUPPORTED"] if guarded else []
                    body += [
                        f"  // Test case {n}: {desc} leaf PTE | Test in {mode[0]}-Mode | expected = {expected}",
                        *_walk(sv, level),
                        _leaf(sv, perms, level),
                        "  sfence.vma",
                        "",
                        f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, test{n}",
                    ]
                    if guarded:
                        body.append("#endif")
                    cases.append(
                        SvCase(
                            banner=(
                                f"Setup a PTE at level {level} with {desc}, RWX permissions given:",
                                "Then, in {mode}-Mode, the page is accessed --> required: " + expected,
                            ),
                            body=tuple(body),
                            sig_strs=_sig3(f"test{n}"),
                            faults=faults,
                            level=level,
                        )
                    )
            specs.append(
                _spec(
                    sv,
                    "Svpbmt",
                    mode,
                    cases,
                    (RWX_VERIFICATION, RWX_RUNNER_RV64),
                    extra_ext=("Svpbmt",),
                    banner=_ATTR,
                    setup_asm=setup,
                    emit_trap_count=False,
                )
            )

            # PBMT values in non-leaf PTEs (should be ignored / fault-free walk);
            # the whole file is guarded on priv 1.12.
            cases = []
            n = 0
            for level in [lv for lv in _levels_desc(sv) if lv < sv.levels - 1]:
                for bits, desc, _, _guarded in _PBMT:
                    n += 1
                    perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                    body = [
                        (
                            f"  // Test case {n}: {desc} in the non-leaf PTE at level {level + 1}"
                            f" | Test in {mode[0]}-Mode | expected = No fault"
                        ),
                        *_walk(sv, level, special={level + 1: f"{bits} | PTE_V"}),
                        _leaf(sv, perms, level),
                        "  sfence.vma",
                        "",
                        f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, test{n}",
                    ]
                    cases.append(
                        SvCase(
                            banner=(
                                f"Setup a non-leaf PTE at level {level + 1} with {desc}:",
                                "Then, in {mode}-Mode, the page below it is accessed --> required: No fault",
                            ),
                            body=tuple(body),
                            sig_strs=_sig3(f"test{n}"),
                            faults=0,
                            level=level,
                        )
                    )
            specs.append(
                _spec(
                    sv,
                    "Svpbmt_nonleaf",
                    mode,
                    cases,
                    (RWX_VERIFICATION, RWX_RUNNER_RV64),
                    extra_ext=("Svpbmt",),
                    banner=_ATTR,
                    setup_asm=setup,
                    emit_trap_count=False,
                    code_guard="S1P12P0_OR_LATER_SUPPORTED",
                )
            )
    return specs


@add_sv_suite("Svpbmt")
def svpbmt_files() -> list[FileSpec]:
    """Svpbmt: leaf and non-leaf PBMT encodings across sv39/48/57, S and U mode."""
    return _files()
