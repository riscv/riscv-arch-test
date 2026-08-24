##################################
# priv/sv/suites/Sv.py
#
# Sv suite: core virtual-memory behavior (PTE permissions, satp, mstatus VM fields).
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sv suite table: 134 files covering PTE encodings, satp, and mstatus VM controls.

Each topic below corresponds to one family of hand-written test files. Topics are
built from freeform :class:`SvCase` entries so each can express its own PTE walk,
runner flavor, and signature layout; the local ``.macro`` blocks are verbatim
copies from the original files (see ``testgen.priv.sv.macros`` for the rationale).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import HR, RWX_RUNNER_RV32, RWX_RUNNER_RV64, RWX_VERIFICATION
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode

# ----------------------------------------------------------------------------------
# Banner prefixes (comments; per-file authorship consolidated into one credit line)
# ----------------------------------------------------------------------------------

_ATTR = (
    "// Developed by: Umer Shahid, Muhammad Zain, Muhammad Abdullah, Hamza Ali, Muhammad Ahmad,"
    " Muhammad Hammad Bashir, and Allen Baum"
)

_SV32_BSD = f"""\
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Muhammad Hammad Bashir, Allen Baum, Umer Shahid
{HR}
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause"""

# sv32 topics whose original files carried the BSD-3-Clause banner block
_SV32_BSD_TOPICS = {
    "invalid_pte",
    "misaligned_page",
    "mstatus_mprv",
    "mstatus_mxr",
    "nleaf_pte_level0",
    "pte_reserved_rwx",
    "pte_rsw",
    "satp_access_test",
    "spage",
    "spage_access",
    "upage",
    "upage_mprv_set_sum_set",
    "upage_mprv_set_sum_unset",
    "upage_mstatus_sum_set",
    "upage_mstatus_sum_unset",
}


def _prefix(sv: SvMode, topic: str) -> str:
    return _SV32_BSD if (sv.xlen == 32 and topic in _SV32_BSD_TOPICS) else _ATTR


# ----------------------------------------------------------------------------------
# Verbatim macro variants (beyond the shared RWX battery/runners in macros.py)
# ----------------------------------------------------------------------------------

# MPRV topics: fetch uses the physical address (instruction fetch ignores MPRV)
V_RWX_PHYS_FETCH = _t("v_rwx_phys_fetch")

# upage_mprv_set_sum_unset: the store traps and the trap clears MPRV, so re-set it
V_RWX_MPRV_SUM_UNSET = _t("v_rwx_mprv_sum_unset")

# Direct-VA battery (misaligned pages, NAPOT, non-leaf-at-level-0): VA passed in
V_RWX_VA = _t("v_rwx_va")

# mstatus.SBE topics: big-endian PTEs; only store/load are checked
V_SL_ONLY = _t("v_sl_only")

RUN_MPRV_RV64 = _t("run_mprv_rv64")

RUN_MPRV_RV32 = _t("run_mprv_rv32")

SETREQ_MPRV_S = _t("setreq_mprv_s")

SETREQ_MPRV_U = _t("setreq_mprv_u")

SETREQ_MPRV_SUM_SET = _t("setreq_mprv_sum_set")

SETREQ_MPRV_SUM_UNSET = _t("setreq_mprv_sum_unset")

RUN_DIRECT_VA = _t("run_direct_va")

RUN_SUM_RV64 = _t("run_sum_rv64")

RUN_SUM_RV32 = _t("run_sum_rv32")

RUN_2SIG_RV64 = _t("run_2sig_rv64")

RUN_2SIG_RV32 = _t("run_2sig_rv32")

# pte_rsw: standard runner plus a per-level PTE readback checking the RSW field
_RSW_READBACKS = {name: _t(f"rsw_readback_{name}") for name in ("sv32", "sv39", "sv48", "sv57")}


def _run_rsw(sv: SvMode) -> str:
    base = RWX_RUNNER_RV32 if sv.xlen == 32 else RWX_RUNNER_RV64
    tail = (
        "\n"
        + _RSW_READBACKS[sv.name]
        + "\n  RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_read_pte, \\TEST_CASE\\()_read_pte_str)\n\n.endm\n"
    )
    return base.rstrip("\n").removesuffix(".endm") + tail


def _change_be(sv: SvMode) -> str:
    width, shift = (4, 24) if sv.xlen == 32 else (8, 56)
    return _t("change_pte_to_be").format(SUF=sv.suffix, width=width, shift=shift)


RUNNER_RW_BYTE = _t("runner_rw_byte")

RUNNER_RW_WORD = _t("runner_rw_word")

RUNNER_X_ONLY = _t("runner_x_only")

# ----------------------------------------------------------------------------------
# Shared builders
# ----------------------------------------------------------------------------------


def _std_macros(sv: SvMode) -> tuple[str, str]:
    return (RWX_VERIFICATION, RWX_RUNNER_RV32 if sv.xlen == 32 else RWX_RUNNER_RV64)


def _u(perms: str, umode: bool) -> str:
    """Insert PTE_U right after the D/A (and leading literal) prefix for U-mode pages."""
    if not umode:
        return perms
    toks = perms.split(" | ")
    idx = next(
        (i for i, t in enumerate(toks) if t not in ("PTE_D", "PTE_A") and not t.startswith("(")),
        len(toks),
    )
    return " | ".join([*toks[:idx], "PTE_U", *toks[idx:]])


