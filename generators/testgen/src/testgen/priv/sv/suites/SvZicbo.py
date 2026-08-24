##################################
# priv/sv/suites/SvZicbo.py
#
# SvZicbo suite: cache-block operations under virtual memory.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvZicbo suite table: cbo.clean/flush/inval, cbo.zero, and prefetch under VM.

The zicbom/zicboz "exceptions" files repeat one permission matrix at every page
level; the matrix is identical across levels except that the deepest level adds
a pointer-encoding case and an extra access-fault flavor, non-top levels add a
walk-corruption access fault and a guarded D/A/U non-leaf trio, and only levels
above 0 include the misaligned-superpage case.
"""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode
from testgen.priv.sv.suites.Sv import _spec

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

# ------------------------------- verbatim macros -------------------------------

V_CBOM = _t("v_cbom")

V_CBOZ = _t("v_cboz")

V_PREFETCH = _t("v_prefetch")

_VA_MATH_RV64 = _t("va_math_rv64")

_PA_MATH_RV64 = _t("pa_math_rv64")

_VA_MATH_RV32 = _t("va_math_rv32")

_PA_MATH_RV32 = _t("pa_math_rv32")

_SIG_CBOM = _t("sig_cbom")

_SIG_CBOZ = _t("sig_cboz")

_BODY = _t("cbo_body")

_BODY_NOARG = _t("cbo_body_noarg")


def _runner(name: str, args: str, math: str, sig: str, body: str = _BODY) -> str:
    math_body = math.strip("\n")
    tail = f"\n{sig.rstrip()}\n.endm\n" if sig else "\n\n.endm\n"
    return f"\n.macro {name} {args}\n{math_body}\n{body.rstrip()}{tail}"


def _macros(sv: SvMode, family: str) -> tuple[str, ...]:
    rv32 = sv.xlen == 32
    va_math, pa_math = (_VA_MATH_RV32, _PA_MATH_RV32) if rv32 else (_VA_MATH_RV64, _PA_MATH_RV64)
    if family == "zicbop":
        return (V_PREFETCH, _runner("TEST_CASES_RUNNER", "LOWER_MODE, VA, level", va_math, "", _BODY_NOARG))
    verif = V_CBOM if family == "zicbom" else V_CBOZ
    sig = _SIG_CBOM if family == "zicbom" else _SIG_CBOZ
    return (
        verif,
        _runner("TEST_CASES_RUNNER", "LOWER_MODE, VA, level, TEST_CASE", va_math, sig),
        _runner("TEST_CASES_RUNNER_2", "LOWER_MODE, PA, VA, level, TEST_CASE", pa_math, sig),
    )


# ------------------------------- case matrix -------------------------------


def _sig(family: str, n: int) -> tuple[tuple[str, str], ...]:
    if family == "zicboz":
        return ((f"test{n}", f"Mismatch during cbo.zero in Test Case {n}!"),)
    return tuple((f"test{n}_{op}", f"Mismatch during cbo.{op} in Test Case {n}!") for op in ("clean", "flush", "inval"))


class _Group:
    """Builds the per-level case group for one exceptions file."""

    def __init__(self, sv: SvMode, mode: str, family: str) -> None:
        self.sv = sv
        self.mode = mode
        self.family = family
        self.umode = mode == "Umode"
        self.u = "PTE_U | " if self.umode else ""
        self.cases: list[SvCase] = []
        self.n = 0

    def _walk(self, level: int, override: dict[int, str] | None = None) -> list[str]:
        lines = []
        for j in range(self.sv.levels - 2, level - 1, -1):
            entry = (override or {}).get(j + 1)
            if entry is not None and entry.startswith("@"):  # replace the table address
                lines.append(f"  PTE_SETUP_{self.sv.suffix}({entry[1:]}, (PTE_V), va_data, LEVEL{j + 1})")
            else:
                perms = entry or "PTE_V"
                lines.append(f"  PTE_SETUP_{self.sv.suffix}(rvtest_slvl{j}_pg_tbl, ({perms}), va_data, LEVEL{j + 1})")
        return lines

    def _leaf(self, perms: str, level: int, label: str = "rvtest_data_1", superpage: bool = True) -> str:
        macro = "SUPERPAGE_PTE_SETUP" if (superpage and level > 0) else "PTE_SETUP"
        return f"  {macro}_{self.sv.suffix}({label}, ({perms}), va_data, LEVEL{level})"

    def add(
        self,
        level: int,
        desc: str,
        expected: str,
        faults: int,
        pte_lines: list[str],
        *,
        runner: str = "TEST_CASES_RUNNER",
        pa: str | None = None,
        pre: tuple[str, ...] = (),
        post: tuple[str, ...] = (),
        guard: str | None = None,
        guard_open: bool = False,
        guard_close: bool = False,
    ) -> None:
        self.n += 1
        n = self.n
        body: list[str] = []
        if guard and guard_open:
            body.append(f"#ifdef {guard}")
        args = f"{self.mode}, {pa}, va_data" if pa is not None else f"{self.mode}, va_data"
        body += [
            f"  // Test case {n}: {desc} | Test in {self.mode[0]}-Mode | expected = {expected}",
            *pte_lines,
            "  sfence.vma",
            *pre,
            "",
            f"  {runner} {args}, LEVEL{level}, test{n}",
            *post,
        ]
        if guard and guard_close:
            body.append("#endif")
        self.cases.append(
            SvCase(
                banner=(f"{desc} at level {level}:", "Expected: " + expected),
                body=tuple(body),
                sig_strs=_sig(self.family, n),
                faults=faults,
                level=level,
            )
        )

    def level_group(self, level: int) -> None:
        sv, u, umode = self.sv, self.u, self.umode
        top = level == sv.levels - 1
        l0 = level == 0
        walk = self._walk(level)
        nfaults = 3 if self.family == "zicbom" else 1

        def std(perms: str, desc: str, expected: str, faults: int, **kw: object) -> None:
            self.add(level, desc, expected, faults, [*walk, self._leaf(perms, level)], **kw)  # type: ignore[arg-type]

        std(f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R", "PTE.V unset", "Store page fault", nfaults)
        std(
            f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_V",
            "Reserved W+X without R",
            "Store page fault",
            nfaults,
            guard="S1P12P0_OR_LATER_SUPPORTED",
            guard_open=True,
        )
        std(
            f"PTE_D | PTE_A | {u}PTE_W | PTE_V",
            "Reserved W without R",
            "Store page fault",
            nfaults,
            guard="S1P12P0_OR_LATER_SUPPORTED",
            guard_close=True,
        )
        std(f"PTE_D | PTE_A | {u}PTE_X | PTE_R | PTE_V", "RX permissions", "Store page fault", nfaults)
        if not umode:
            std(
                "PTE_D | PTE_A | PTE_X | PTE_R | PTE_V",
                "RX permissions with mstatus.SUM set",
                "Store page fault",
                nfaults,
                pre=("  LI(t0, MSTATUS_SUM)", "  csrs mstatus, t0"),
                post=("  LI(t0, MSTATUS_SUM)", "  csrc mstatus, t0"),
            )
            std(
                "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V",
                "User page from S-Mode",
                "Store page fault",
                nfaults,
            )
        else:
            std(
                "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V",
                "Supervisor page from U-Mode",
                "Store page fault",
                nfaults,
            )
            if self.family == "zicbom":
                std("PTE_D | PTE_A | PTE_U | PTE_X | PTE_V", "Execute-only page", "Store page fault", nfaults)
        if self.family == "zicbom" and not umode:
            std("PTE_D | PTE_A | PTE_X | PTE_V", "Execute-only page", "Store page fault", nfaults)
        std(f"PTE_D | {u}PTE_X | PTE_W | PTE_R | PTE_V", "PTE.A unset", "Store page fault", nfaults)
        std(f"PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V", "PTE.D unset", "No fault", 0)
        if not l0:
            self.add(
                level,
                "Misaligned superpage",
                "Store page fault",
                nfaults,
                [*walk, self._leaf(f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V", level, superpage=False)],
                runner="TEST_CASES_RUNNER_2",
                pa="0x0",
            )
        if l0:
            self.add(
                level,
                "Pointer encoding (V only) in the leaf",
                "Store page fault",
                nfaults,
                [*walk, self._leaf(f"{u}PTE_V", level)],
            )
        if not top and not l0:
            self.add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                nfaults,
                [
                    *self._walk(level, {level + 1: "@RVMODEL_ACCESS_FAULT_ADDRESS"}),
                    self._leaf(f"PTE_A | PTE_D | {u}PTE_X | PTE_W | PTE_R | PTE_V", level),
                ],
                guard="RVMODEL_ACCESS_FAULT_ADDRESS",
                guard_open=True,
                guard_close=True,
            )
        if l0 and sv.levels > 1:
            self.add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                nfaults,
                [
                    *self._walk(level, {1: "@RVMODEL_ACCESS_FAULT_ADDRESS"}),
                    self._leaf(f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V", level),
                ],
                runner="TEST_CASES_RUNNER_2",
                pa="RVMODEL_ACCESS_FAULT_ADDRESS",
                guard="RVMODEL_ACCESS_FAULT_ADDRESS",
                guard_open=True,
                guard_close=True,
            )
        self.add(
            level,
            "Leaf PTE points to the access-fault region",
            "Store access fault",
            nfaults,
            [
                *walk,
                self._leaf(
                    f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V", level, label="RVMODEL_ACCESS_FAULT_ADDRESS"
                ),
            ],
            runner="TEST_CASES_RUNNER_2",
            pa="RVMODEL_ACCESS_FAULT_ADDRESS",
            guard="RVMODEL_ACCESS_FAULT_ADDRESS",
            guard_open=True,
            guard_close=True,
        )
        if not top:
            for i, bit in enumerate(("PTE_D", "PTE_A", "PTE_U")):
                # NOTE: the hand-written files place the A-bit case's leaf at LEVEL0
                if bit == "PTE_A" and level > 0:
                    leaf = (
                        f"  SUPERPAGE_PTE_SETUP_{sv.suffix}(rvtest_data_1,"
                        f" (PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)"
                    )
                else:
                    leaf = self._leaf(f"PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V", level)
                self.add(
                    level,
                    f"Non-leaf PTE with {bit.removeprefix('PTE_')} bit set",
                    "Store page fault",
                    nfaults,
                    [
                        *self._walk(level, {level + 1: f"{bit} | PTE_V"}),
                        leaf,
                    ],
                    guard="S1P12P0_OR_LATER_SUPPORTED",
                    guard_open=(i == 0),
                    guard_close=(i == 2),
                )


def _exceptions_file(sv: SvMode, mode: str, family: str) -> FileSpec:
    grp = _Group(sv, mode, family)
    for level in range(sv.levels - 1, -1, -1):
        grp.level_group(level)
    ext = "Zicbom" if family == "zicbom" else "Zicboz"
    envmask = "MENVCFG_CBCFE | MENVCFG_CBIE" if family == "zicbom" else "MENVCFG_CBZE"
    setup = [f"  LI(t0, {envmask})", "  csrs menvcfg, t0"]
    if mode == "Umode":
        setup.append("  csrs senvcfg, t0")
    return _spec(
        sv,
        f"{family}_exceptions",
        mode,
        grp.cases,
        _macros(sv, family),
        extra_ext=(ext,),
        banner=_ATTR,
        march=f"{sv.march}_{family[:6]}",
        setup_asm=tuple(setup),
        emit_trap_count=False,
    )


def _prefetch_file(sv: SvMode, mode: str) -> FileSpec:
    umode = mode == "Umode"
    u = "PTE_U | " if umode else ""
    cases = []
    for level in range(sv.levels - 1, -1, -1):
        walk = [
            f"  PTE_SETUP_{sv.suffix}(rvtest_slvl{j}_pg_tbl, (PTE_V), va_data, LEVEL{j + 1})"
            for j in range(sv.levels - 2, level - 1, -1)
        ]
        macro = "SUPERPAGE_PTE_SETUP" if level > 0 else "PTE_SETUP"
        cases.append(
            SvCase(
                banner=(
                    f"Prefetch instructions on an RWX page at level {level}:",
                    "Expected: No fault (prefetches never trap)",
                ),
                body=(
                    f"  // Prefetch at level {level} | Test in {mode[0]}-Mode | expected = No fault",
                    *walk,
                    (
                        f"  {macro}_{sv.suffix}(rvtest_data_1, (PTE_D | PTE_A | {u}PTE_X | PTE_W | PTE_R | PTE_V),"
                        f" va_data, LEVEL{level})"
                    ),
                    "  sfence.vma",
                    "",
                    f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}",
                ),
                sig_strs=(),
                faults=0,
                level=level,
            )
        )
    return _spec(
        sv,
        "zicbop",
        mode,
        cases,
        _macros(sv, "zicbop"),
        extra_ext=("Zicbop",),
        banner=_ATTR,
        march=f"{sv.march}_zicbop",
        sig_init="",
    )


@add_sv_suite("SvZicbo")
def svzicbo_files() -> list[FileSpec]:
    """SvZicbo: cbo.clean/flush/inval, cbo.zero, and prefetch exceptions under VM."""
    specs: list[FileSpec] = []
    for name in ("sv32", "sv39", "sv48", "sv57"):
        sv = SVMODES[name]
        for mode in ("Smode", "Umode"):
            specs.append(_exceptions_file(sv, mode, "zicbom"))
            specs.append(_exceptions_file(sv, mode, "zicboz"))
            specs.append(_prefetch_file(sv, mode))
    return specs
