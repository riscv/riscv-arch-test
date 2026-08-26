##################################
# priv/sv/suites/Svbare.py
#
# Svbare suite: accesses with translation disabled (satp.MODE = Bare).
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svbare suite: three verbatim body-template files (Bare mode, plus MPRV in Bare)."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"


def _bare_spec(filename: str, banner_body: str, body: str, sigupd: int, trap: int, *, boot_m: bool = False) -> FileSpec:
    return FileSpec(
        filename=filename,
        required_extensions=("I", "S"),
        march="rv${XLEN}i_zicsr_zifencei",
        svmode=SVMODES["sv39"],  # xlen-agnostic file; the template uses no svmode fields
        priv_mode="Smode",
        banner_prefix=_ATTR,
        banner_body=banner_body,
        body_template=body.replace("{", "{{").replace("}", "}}"),
        sigupd_override=sigupd,
        trap_override=trap,
        extra_defines=("#define BOOT_TO_MMODE",) if boot_m else (),
    )


@add_sv_suite("Svbare")
def svbare_files() -> list[FileSpec]:
    """Svbare: Bare-mode RWX accesses from S and U mode, and under mstatus.MPRV."""
    specs = []
    for mode in ("S", "U"):
        banner = f"""\
// 1. Disable virtualization (satp.MODE = Bare)
//        Then, in {mode}-Mode, Load, Store & Execute --> required: No Fault
//
// Total Expected Faults :: 0"""
        specs.append(
            _bare_spec(f"Svbare_{mode}mode.S", banner, _t("svbare_mode_body").replace("MODEWORD", mode), 10, 10)
        )
    banner = """\
// 1. mstatus.MPRV set, mstatus.MPP = S-mode and virtualization is disabled (satp.MODE = Bare):
// 2. mstatus.MPRV set, mstatus.MPP = U-mode and virtualization is disabled (satp.MODE = Bare):
//
// Total Expected Faults :: 0"""
    specs.append(_bare_spec("Svbare_mstatus_mprv.S", banner, _t("svbare_mprv_body"), 15, 10, boot_m=True))
    return specs
