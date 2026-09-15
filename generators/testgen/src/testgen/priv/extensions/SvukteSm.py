##################################
# priv/extensions/SvukteSm.py
#
# SvukteSm test generator: Svukte qualification of M-mode accesses via mstatus.MPRV.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvukteSm - Uses mstatus.MPRV and mstatus.MPP to check that accesses with an effective privilege mode of user
from machine mode are still Svukte-qualified.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SvukteCommon import (
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
    init_store_value,
    mode_guarded,
    release_regs,
    rv64_only,
    s_stage_pte,
    set_csr_bits,
    set_ukte,
    target_va,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "SvukteSm_cg"

# mstatus.MPRV makes M-mode loads and stores translate and check permissions as though
# the current privilege mode were mstatus.MPP, so MPP=U gives them effective privilege U.
#
# Only the UKTE-set case faults, so only it can close the qualified bins. The UKTE-clear
# case is the baseline it is contrasted against: the covergroup has no ukte_not_set
# coverpoint, so cp_baseline_mprv_ukte_clear deliberately has no cross and exists to keep
# the testcase labels honest about which bin each case closes.
_MPRV_COVERPOINTS = {
    True: {
        "store": "cp_svukte_qualified_mprv_write_fault",
        "load": "cp_svukte_qualified_mprv_read_fault",
    },
    False: {
        "store": "cp_baseline_mprv_ukte_clear",
        "load": "cp_baseline_mprv_ukte_clear",
    },
}


def _set_mprv_umode(regs: SvukteRegs) -> list[str]:
    """Set mstatus.MPRV and clear mstatus.MPP, giving M-mode accesses effective privilege U.

    This has to be re-applied before every access under test: a trap taken to M-mode
    overwrites mstatus.MPP with the interrupted privilege mode, so the pair does not
    survive a faulting access.
    """
    return [
        *set_csr_bits("mstatus", "MSTATUS_MPRV", regs.scratch, set_bits=True),
        *set_csr_bits("mstatus", "MSTATUS_MPP", regs.scratch, set_bits=False),
    ]


def _clear_mprv(regs: SvukteRegs) -> list[str]:
    """Clear mstatus.MPRV so the signature stores are not themselves Svukte-qualified."""
    return set_csr_bits("mstatus", "MSTATUS_MPRV", regs.scratch, set_bits=False)


def _mprv_case(test_data: TestData, mode: SvMode, regs: SvukteRegs, *, ukte: bool) -> list[str]:
    """Emit one case: stay in M-mode, but give each access an effective privilege of U."""
    bin_prefix = f"{mode.name}_ukte_{'set' if ukte else 'clear'}_mprv"
    lines = [
        "",
        f"# {bin_prefix}: senvcfg.UKTE {'set' if ukte else 'clear'}, effective privilege U via MPRV",
        *set_ukte(regs, qualified=ukte),
        *target_va(mode, mode.va_data, regs),
        *bump_store_value(regs),
    ]

    results: list[tuple[str, int]] = []
    for kind, coverpoint in _MPRV_COVERPOINTS[ukte].items():
        lines.extend(_set_mprv_umode(regs))
        asm, label, check_reg = access_test(
            test_data,
            regs,
            covergroup=covergroup,
            coverpoint=coverpoint,
            bin_name=f"{bin_prefix}_{kind}",
            kind=kind,
        )
        lines.extend(asm)
        results.append((label, check_reg))

    lines.extend(_clear_mprv(regs))
    lines.extend(deferred_sigupds(test_data, results))
    return lines


def _mode_block(test_data: TestData, mode: SvMode, regs: SvukteRegs) -> list[str]:
    """Emit both MPRV cases for one translation mode."""
    lines = [
        f"# ---- {mode.name}: M-mode accesses with effective privilege U (mstatus.MPRV) ----",
        f"SATP_SETUP_RV64({mode.name})",
        "sfence.vma",
        "# Permissive RWXU leaf PTE, so any fault below is attributable only to Svukte.",
        *s_stage_pte(mode, "rvtest_data_1", PTE_USER_RWX, mode.va_data),
    ]
    for ukte in (False, True):
        lines.extend(_mprv_case(test_data, mode, regs, ukte=ukte))
    lines.extend(["", *disable_translation()])
    return mode_guarded(mode, lines)


@add_priv_test_generator(
    "SvukteSm",
    required_extensions=["Svukte", "Sm"],
    march_extensions=["S"],
)
def make_svuktesm(test_data: TestData) -> list[TestChunk]:
    """Generate the SvukteSm machine-mode tests for every supported RV64 translation mode."""
    tc = test_data.begin_test_chunk()
    regs = allocate_regs(test_data)

    body = [*data_payload(regs), *init_store_value(regs)]
    for mode in SV_MODES:
        body.extend(["", *_mode_block(test_data, mode, regs)])

    tc.code.append(comment_banner("SvukteSm", make_svuktesm.__doc__))
    tc.code.extend(rv64_only(body))

    release_regs(test_data, regs)
    return [test_data.end_test_chunk()]
