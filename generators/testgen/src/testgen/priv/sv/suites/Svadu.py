##################################
# priv/sv/suites/Svadu.py
#
# Svadu suite: hardware A/D-bit updates with menvcfg.ADUE set.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svadu suite table: hardware A/D updates observed via separate W/R/X pages."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode
from testgen.priv.sv.suites.Sv import _spec

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

# Per-svmode virtual addresses: one W/R/X triple per level
_VAS = {
    "sv32": {
        1: ("0x00400000", "0x00800000", "0x00C00000"),
        0: ("0x01001000", "0x01002000", "0x01003000"),
    },
    "sv39": {
        2: ("0x040000000", "0x080000000", "0x0C0000000"),
        1: ("0x000200000", "0x000400000", "0x000600000"),
        0: ("0x000001000", "0x000002000", "0x000003000"),
    },
    "sv48": {
        3: ("0x008080000000", "0x010080000000", "0x018080000000"),
        2: ("0x028040000000", "0x028080000000", "0x0280C0000000"),
        1: ("0x028000200000", "0x028000400000", "0x028000600000"),
        0: ("0x028000001000", "0x028000002000", "0x028000003000"),
    },
    "sv57": {
        4: ("0x01000000000000", "0x02000000000000", "0x03000000000000"),
        3: ("0x04008000000000", "0x04010000000000", "0x04018000000000"),
        2: ("0x04020040000000", "0x04020080000000", "0x040200C0000000"),
        1: ("0x04020300200000", "0x04020300400000", "0x04020300600000"),
        0: ("0x04020300801000", "0x04020300802000", "0x04020300803000"),
    },
}

_CODE_VA = {"sv32": "0x90000000", "sv39": "0x180000000", "sv48": "0x030080000000", "sv57": "0x05000080000000"}

# The rv64 runners differ only in the readback .if chain (and one register quirk in sv39 U-mode)
_RUNNER_HEAD_RV64 = _t("adu_runner_head_rv64")

V_ADU = _t("v_adu")

RUNNER_ADU_RV32 = _t("adu_runner_rv32")


def _readback_chain(sv: SvMode) -> str:
    lines = []
    for level in range(sv.levels - 1, -1, -1):
        kw = ".if" if level == sv.levels - 1 else ".elseif"
        table = "rvtest_Sroot_pg_tbl" if level == sv.levels - 1 else f"rvtest_slvl{level}_pg_tbl"
        lines.append(f"  {kw} \\level == LEVEL{level}")
        lines.append(f"      LA(a0, {table})")
    lines.append("  .endif")
    return "\n".join(lines)


def _runner_rv64(sv: SvMode, mode: str) -> str:
    # The hand-written sv39 U-mode file uses a4 as the scratch register; everything else uses t0
    reg = "a4" if (sv.name == "sv39" and mode == "Umode") else "t0"
    return _RUNNER_HEAD_RV64.format(reg=reg, readback=_readback_chain(sv))


def _sig6(n: int) -> tuple[tuple[str, str], ...]:
    sig = [
        (f"test{n}_{op}", f"Mismatch during {insn} in Test Case {n}!")
        for op, insn in (("store", "sw"), ("load", "lw"), ("exec", "jalr"))
    ]
    sig += [
        (f"test{n}_read_{op}_pte", f"Mismatch in PTE used during {insn} in Test Case {n}!")
        for op, insn in (("store", "sw"), ("load", "lw"), ("exec", "jalr"))
    ]
    return tuple(sig)


@add_sv_suite("Svadu")
def svadu_files() -> list[FileSpec]:
    """Svadu: A/D combinations on separate W/R/X pages with hardware updates enabled."""
    specs: list[FileSpec] = []
    for name, va_table in _VAS.items():
        sv = SVMODES[name]
        csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
        setup = (f"  LI(t0, {mask})", f"  csrs {csr}, t0")
        va_defs = tuple(
            (f"va_data_l{level}_{sfx}", va)
            for level in sorted(va_table, reverse=True)
            for sfx, va in zip(("w", "r", "x"), va_table[level], strict=True)
        )
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            u = "PTE_U | " if umode else ""
            runner = RUNNER_ADU_RV32 if sv.xlen == 32 else _runner_rv64(sv, mode)
            cases: list[SvCase] = []
            n = 0
            for level in sorted(va_table, reverse=True):
                va_w, va_r, va_x = (f"va_data_l{level}_{sfx}" for sfx in ("w", "r", "x"))
                for bits, desc in (
                    ("PTE_D | ", "PTE.D set, PTE.A unset"),
                    ("PTE_A | ", "PTE.A set, PTE.D unset"),
                    ("", "PTE.D and PTE.A unset"),
                ):
                    n += 1
                    perms = f"{bits}{u}PTE_X | PTE_W | PTE_R | PTE_V"
                    macro = "SUPERPAGE_PTE_SETUP" if level > 0 else "PTE_SETUP"
                    walk = []
                    for j in range(sv.levels - 2, level - 1, -1):
                        walk.append(f"  PTE_SETUP_{sv.suffix}(rvtest_slvl{j}_pg_tbl, (PTE_V), {va_w}, LEVEL{j + 1})")
                    body = [
                        f"  // Test case {n}: {desc} at level {level} | hardware update expected",
                        *walk,
                        f"  {macro}_{sv.suffix}(rvtest_data_1, ({perms}), {va_w}, LEVEL{level})",
                        f"  {macro}_{sv.suffix}(rvtest_data_1, ({perms}), {va_r}, LEVEL{level})",
                        f"  {macro}_{sv.suffix}(rvtest_data_1, ({perms}), {va_x}, LEVEL{level})",
                        "  sfence.vma",
                        "",
                        f"  TEST_CASES_RUNNER {mode}, {va_w}, {va_r}, {va_x}, LEVEL{level}, test{n}",
                    ]
                    cases.append(
                        SvCase(
                            banner=(
                                f"{desc} on separate W/R/X pages at level {level}:",
                                (
                                    "Then, in {mode}-Mode, the pages are accessed and the PTEs read back"
                                    " --> required: hardware sets A/D, no fault"
                                ),
                            ),
                            body=tuple(body),
                            sig_strs=_sig6(n),
                            faults=0,
                            level=level,
                        )
                    )
            specs.append(
                _spec(
                    sv,
                    "Svadu",
                    mode,
                    cases,
                    (V_ADU, runner),
                    extra_ext=("Svadu",),
                    banner=_ATTR,
                    setup_asm=setup,
                    va_defs=va_defs,
                    va_code_override=_CODE_VA[name],
                    emit_trap_count=False,
                )
            )
    return specs
