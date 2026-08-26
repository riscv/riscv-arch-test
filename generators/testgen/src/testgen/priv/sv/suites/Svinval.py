##################################
# priv/sv/suites/Svinval.py
#
# Svinval suite: fine-grained TLB invalidation instructions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Svinval suite: two verbatim body-template files (per-mode legality, and TVM)."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv.macros import template as _t
from testgen.priv.sv.model import SVMODES, FileSpec

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"


def _inval_spec(
    filename: str, ext: tuple[str, ...], banner_body: str, body: str, trap: int, *, boot_m: bool
) -> FileSpec:
    return FileSpec(
        filename=filename,
        required_extensions=ext,
        march="rv${XLEN}i_zicsr_zifencei_svinval",
        svmode=SVMODES["sv39"],  # xlen-agnostic file; the template uses no svmode fields
        priv_mode="Smode",
        banner_prefix=_ATTR,
        banner_body=banner_body,
        body_template=body.replace("{", "{{").replace("}", "}}"),
        sigupd_override=10,
        trap_override=trap,
        extra_defines=("#define BOOT_TO_MMODE",) if boot_m else (),
    )


@add_sv_suite("Svinval")
def svinval_files() -> list[FileSpec]:
    """Svinval: instruction legality per privilege mode, and interaction with mstatus.TVM."""
    banner_main = """\
// 1. Execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in S-Mode.
//        Expected: No fault
// 2. Execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in U-Mode.
//        Expected: 4 Illegal instruction exceptions
//
// Total Expected Faults :: 4"""
    banner_tvm = """\
// 1. mstatus.TVM=0, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in M-Mode.
//        Expected: No fault
// 2. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in M-Mode.
//        Expected: No fault
// 3. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in S-Mode.
//        Expected: 2 Illegal instruction exceptions
// 4. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in U-Mode.
//        Expected: 4 Illegal instruction exceptions
//
// Total Expected Faults :: 6"""
    return [
        _inval_spec("Svinval.S", ("S", "Svinval"), banner_main, _t("svinval_body"), 30, boot_m=False),
        _inval_spec(
            "Svinval_mstatus_tvm.S", ("Sm", "S", "Svinval"), banner_tvm, _t("svinval_tvm_body"), 50, boot_m=True
        ),
    ]