def _walk(sv: SvMode, level: int, va: str = "va_data", special: dict[int, str] | None = None) -> list[str]:
    """Non-leaf walk lines for a leaf at ``level``; ``special`` overrides the perms at a given LEVEL."""
    lines = []
    for j in range(sv.levels - 2, level - 1, -1):
        perms = (special or {}).get(j + 1, "PTE_V")
        lines.append(f"  PTE_SETUP_{sv.suffix}(rvtest_slvl{j}_pg_tbl, ({perms}), va_data, LEVEL{j + 1})")
    return lines if va == "va_data" else [line.replace("va_data", va) for line in lines]


def _leaf(
    sv: SvMode, perms: str, level: int, va: str = "va_data", superpage: bool = True, label: str = "rvtest_data_1"
) -> str:
    macro = "SUPERPAGE_PTE_SETUP" if (superpage and level > 0) else "PTE_SETUP"
    return f"  {macro}_{sv.suffix}({label}, ({perms}), {va}, LEVEL{level})"


def _sig3(name: str) -> tuple[tuple[str, str], ...]:
    n = name.removeprefix("test")
    return (
        (f"{name}_store", f"Mismatch during sw in Test Case {n}!"),
        (f"{name}_load", f"Mismatch during lw in Test Case {n}!"),
        (f"{name}_exec", f"Mismatch during jalr in Test Case {n}!"),
    )


def _sig2(name: str) -> tuple[tuple[str, str], ...]:
    return _sig3(name)[:2]


def _case(
    sv: SvMode,
    n: int,
    level: int,
    banner: tuple[str, ...],
    inline: str,
    pte_lines: list[str],
    *,
    runner: str = "TEST_CASES_RUNNER",
    mode_arg: str,
    va: str = "va_data",
    pre: tuple[str, ...] = (),
    post: tuple[str, ...] = (),
    sig: tuple[tuple[str, str], ...] | None = None,
    faults: int = 0,
) -> SvCase:
    name = f"test{n}"
    body = [f"  // Test case {n}: {inline}", *pte_lines, "  sfence.vma", *pre, ""]
    body.append(f"  {runner} {mode_arg}, {va}, LEVEL{level}, {name}")
    body.extend(post)
    return SvCase(
        banner=banner,
        body=tuple(body),
        sig_strs=sig if sig is not None else _sig3(name),
        faults=faults,
        level=level,
    )


def _spec(sv: SvMode, topic: str, mode: str, cases: list[SvCase], macros: tuple[str, ...], **kw: Any) -> FileSpec:  # noqa: ANN401
    norun = kw.pop("norun", False)
    extra_ext = kw.pop("extra_ext", ())
    banner = kw.pop("banner", None)
    march = kw.pop("march", sv.march)
    ext = ("I", sv.ext, *extra_ext, *(("NORUN",) if norun else ()))
    filename = f"{sv.name}_{topic}_{mode}.S" if mode else f"{sv.name}_{topic}.S"
    return FileSpec(
        filename=filename,
        required_extensions=ext,
        march=march,
        svmode=sv,
        priv_mode=mode or "Smode",
        banner_prefix=banner if banner is not None else _prefix(sv, topic),
        macro_blocks=macros,
        sv_cases=tuple(cases),
        **kw,
    )


def _levels_desc(sv: SvMode) -> list[int]:
    return list(range(sv.levels - 1, -1, -1))


# ----------------------------------------------------------------------------------
# Topic builders
# ----------------------------------------------------------------------------------


def _t_invalid_pte(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R", umode)
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            (
                                f"PTE.V unset for the page at level {level} with RWX Permissions"
                                " (Read, write, execute page):"
                            ),
                            (
                                "Then, in {mode}-Mode, the page is accessed --> required:"
                                " Load-page-fault, Store-page-fault, Fetch-page-fault"
                            ),
                        ),
                        f"V bit unset | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                        [*_walk(sv, level), _leaf(sv, perms, level)],
                        mode_arg=mode,
                        faults=3,
                    )
                )
            specs.append(_spec(sv, "invalid_pte", mode, cases, _std_macros(sv)))


_CANONICAL_VA = {"sv39": "0x8000000140802000", "sv48": "0x8000028500403000", "sv57": "0x8007028500403000"}


def _t_canonical(specs: list[FileSpec]) -> None:
    for name, va in _CANONICAL_VA.items():
        sv = SVMODES[name]
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            f"Access a non-canonical virtual address mapped at level {level} with RWX permissions:",
                            (
                                "Then, in {mode}-Mode, the page is accessed --> required:"
                                " Load-page-fault, Store-page-fault, Fetch-page-fault"
                            ),
                        ),
                        f"Non-canonical VA | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                        [*_walk(sv, level), _leaf(sv, perms, level)],
                        mode_arg=mode,
                        faults=3,
                    )
                )
            specs.append(_spec(sv, "canonical", mode, cases, _std_macros(sv), va_defs=(("va_data", va),)))


