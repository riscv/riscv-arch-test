##################################
# priv/sv/suites/Svnapot.py
#
# Svnapot suite: 64 KiB NAPOT translation contiguity and reserved encodings.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svnapot suite table: NAPOT 64KiB pages and reserved NAPOT encodings."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import RWX_RUNNER_RV64, RWX_VERIFICATION
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase
from testgen.priv.sv.suites.Sv import RUN_DIRECT_VA, V_RWX_VA, _leaf, _sig3, _spec, _walk

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

_NAPOT_VA = {"sv39": "0x140200000", "sv48": "0x0280C0410000", "sv57": "0x400280C0410000"}

# Three regions inside the 64KiB NAPOT range, exercised at offsets 0, 0x2000, 0xF000
_NAPOT_DATA = _t("napot_data")

_RESERVED_DATA = _t("napot_reserved_data")


def _napot_perms(umode: bool, extra: str = "(1 << 13) | ") -> str:
    u = "PTE_U | " if umode else ""
    return f"PTE_N | {extra}PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V"


@add_sv_suite("Svnapot")
def svnapot_files() -> list[FileSpec]:
    """Svnapot: 16-page NAPOT groups and reserved NAPOT encodings, sv39/48/57 x S/U."""
    specs: list[FileSpec] = []
    for name, va in _NAPOT_VA.items():
        sv = SVMODES[name]
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"

            # A full 16-entry NAPOT group; access three of the pages
            perms = _napot_perms(umode)
            body = [
                "  // Test case 1: 64KiB NAPOT group of 16 PTEs; access three pages of the group",
                *_walk(sv, 0),
                _leaf(sv, perms, 0),
            ]
            body += [
                f"  PTE_SETUP_{sv.suffix}(rvtest_data_1, ({perms}), (va_data+0x{off:X}000), LEVEL0)"
                for off in range(1, 16)
            ]
            body += [
                "  sfence.vma",
                "",
                f"  TEST_CASES_RUNNER {mode}, va_data,        LEVEL0, test1_access1",
                f"  TEST_CASES_RUNNER {mode}, va_data+0x2000, LEVEL0, test1_access2",
                f"  TEST_CASES_RUNNER {mode}, va_data+0xF000, LEVEL0, test1_access3",
            ]
            sig = tuple(
                (f"test1_access{k}_{op}", f"Mismatch during {insn} in Test Case 1, Access {k}!")
                for k in (1, 2, 3)
                for op, insn in (("store", "sw"), ("load", "lw"), ("exec", "jalr"))
            )
            cases = [
                SvCase(
                    banner=(
                        "PTE.N set with PPN[3:0]=0b1000 (64KiB NAPOT group), RWX permissions given (level 0):",
                        "Then, in {mode}-Mode, three pages of the group are accessed --> required: No fault",
                    ),
                    body=tuple(body),
                    sig_strs=sig,
                    faults=0,
                    level=0,
                )
            ]
            specs.append(
                _spec(
                    sv,
                    "Svnapot",
                    mode,
                    cases,
                    (V_RWX_VA, RUN_DIRECT_VA),
                    extra_ext=("Svnapot",),
                    banner=_ATTR,
                    va_defs=(("va_data", va),),
                    data_align=16,
                    data_region_body=_NAPOT_DATA,
                    emit_trap_count=False,
                )
            )

            # Reserved NAPOT encodings: N on superpages, and N with reserved PPN[3:0]
            cases = []
            n = 0
            for level in range(sv.levels - 1, 0, -1):
                n += 1
                cases.append(
                    SvCase(
                        banner=(
                            f"PTE.N set on a superpage at level {level} (reserved):",
                            "Then, in {mode}-Mode, the page is accessed --> required: Load, Store & Fetch Page Fault",
                        ),
                        body=(
                            f"  // Test case {n}: PTE.N on a level {level} superpage | expected = RWX fault",
                            *_walk(sv, level),
                            _leaf(sv, _napot_perms(umode, extra=""), level),
                            "  sfence.vma",
                            "",
                            f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, test{n}",
                        ),
                        sig_strs=_sig3(f"test{n}"),
                        faults=3,
                        level=level,
                    )
                )
            for enc in ("(1 << 10) | ", "(2 << 10) | ", "(4 << 10) | ", ""):
                n += 1
                desc = f"PPN[3:0]={enc.strip(' |')}" if enc else "PPN[3:0]=0"
                cases.append(
                    SvCase(
                        banner=(
                            f"PTE.N set with reserved encoding {desc} at level 0:",
                            "Then, in {mode}-Mode, the page is accessed --> required: Load, Store & Fetch Page Fault",
                        ),
                        body=(
                            f"  // Test case {n}: PTE.N with reserved encoding {desc} | expected = RWX fault",
                            *_walk(sv, 0),
                            _leaf(sv, _napot_perms(umode, extra=enc), 0),
                            "  sfence.vma",
                            "",
                            f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL0, test{n}",
                        ),
                        sig_strs=_sig3(f"test{n}"),
                        faults=3,
                        level=0,
                    )
                )
            specs.append(
                _spec(
                    sv,
                    "Svnapot_reserved_enc",
                    mode,
                    cases,
                    (RWX_VERIFICATION, RWX_RUNNER_RV64),
                    extra_ext=("Svnapot",),
                    banner=_ATTR,
                    va_defs=(("va_data", va),),
                    data_align=16,
                    data_region_body=_RESERVED_DATA,
                    emit_trap_count=False,
                    code_guard="S1P12P0_OR_LATER_SUPPORTED",
                )
            )
    return specs