def _t_global_pte(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        if sv.xlen == 32:
            asid_lines = ("  csrr  t0, satp", "  slli  t0, t0, 1", "  srli  t0, t0, 23", "  sfence.vma x0, t0")
        else:
            asid_lines = ("  csrr  t0, satp", "  slli  t0, t0, 4", "  srli  t0, t0, 48", "  sfence.vma x0, t0")
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                # The original files disagree on ordering: sv57 puts PTE_U before PTE_G
                u_g = "PTE_U | PTE_G" if sv.name == "sv57" else "PTE_G | PTE_U"
                base = u_g if umode else "PTE_G"
                perms = f"PTE_D | PTE_A | {base} | PTE_X | PTE_W | PTE_R | PTE_V"
                name1, name2 = f"test{n}_access1", f"test{n}_access2"
                body = [
                    (
                        f"  // Test case {n}: Global PTE at level {level} | Test in {mode[0]}-Mode"
                        " | access, sfence with ASID, access again | expected = No Fault"
                    ),
                    *_walk(sv, level),
                    _leaf(sv, perms, level),
                    "  sfence.vma",
                    "",
                    f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, {name1}",
                    "",
                    "  // Flush the TLB for the current ASID and access again",
                    *asid_lines,
                    "",
                    f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, {name2}",
                ]
                num = str(n)
                sig = tuple(
                    (f"{base}_{op}", f"Mismatch during {insn} in Test Case {num}, Access {k}!")
                    for k, base in ((1, name1), (2, name2))
                    for op, insn in (("store", "sw"), ("load", "lw"), ("exec", "jalr"))
                )
                cases.append(
                    SvCase(
                        banner=(
                            f"Global (PTE.G set) page at level {level} with RWX permissions:",
                            (
                                "Access in {mode}-Mode, sfence.vma with the current ASID, access again"
                                " --> required: No Fault"
                            ),
                        ),
                        body=tuple(body),
                        sig_strs=sig,
                        faults=0,
                        level=level,
                    )
                )
            specs.append(_spec(sv, "global_pte", mode, cases, _std_macros(sv)))


_MISALIGNED_VA = {
    "sv32": "0x90400000",
    "sv39": "0x140000000",
    "sv48": "0x028000000000",
    "sv57": "0x07000000000000",
}


def _t_misaligned_page(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            levels = [level for level in _levels_desc(sv) if level > 0]
            for n, level in enumerate(levels, start=1):
                perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            f"Misaligned superpage at level {level} (PPN low bits nonzero), RWX permissions:",
                            (
                                "Then, in {mode}-Mode, the page is accessed --> required:"
                                " Load-page-fault, Store-page-fault, Fetch-page-fault"
                            ),
                        ),
                        f"Misaligned superpage | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                        [*_walk(sv, level), _leaf(sv, perms, level, superpage=False)],
                        mode_arg=mode,
                        faults=3,
                    )
                )
            specs.append(
                _spec(
                    sv,
                    "misaligned_page",
                    mode,
                    cases,
                    (V_RWX_VA, RUN_DIRECT_VA),
                    va_defs=(("va_data", _MISALIGNED_VA[sv.name]),),
                )
            )


def _t_mstatus_mprv(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            setreq = SETREQ_MPRV_S if mode == "Smode" else SETREQ_MPRV_U
            runner = RUN_MPRV_RV32 if sv.xlen == 32 else RUN_MPRV_RV64
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            f"mstatus.MPRV set with MPP={mode[0]} and an RWX page at level {level}:",
                            (
                                "Loads and stores in M-Mode use the translated address; the fetch uses"
                                " the physical address --> required: No Fault"
                            ),
                        ),
                        f"MPRV set, MPP={mode[0]} | RWX bit set | expected = No Fault",
                        [*_walk(sv, level), _leaf(sv, perms, level)],
                        mode_arg="Mmode",
                        faults=0,
                    )
                )
            specs.append(_spec(sv, "mstatus_mprv", mode, cases, (V_RWX_PHYS_FETCH, runner, setreq)))


def _t_mstatus_mxr(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            n = 0
            for level in _levels_desc(sv):
                for op, expected, faults in (("csrc", "Load & Store page fault", 2), ("csrs", "Store page fault", 1)):
                    n += 1
                    perms = _u("PTE_D | PTE_A | PTE_X | PTE_V", umode)
                    cases.append(
                        _case(
                            sv,
                            n,
                            level,
                            (
                                (
                                    f"Execute-only page at level {level} with mstatus.MXR"
                                    f" {'cleared' if op == 'csrc' else 'set'}:"
                                ),
                                "Then, in {mode}-Mode, the page is accessed --> required: " + expected,
                            ),
                            f"X-only page, MXR {'unset' if op == 'csrc' else 'set'}"
                            f" | Test in {mode[0]}-Mode | expected = {expected}",
                            [*_walk(sv, level), _leaf(sv, perms, level)],
                            mode_arg=mode,
                            pre=("  LI(   t0, MSTATUS_MXR)", f"  {op}  mstatus, t0"),
                            faults=faults,
                        )
                    )
            specs.append(_spec(sv, "mstatus_mxr", mode, cases, _std_macros(sv)))


def _sbe_setup(sv: SvMode, with_sum: bool) -> tuple[str, ...]:
    csr, mask = ("mstatush", "MSTATUSH_SBE") if sv.xlen == 32 else ("mstatus", "MSTATUS_SBE")
    lines = [f"  LI(   t0, {mask})", f"  csrs  {csr}, t0"]
    if with_sum:
        lines += ["  LI(   t0, MSTATUS_SUM)", "  csrs  mstatus, t0"]
    return tuple(lines)


def _walk_be(sv: SvMode, level: int) -> list[str]:
    lines = []
    for line in _walk(sv, level):
        lines.extend([line, "  CHANGE_PTE_TO_BE"])
    return lines


def _t_mstatus_sbe(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for topic, with_sum in (("mstatus_sbe_set", False), ("mstatus_sbe_and_sum_set", True)):
            umode_page = with_sum  # sbe_and_sum tests a U page from S-mode with SUM set
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode_page)
                if sv.xlen == 32 and level == 0:
                    perms += " | PTE_SOFT"
                sig = _sig2(f"test{n}") if with_sum else _sig3(f"test{n}")
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            (
                                f"Big-endian PTEs (mstatus.SBE set{' with mstatus.SUM' if with_sum else ''})"
                                f" for an RWX page at level {level}:"
                            ),
                            "Then, in S-Mode, the page is accessed --> required: No Fault",
                        ),
                        "Big-endian PTE | Test in S-Mode | RWX bit set | expected = No Fault",
                        [*_walk_be(sv, level), _leaf(sv, perms, level), "  CHANGE_PTE_TO_BE"],
                        mode_arg="Smode",
                        sig=sig,
                        faults=0,
                    )
                )
            verif = V_SL_ONLY if with_sum else RWX_VERIFICATION
            if with_sum:
                runner = RUN_2SIG_RV32 if sv.xlen == 32 else RUN_2SIG_RV64
            else:
                runner = RWX_RUNNER_RV32 if sv.xlen == 32 else RWX_RUNNER_RV64
            specs.append(
                _spec(
                    sv,
                    topic,
                    "Smode",
                    cases,
                    (verif, runner, _change_be(sv)),
                    norun=True,
                    code_pte_change_be=True,
                    setup_asm=_sbe_setup(sv, with_sum),
                )
            )


def _t_nleaf_pte_dau(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            n = 0
            for table_level in range(sv.levels - 1, 0, -1):
                for bit in ("PTE_D", "PTE_A", "PTE_U"):
                    n += 1
                    perms = _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                    cases.append(
                        _case(
                            sv,
                            n,
                            0,
                            (
                                (
                                    f"Non-leaf PTE at level {table_level} with {bit.removeprefix('PTE_')}"
                                    " bit set (reserved for non-leaf PTEs):"
                                ),
                                (
                                    "Then, in {mode}-Mode, the page is accessed --> required:"
                                    " Load-page-fault, Store-page-fault, Fetch-page-fault"
                                ),
                            ),
                            f"Non-leaf {bit.removeprefix('PTE_')} bit set at level {table_level}"
                            f" | Test in {mode[0]}-Mode | expected = RWX fault",
                            [
                                *_walk(sv, 0, special={table_level: f"{bit} | PTE_V"}),
                                _leaf(sv, perms, 0),
                            ],
                            mode_arg=mode,
                            faults=3,
                        )
                    )
            specs.append(
                _spec(sv, "nleaf_pte_DAU", mode, cases, _std_macros(sv), code_guard="S1P12P0_OR_LATER_SUPPORTED")
            )


def _t_nleaf_pte_level0(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        macros = (V_RWX_VA, RUN_DIRECT_VA) if sv.name == "sv39" else _std_macros(sv)
        for mode in ("Smode", "Umode"):
            cases = [
                _case(
                    sv,
                    1,
                    0,
                    (
                        "Non-leaf encoding (V only, no RWX) in a level 0 PTE:",
                        (
                            "Then, in {mode}-Mode, the page is accessed --> required:"
                            " Load-page-fault, Store-page-fault, Fetch-page-fault"
                        ),
                    ),
                    f"Level 0 PTE with pointer encoding | Test in {mode[0]}-Mode | expected = RWX fault",
                    [*_walk(sv, 0), _leaf(sv, _u("PTE_V", mode == "Umode"), 0)],
                    mode_arg=mode,
                    faults=3,
                )
            ]
            specs.append(_spec(sv, "nleaf_pte_level0", mode, cases, macros))


def _t_pte_reserved_rwx(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            n = 0
            for level in _levels_desc(sv):
                for perms_base, desc in (
                    ("PTE_D | PTE_A | PTE_X | PTE_W | PTE_V", "W and X set without R"),
                    ("PTE_D | PTE_A | PTE_W | PTE_V", "W set without R"),
                ):
                    n += 1
                    cases.append(
                        _case(
                            sv,
                            n,
                            level,
                            (
                                f"Reserved RWX encoding ({desc}) at level {level}:",
                                (
                                    "Then, in {mode}-Mode, the page is accessed --> required:"
                                    " Load-page-fault, Store-page-fault, Fetch-page-fault"
                                ),
                            ),
                            f"Reserved encoding: {desc} | Test in {mode[0]}-Mode | expected = RWX fault",
                            [*_walk(sv, level), _leaf(sv, _u(perms_base, umode), level)],
                            mode_arg=mode,
                            faults=3,
                        )
                    )
            specs.append(
                _spec(sv, "pte_reserved_rwx", mode, cases, _std_macros(sv), code_guard="S1P12P0_OR_LATER_SUPPORTED")
            )


def _sig_rsw(sv: SvMode, name: str) -> tuple[tuple[str, str], ...]:
    n = name.removeprefix("test")
    bang = "" if sv.name == "sv39" else "!"
    return (*_sig3(name), (f"{name}_read_pte", f"Mismatch in PTE value in Test Case {n}{bang}"))


def _t_pte_rsw(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        va_defs = (("va_data", "0x04007000"),) if sv.xlen == 32 else None
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases = []
            n = 0
            for level in _levels_desc(sv):
                for rsw, desc in (("(1 << 8)", "RSW=01"), ("(1 << 9)", "RSW=10"), ("(1 << 9) | (1 << 8)", "RSW=11")):
                    n += 1
                    perms = f"{rsw} | " + _u("PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", umode)
                    cases.append(
                        _case(
                            sv,
                            n,
                            level,
                            (
                                f"PTE with {desc} in the RSW field and RWX permissions at level {level}:",
                                (
                                    "Then, in {mode}-Mode, the page is accessed and the PTE is read back"
                                    " --> required: No Fault, RSW unchanged"
                                ),
                            ),
                            f"{desc} | Test in {mode[0]}-Mode | RWX bit set | expected = No Fault",
                            [*_walk(sv, level), _leaf(sv, perms, level)],
                            mode_arg=mode,
                            sig=_sig_rsw(sv, f"test{n}"),
                            faults=0,
                        )
                    )
            specs.append(_spec(sv, "pte_rsw", mode, cases, (RWX_VERIFICATION, _run_rsw(sv)), va_defs=va_defs))


def _t_pte_reserved_field(specs: list[FileSpec]) -> None:
    for name in ("sv39", "sv48", "sv57"):
        sv = SVMODES[name]
        top = sv.levels - 1
        cases = []
        for n, bit in enumerate(range(54, 61), start=1):
            perms = f"(1 << {bit}) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"
            cases.append(
                _case(
                    sv,
                    n,
                    top,
                    (
                        f"Reserved PTE bit {bit} set with RWX permissions at level {top}:",
                        (
                            "Then, in S-Mode, the page is accessed --> required:"
                            " Load-page-fault, Store-page-fault, Fetch-page-fault"
                        ),
                    ),
                    f"Reserved bit {bit} set | Test in S-Mode | expected = RWX fault",
                    [_leaf(sv, perms, top)],
                    mode_arg="Smode",
                    faults=3,
                )
            )
        specs.append(
            _spec(sv, "pte_reserved_field", "Smode", cases, _std_macros(sv), code_guard="S1P12P0_OR_LATER_SUPPORTED")
        )


def _t_svpbmt_disabled(specs: list[FileSpec]) -> None:
    for name in ("sv39", "sv48", "sv57"):
        sv = SVMODES[name]
        if name == "sv39":
            setup = (
                "  #ifdef SM1P12P0_OR_LATER_SUPPORTED",
                "      LI(t0, MENVCFG_PBMTE)",
                "      csrc menvcfg, t0",
                "  #endif",
            )
        else:
            setup = ("  LI(t0, MENVCFG_PBMTE)", "  csrc menvcfg, t0")
        # 2b. and sv57 spells the PBMT values differently
        if name == "sv57":
            pbmt = (("(1 << 61)", "PBMT=1"), ("(2 << 61)", "PBMT=2"), ("(3 << 61)", "PBMT=3"))
        else:
            pbmt = (("(1 << 61)", "PBMT=1"), ("(1 << 62)", "PBMT=2"), ("(1 << 62) | (1 << 61)", "PBMT=3"))
        top = sv.levels - 1
        cases = []
        for n, (bits, desc) in enumerate(pbmt, start=1):
            perms = f"{bits} | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"
            cases.append(
                _case(
                    sv,
                    n,
                    top,
                    (
                        f"PTE with {desc} while menvcfg.PBMTE is clear (Svpbmt disabled), level {top}:",
                        (
                            "Then, in S-Mode, the page is accessed --> required:"
                            " Load-page-fault, Store-page-fault, Fetch-page-fault"
                        ),
                    ),
                    f"{desc}, PBMTE disabled | Test in S-Mode | expected = RWX fault",
                    [_leaf(sv, perms, top)],
                    mode_arg="Smode",
                    faults=3,
                )
            )
        specs.append(
            _spec(
                sv,
                "svpbmt_disabled",
                "Smode",
                cases,
                _std_macros(sv),
                code_guard="S1P12P0_OR_LATER_SUPPORTED",
                setup_asm=setup,
            )
        )


_NAPOT_VA = {"sv39": "0x140860000", "sv48": "0x028500430000", "sv57": "0x07028500430000"}


def _t_svnapot_not_supported(specs: list[FileSpec]) -> None:
    for name, va in _NAPOT_VA.items():
        sv = SVMODES[name]
        napot_bit = "PTE_N" if name == "sv39" else "(1 << 63)"
        perms = f"{napot_bit} | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"
        cases = [
            _case(
                sv,
                1,
                0,
                (
                    (
                        "Bit 63 Set (NAPOT indicator, but reserved as SVNAPOT is not supported),"
                        " RWX permissions given (level 0):"
                    ),
                    "Then, in S-Mode, the page is accessed --> required: Load, Store & Fetch Page Fault",
                ),
                "Test in S-Mode | RWX bit set | Bit 63 (PTE.N) set | PTE.PPN0[3] set (64KiB region encoding)",
                [*_walk(sv, 0), _leaf(sv, perms, 0)],
                mode_arg="Smode",
                faults=3,
            )
        ]
        specs.append(
            _spec(
                sv,
                "svnapot_not_supported",
                "Smode",
                cases,
                (V_RWX_VA, RUN_DIRECT_VA) if name == "sv39" else _std_macros(sv),
                code_guard="S1P12P0_OR_LATER_SUPPORTED",
                va_defs=(("va_data", va),),
                data_align=16,
            )
        )


_PAGE_PERMS = (
    ("PTE_X | PTE_W | PTE_R", "RWX"),
    ("PTE_X", "X-only"),
    ("PTE_R | PTE_X", "RX"),
    ("PTE_R | PTE_W", "RW"),
    ("PTE_R", "R-only"),
)


def _perm_matrix_cases(
    sv: SvMode,
    mode_arg: str,
    upage: bool,
    fault_of: Callable[[str], int],
) -> list[SvCase]:
    cases = []
    n = 0
    for level in _levels_desc(sv):
        for perms_base, desc in _PAGE_PERMS:
            n += 1
            perms = _u(f"PTE_D | PTE_A | {perms_base} | PTE_V", upage)
            faults = fault_of(desc)
            expected = "No Fault" if faults == 0 else f"{faults} page fault(s)"
            cases.append(
                _case(
                    sv,
                    n,
                    level,
                    (
                        f"{'User' if upage else 'Supervisor'} page with {desc} permissions at level {level}:",
                        "Then, in {mode}-Mode, the page is accessed --> required: " + expected,
                    ),
                    f"{desc} page | expected = {expected}",
                    [*_walk(sv, level), _leaf(sv, perms, level)],
                    mode_arg=mode_arg,
                    faults=faults,
                )
            )
    return cases


def _t_page_perm_topics(specs: list[FileSpec]) -> None:
    s_faults = {"RWX": 0, "X-only": 2, "RX": 1, "RW": 1, "R-only": 2}.__getitem__

    # sv32-only: S pages from S-mode, U pages from U-mode
    sv32 = SVMODES["sv32"]
    specs.append(_spec(sv32, "spage", "Smode", _perm_matrix_cases(sv32, "Smode", False, s_faults), _std_macros(sv32)))
    specs.append(_spec(sv32, "upage", "Umode", _perm_matrix_cases(sv32, "Umode", True, s_faults), _std_macros(sv32)))

    # spage_access (Umode): S pages accessed from U-mode always fault.
    # sv32 runs the full permission matrix; rv64 runs RWX pages at each level.
    specs.append(
        _spec(sv32, "spage_access", "Umode", _perm_matrix_cases(sv32, "Umode", False, lambda d: 3), _std_macros(sv32))
    )
    for name in ("sv39", "sv48", "sv57"):
        sv = SVMODES[name]
        cases = []
        for n, level in enumerate(_levels_desc(sv), start=1):
            cases.append(
                _case(
                    sv,
                    n,
                    level,
                    (
                        f"Supervisor RWX page at level {level} accessed from U-Mode:",
                        (
                            "Then, in U-Mode, the page is accessed --> required:"
                            " Load-page-fault, Store-page-fault, Fetch-page-fault"
                        ),
                    ),
                    "S page | Test in U-Mode | RWX bit set | expected = RWX fault",
                    [*_walk(sv, level), _leaf(sv, "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V", level)],
                    mode_arg="Umode",
                    faults=3,
                )
            )
        specs.append(_spec(sv, "spage_access", "Umode", cases, _std_macros(sv)))

    # upage_mstatus_sum_set / sum_unset (Smode): U pages accessed from S-mode
    sum_set_faults = {"RWX": 1, "X-only": 3, "RX": 2, "RW": 1, "R-only": 2}.__getitem__
    for sv in SVMODES.values():
        run_sum = RUN_SUM_RV32 if sv.xlen == 32 else RUN_SUM_RV64
        specs.append(
            _spec(
                sv,
                "upage_mstatus_sum_set",
                "Smode",
                _perm_matrix_cases(sv, "Smode", True, sum_set_faults),
                (RWX_VERIFICATION, run_sum),
            )
        )
        specs.append(
            _spec(
                sv,
                "upage_mstatus_sum_unset",
                "Smode",
                _perm_matrix_cases(sv, "Smode", True, lambda d: 3),
                _std_macros(sv),
            )
        )

    # spage_mstatus_sum_set (Smode): S pages from S-mode with SUM set (SUM is ignored)
    spage_perms = (("PTE_X | PTE_W | PTE_R", "RWX"), ("PTE_R", "R-only"), ("PTE_X", "X-only"))
    spage_faults = {"RWX": 0, "R-only": 2, "X-only": 2}.__getitem__
    for sv in SVMODES.values():
        run_sum = RUN_SUM_RV32 if sv.xlen == 32 else RUN_SUM_RV64
        cases = []
        n = 0
        for level in _levels_desc(sv):
            for perms_base, desc in spage_perms:
                n += 1
                faults = spage_faults(desc)
                expected = "No Fault" if faults == 0 else f"{faults} page fault(s)"
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            f"Supervisor page with {desc} permissions at level {level}, mstatus.SUM set:",
                            "Then, in S-Mode, the page is accessed --> required: " + expected,
                        ),
                        f"{desc} S page, SUM set | expected = {expected}",
                        [*_walk(sv, level), _leaf(sv, f"PTE_D | PTE_A | {perms_base} | PTE_V", level)],
                        mode_arg="Smode",
                        faults=faults,
                    )
                )
        specs.append(_spec(sv, "spage_mstatus_sum_set", "Smode", cases, (RWX_VERIFICATION, run_sum)))


def _t_upage_mprv(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        runner = RUN_MPRV_RV32 if sv.xlen == 32 else RUN_MPRV_RV64
        for topic, setreq, verif, faults in (
            ("upage_mprv_set_sum_set", SETREQ_MPRV_SUM_SET, V_RWX_PHYS_FETCH, 0),
            ("upage_mprv_set_sum_unset", SETREQ_MPRV_SUM_UNSET, V_RWX_MPRV_SUM_UNSET, 2),
        ):
            sum_state = "set" if faults == 0 else "unset"
            expected = "No Fault" if faults == 0 else "Load & Store page fault"
            cases = []
            for n, level in enumerate(_levels_desc(sv), start=1):
                cases.append(
                    _case(
                        sv,
                        n,
                        level,
                        (
                            (
                                f"mstatus.MPRV set with MPP=S, mstatus.SUM {sum_state}, and a user RWX"
                                f" page at level {level}:"
                            ),
                            f"Loads and stores in M-Mode use the translated address --> required: {expected}",
                        ),
                        f"MPRV set, MPP=S, SUM {sum_state} | U page | expected = {expected}",
                        [*_walk(sv, level), _leaf(sv, "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V", level)],
                        mode_arg="Mmode",
                        faults=faults,
                    )
                )
            specs.append(_spec(sv, topic, "Smode", cases, (verif, runner, setreq)))


_VA_ONES_DATA = _t("va_ones_data")

_VA_ZEROS_DATA = _t("va_zeros_data")


def _va_all_case(
    sv: SvMode,
    n: int,
    va: str,
    label: str,
    perms: str,
    runner: str,
    sig: tuple[tuple[str, str], ...],
    banner: tuple[str, ...],
) -> SvCase:
    body = [
        f"  // Test case {n}: {'RW' if runner.endswith('RW') else 'X'} access at the VA extreme",
        *_walk(sv, 0, va=va),
        _leaf(sv, perms, 0, va=va, label=label),
        "  sfence.vma",
        "",
        f"  {runner} Smode, {va}, LEVEL0, test{n}",
    ]
    return SvCase(banner=banner, body=tuple(body), sig_strs=sig, faults=0, level=0)


def _t_va_all(specs: list[FileSpec]) -> None:
    for sv in SVMODES.values():
        all_f = "0x" + "f" * (sv.xlen // 4)
        all_fc = all_f[:-1] + "c"
        zeros = "0x" + "0" * (sv.xlen // 4)
        sig_init = (
            "  LI( a2, 0x800)              // Test signature initialization"
            if sv.xlen == 32
            else "  li a2, 0x12                 // Test signature initialization"
        )
        # VA all ones
        cases = [
            _va_all_case(
                sv,
                1,
                "va_data_rw",
                "rvtest_data_1_l0_rw",
                "PTE_D | PTE_A | PTE_W | PTE_R | PTE_V",
                "TEST_CASES_RUNNER_RW",
                _sig2("test1"),
                ("Store and load a byte at the all-ones virtual address:", "Expected: No Fault"),
            ),
            _va_all_case(
                sv,
                2,
                "va_data_x",
                "rvtest_data_1_l0_x",
                "PTE_D | PTE_A | PTE_X | PTE_V",
                "TEST_CASES_RUNNER_X",
                (_sig3("test2")[2],),
                ("Execute at the top of the virtual address space:", "Expected: No Fault"),
            ),
        ]
        specs.append(
            _spec(
                sv,
                "VA_all_ones",
                "Smode",
                cases,
                (RUNNER_RW_BYTE, RUNNER_X_ONLY),
                sig_init=sig_init,
                va_defs=(("va_data_rw", all_f), ("va_data_x", all_fc)),
                data_region_body=_VA_ONES_DATA,
            )
        )
        # VA all zeros
        rw_runner = RUNNER_RW_WORD if sv.name in ("sv32", "sv39") else RUNNER_RW_BYTE
        cases = [
            _va_all_case(
                sv,
                1,
                "va_data",
                "rvtest_data_1_l0_rw",
                "PTE_D | PTE_A | PTE_W | PTE_R | PTE_V",
                "TEST_CASES_RUNNER_RW",
                _sig2("test1"),
                ("Store and load at virtual address zero:", "Expected: No Fault"),
            ),
            _va_all_case(
                sv,
                2,
                "va_data",
                "rvtest_data_1_l0_x",
                "PTE_D | PTE_A | PTE_X | PTE_V",
                "TEST_CASES_RUNNER_X",
                (_sig3("test2")[2],),
                ("Execute at virtual address zero:", "Expected: No Fault"),
            ),
        ]
        specs.append(
            _spec(
                sv,
                "VA_all_zeros",
                "Smode",
                cases,
                (rw_runner, RUNNER_X_ONLY),
                sig_init=sig_init,
                va_defs=(("va_data", zeros),),
                data_region_body=_VA_ZEROS_DATA,
            )
        )


# ----------------------------------------------------------------------------------
# Bespoke body-template files: satp access and mstatus.TVM
# ----------------------------------------------------------------------------------

_SATP_ACCESS_FULL = _t("satp_access_full")

_SATP_MSU_CASES = _t("satp_msu_cases")

_SATP_BANNER = """\
//  1. Accessing satp in M mode -> Successful
//  2. Accessing satp in S mode -> Successful
//  3. Accessing satp in U mode -> 3 Illegal Instruction exceptions
//  4. Set satp.MODE to {Svn} -> Successful
//  5. All zeros, ones and walking ones on the PPN field of satp when satp.MODE={Svn} -> Successful
//  6. All zeros, ones and walking ones on the ASID field of satp when satp.MODE={Svn} -> Successful
//
// Total Expected Faults :: 3"""

_SATP_BANNER_SHORT = """\
//  1. Set satp.MODE to {Svn} -> Successful
//  2. All zeros, ones and walking ones on the PPN field of satp when satp.MODE={Svn} -> Successful
//  3. All zeros, ones and walking ones on the ASID field of satp when satp.MODE={Svn} -> Successful
//
// Total Expected Faults :: 0"""

_SATP_ACCESS_SHORT = _t("satp_access_short")


def _t_satp_access(specs: list[FileSpec]) -> None:
    params = {
        "sv32": {"shift": 31, "asid_ones": "0x1FF", "asid_shift": 22, "asid_bits": 9, "sigupd": 55, "trap": 30},
        "sv39": {"shift": 60, "asid_ones": "0xFFFF", "asid_shift": 44, "asid_bits": 16, "sigupd": 80, "trap": 30},
        "sv48": {"shift": 60, "asid_ones": "0xFFFF", "asid_shift": 44, "asid_bits": 16, "sigupd": 70, "trap": 10},
        "sv57": {"shift": 60, "asid_ones": "0xFFFF", "asid_shift": 44, "asid_bits": 16, "sigupd": 70, "trap": 10},
    }
    for name, p in params.items():
        sv = SVMODES[name]
        template = _SATP_ACCESS_FULL if name in ("sv32", "sv39") else _SATP_ACCESS_SHORT
        body = template.format(
            access_cases=_SATP_MSU_CASES.format(HR=HR) if name in ("sv32", "sv39") else "",
            HR=HR,
            Svn=sv.ext,
            SVN=sv.suffix,
            svn=sv.name,
            shift=p["shift"],
            asid_ones=p["asid_ones"],
            asid_shift=p["asid_shift"],
            asid_bits=p["asid_bits"],
        )
        # Escape literal braces are already resolved; render_file .format(mode=...) must not
        # re-interpret anything, so double any remaining braces (there are none by design).
        specs.append(
            FileSpec(
                filename=f"{sv.name}_satp_access_test.S",
                required_extensions=("I", sv.ext),
                march=sv.march,
                svmode=sv,
                priv_mode="Smode",
                banner_prefix=_prefix(sv, "satp_access_test"),
                banner_body=(_SATP_BANNER if name in ("sv32", "sv39") else _SATP_BANNER_SHORT).replace("{Svn}", sv.ext),
                body_template=body.replace("{", "{{").replace("}", "}}"),
                sigupd_override=p["sigupd"],
                trap_override=p["trap"],
            )
        )


_TVM_BODY = _t("tvm_body")

_TVM_BANNER = """\
// This test verifies the functionality of mstatus.TVM bit with the satp and sfence.vma
// Test cases are as follows:
//  1. satp accessed in M-Mode with mstatus.TVM set -> Successful
//  2. sfence.vma accessed in M-Mode with mstatus.TVM set -> Successful
//  3. satp accessed in S-Mode with mstatus.TVM set -> 3 Illegal instruction exceptions
//  4. sfence.vma accessed in S-Mode with mstatus.TVM set -> Illegal instruction exception
//
// Total Expected Faults :: 4"""


def _t_mstatus_tvm(specs: list[FileSpec]) -> None:
    body = _TVM_BODY.format(HR=HR)
    specs.append(
        FileSpec(
            filename="sv_mstatus_tvm_test.S",
            required_extensions=("I", "S"),
            march="rv${XLEN}i_zicsr_zifencei",
            svmode=SVMODES["sv39"],  # unused by the template path beyond xlen-independent fields
            priv_mode="Smode",
            banner_prefix=_ATTR,
            banner_body=_TVM_BANNER,
            body_template=body.replace("{", "{{").replace("}", "}}"),
            sigupd_override=10,
            trap_override=30,
            extra_defines=("#define BOOT_TO_MMODE",),
        )
    )


# ----------------------------------------------------------------------------------
# Suite assembly
# ----------------------------------------------------------------------------------


@add_sv_suite("Sv")
def sv_files() -> list[FileSpec]:
    """All 134 files of the Sv suite."""
    specs: list[FileSpec] = []
    _t_invalid_pte(specs)
    _t_canonical(specs)
    _t_global_pte(specs)
    _t_misaligned_page(specs)
    _t_mstatus_mprv(specs)
    _t_mstatus_mxr(specs)
    _t_mstatus_sbe(specs)
    _t_nleaf_pte_dau(specs)
    _t_nleaf_pte_level0(specs)
    _t_pte_reserved_rwx(specs)
    _t_pte_rsw(specs)
    _t_pte_reserved_field(specs)
    _t_svpbmt_disabled(specs)
    _t_svnapot_not_supported(specs)
    _t_page_perm_topics(specs)
    _t_upage_mprv(specs)
    _t_va_all(specs)
    _t_satp_access(specs)
    _t_mstatus_tvm(specs)
    return specs
