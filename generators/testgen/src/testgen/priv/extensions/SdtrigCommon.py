##################################
# SdtrigCommon.py
#
# Sdtrig (debug triggers) shared test-case generators.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sdtrig debug-trigger test-case generators."""

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import add_tsbi
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# data
PERM_XSL = ("exec", "store", "load")
SIZE_ALL = ("any", "b8", "b16", "b32", "b48", "b64", "b128")
SIZE_SEW = ("any", "s8", "s16", "s32", "s64", "s128")


def add_tc(test_data: TestData, mode: str, binname: str, coverpoint: str, covergroup: str) -> str:
    """Register a testcase with its mode ("Sm"/"S"/"U") prefixed onto the bin name."""
    return test_data.add_testcase(f"{mode}_{binname}", coverpoint, covergroup)


def _tsbi_csr(op: str, csr: str, val: str) -> list[str]:
    """Run one CSR op on a trigger CSR in M-mode via the framework T-SBI.
    Args:
        op:  "read" | "write" | "set" | "clear"
        csr: trigger-CSR name (tdata1/2/3, tinfo, tcontrol, scontext, mcontext, hcontext)
        val: register string ("x5", "x0") — destination for "read", source for write/set/clear
    """
    a0, a1, x0 = 10, 11, 0
    csrrw, csrrs, csrrc = 0b001, 0b010, 0b011
    csr_addr = {
        "tdata1": 0x7A1,
        "tdata2": 0x7A2,
        "tdata3": 0x7A3,
        "tinfo": 0x7A4,
        "tcontrol": 0x7A5,
        "scontext": 0x5A8,
        "mcontext": 0x7A8,
        "hcontext": 0x6A8,
        "mscontext": 0x7AA,
    }
    ops = {
        "read": (csrrs, a0, x0),
        "write": (csrrw, x0, a1),
        "set": (csrrs, x0, a1),
        "clear": (csrrc, x0, a1),
    }
    funct3, rd, rs1 = ops[op]
    enc = (csr_addr[csr] << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0b1110011
    if op == "read":
        return [f"RVTEST_TSBI_CSR_ACCESS 0x{enc:08x}", f"mv {val}, a0"]
    return [f"RVTEST_TSBI_CSR_ACCESS 0x{enc:08x}, {val}"]


def _load_tdata1_type(reg: int, trig_type: int, mode: str) -> list[str]:
    """Load tdata1.type = trig_type into x{reg} and write it to tdata1."""
    lines = [
        f"# tdata1.type = {trig_type}",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, 0x{trig_type << 60:x})",
        "#else",
        f"LI(x{reg}, 0x{trig_type << 28:x})",
        "#endif",
    ]
    if mode == "Sm":
        lines.append(f"CSRW(tdata1, x{reg})")
    else:
        lines.extend(_tsbi_csr("write", "tdata1", f"x{reg}"))
    return lines


def _csr_access(instr: str, mode: str) -> str:
    """Accesses a CSR using an T-SBI or CSR operation based on mode"""
    if mode == "Sm":
        return instr
    else:
        return add_tsbi(instr)


def _generate_access_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate common trigger-CSR access tests."""
    covergroup = f"Sdtrig{mode}_access_cg"
    tc = test_data.begin_test_chunk()
    lines = tc.code

    ######################################
    coverpoint = "cp_sdtrig_csr_access_common"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Access every trigger CSR across all triggers and trigger types\n"
            "Should not cause any illegal instruction exceptions on implemented triggers",
        )
    )
    csrs = ("tdata1", "tdata2", "tdata3", "tinfo", "tcontrol", "scontext", "mcontext", "hcontext")

    type_reg, save_reg, temp_reg = test_data.int_regs.get_registers(
        3, exclude_regs=[10, 11]
    )  # exclude a0, a1 because they are used in SBI
    lines.append(f"LI(x{temp_reg}, -1)")  # all-ones value

    # TODO: sweep all triggers via CSRW(tselect, trig)
    for trig_type in range(16):
        # Write type to tdata1
        lines.extend(_load_tdata1_type(type_reg, trig_type, mode))

        for csr in csrs:
            lines.append(f"#ifdef UDB_{csr}_AVAILABLE")
            binname = f"type_{trig_type}_csr_{csr}"

            lines.extend(
                [
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                    _csr_access(f"csrr x{save_reg}, {csr} # save original value", mode),
                    _csr_access(f"csrw {csr}, x{temp_reg} # write all-1s", mode),
                    _csr_access(f"csrw {csr}, x0 # write all-0s", mode),
                    _csr_access(f"csrs {csr}, x{temp_reg} # set all-1s", mode),
                    _csr_access(f"csrc {csr}, x{temp_reg} # clear all-1s", mode),
                    _csr_access(f"csrw {csr}, x{save_reg} # write back original value", mode),
                ]
            )

            lines.append("#endif")

    test_data.int_regs.return_registers([type_reg, save_reg, temp_reg])

    return [test_data.end_test_chunk()]


def _generate_native_triggers_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate native trigger breakpoint-delegation tests."""
    # covergroup = "SdtrigSm_native_triggers_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    lines.append("#ifdef S_SUPPORTED")
    ######################################
    coverpoint = "cp_sdtrig_breakpoint_delegate"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Breakpoint from a fired trigger, taken in M-mode and delegated to\nS-mode via medeleg[3]",
        )
    )

    r1, r2, addr_reg, medeleg_reg, scr_reg = test_data.int_regs.get_registers(5)

    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for delegate in (0, 1):  # medeleg[3]
        medelegop = "csrs" if delegate else "csrc"
        lines.extend(
            [
                "",
                f"# --- medeleg[3] = {delegate} ---",
                "RVTEST_GOTO_MMODE",
                f"LI(x{medeleg_reg}, 8)",  # medeleg bit 3 = breakpoint
                f"{medelegop} medeleg, x{medeleg_reg}",
            ]
        )
    lines.extend(
        [
            "",
            "# restore medeleg[3]",
            f"csrc medeleg, x{medeleg_reg}",
        ]
    )
    test_data.int_regs.return_registers([r1, r2, addr_reg, medeleg_reg, scr_reg])

    lines.append("#endif")
    return [test_data.end_test_chunk()]


def _generate_a_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate A-extension load/store/AMO matching tests."""
    covergroup = "SdtrigSm_a_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    ######################################
    coverpoint = "cp_sdtrig_lrsc_addr"
    ######################################
    lines.append("#ifdef ZALRSC_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 address match on lr/sc access address",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for addrval in ("marker", "zero"):
        for insn in ("lr_w", "sc_w", "lr_d", "sc_d"):
            for perm in PERM_XSL:
                binname = f"addr_{addrval}_{insn}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_lrsc_data"
    ######################################
    lines.append("#ifdef ZALRSC_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 data match on lr/sc value",
        )
    )
    for addrval in ("marker", "zero"):
        for insn in ("lr_w", "sc_w", "lr_d", "sc_d"):
            for perm in PERM_XSL:
                binname = f"data_{addrval}_{insn}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_amo"
    ######################################
    lines.append("#ifdef ZAAMO_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 address match on AMO read and write portions",
        )
    )
    for addrval in ("marker", "zero"):
        for insn in ("amoswap_w", "amoswap_d"):
            for perm in PERM_XSL:
                binname = f"addr_{addrval}_{insn}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )
    lines.append("#endif")

    return [test_data.end_test_chunk()]


def _generate_combined_accesses_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate multi-access (vector / cm.push-pop) instruction tests."""
    covergroup = "SdtrigSm_combined_accesses_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    vector_ls = ("vse8", "vse16", "vse32", "vse64", "vle8", "vle16", "vle32", "vle64")
    vsews = ("sew8", "sew16", "sew32", "sew64")

    ######################################
    coverpoint = "cp_sdtrig_vector_load_store"
    ######################################
    lines.append("#ifdef V_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 matches each element of a vector load/store as an\nindividual SEW-sized access",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for addrval in ("marker", "zero"):
        for vls in vector_ls:
            for vsew in vsews:
                for size in SIZE_SEW:
                    for vperm in ("store", "load"):
                        binname = f"addr_{addrval}_{vls}_{vsew}_size_{size}_{vperm}"
                        lines.extend(
                            [
                                "",
                                add_tc(test_data, mode, binname, coverpoint, covergroup),
                            ]
                        )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_vector_accesses"
    ######################################
    lines.append("#ifdef V_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "vector accesses across scratch / scratch+8 / 0 tdata2 values",
        )
    )
    for addrval in ("marker", "marker8", "zero"):
        for vls in vector_ls:
            for vsew in vsews:
                for size in SIZE_SEW:
                    for vperm in ("store", "load"):
                        binname = f"addr_{addrval}_{vls}_{vsew}_size_{size}_{vperm}"
                        lines.extend(
                            [
                                "",
                                add_tc(test_data, mode, binname, coverpoint, covergroup),
                            ]
                        )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_cm_pop_push"
    ######################################
    lines.append("#ifdef ZCMP_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 matches each XLEN store of cm.push / cm.pop",
        )
    )
    for addrval in ("marker", "marker8", "zero"):
        for insn in ("cm_push", "cm_pop"):
            for size in SIZE_ALL:
                for perm in ("store", "load"):
                    binname = f"addr_{addrval}_{insn}_size_{size}_{perm}"
                    lines.extend(
                        [
                            "",
                            add_tc(test_data, mode, binname, coverpoint, covergroup),
                        ]
                    )
    lines.append("#endif")

    return [test_data.end_test_chunk()]


def _generate_cache_operations_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate Zicbo* cache-operation matching tests."""
    covergroup = "SdtrigSm_cache_operations_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    ######################################
    coverpoint = "cp_sdtrig_cache_zicbom"
    ######################################
    lines.append("#ifdef ZICBOM_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "cbo.clean/flush/inval match as stores",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for insn in ("cbo_clean", "cbo_flush", "cbo_inval"):
        for addrval in ("marker", "zero"):
            for size in SIZE_ALL:
                for perm in PERM_XSL:
                    binname = f"{insn}_addr_{addrval}_size_{size}_perm_{perm}"
                    lines.extend(
                        [
                            "",
                            add_tc(test_data, mode, binname, coverpoint, covergroup),
                        ]
                    )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_cache_zicboz"
    ######################################
    lines.append("#ifdef ZICBOZ_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "cbo.zero matches as a store",
        )
    )
    for addrval in ("marker", "zero"):
        for size in SIZE_ALL:
            for perm in PERM_XSL:
                binname = f"cbo_zero_addr_{addrval}_size_{size}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )
    lines.append("#endif")

    ######################################
    coverpoint = "cp_sdtrig_cache_zicbop"
    ######################################
    lines.append("#ifdef ZICBOP_SUPPORTED")
    lines.append(
        comment_banner(
            coverpoint,
            "prefetch.i/r/w (HINTs) do not match",
        )
    )
    for insn in ("prefetch_i", "prefetch_r", "prefetch_w"):
        binname = f"{insn}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )
    lines.append("#endif")

    return [test_data.end_test_chunk()]


def _generate_address_matches_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate tdata2 address-storage / translation tests."""
    covergroup = "SdtrigSm_address_matches_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    ######################################
    coverpoint = "cp_sdtrig_tdata2_translate"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "tdata2 holds full-width virtual/physical addresses across satp modes;\nhigh bit reads back",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    # RV64 satp modes; RV32 uses (bare, sv32)
    for satp in ("bare", "sv39", "sv48", "sv57"):
        for msb in (0, 1):  # tdata2 high bit
            binname = f"satp_{satp}_msb_{msb}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    return [test_data.end_test_chunk()]


def _generate_csr_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate trigger-module register semantics tests."""
    covergroup = "SdtrigSm_csr_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    ######################################
    coverpoint = "cp_sdtrig_tselect_trigs"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "tselect selects contiguous triggers starting at 0; read tinfo",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "tinfo", coverpoint, covergroup),
        ]
    )

    ######################################
    coverpoint = "cp_sdtrig_tdata_write"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "writing one tdata register does not disturb the others",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for csr in ("tdata1", "tdata2", "tdata3"):
        binname = f"write_{csr}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_csr_smode_access"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "S-mode access to M-only trigger CSRs raises illegal instruction",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for csr in ("tdata1", "tdata2", "tdata3", "tinfo", "tcontrol", "mcontext", "hcontext"):
        binname = f"smode_{csr}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_tdata1_mode_hardwired"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "type-0 dmode/data fields hard-wired to 0",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for priv in range(32):  # priv_all: all 32 m/s/u/vs/vu enable combinations
        binname = f"priv_{priv:05b}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_tinfo_read_only"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "tinfo is read-only",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "tinfo", coverpoint, covergroup),
        ]
    )

    ######################################
    coverpoint = "cp_sdtrig_tcontrol_enable"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "tcontrol.mte gates M-mode trigger firing",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for mte in (0, 1):  # tcontrol[3]
        binname = f"mte_{mte}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_tcontrol_mtrap"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mte/mpte updated on trap into M-mode",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for mte in (0, 1):  # tcontrol[3]
        for mpte in (0, 1):  # tcontrol[7]
            binname = f"mte_{mte}_mpte_{mpte}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_tcontrol_mret"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mte restored from mpte on mret",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for mte in (0, 1):  # tcontrol[3]
        for mpte in (0, 1):  # tcontrol[7]
            binname = f"mte_{mte}_mpte_{mpte}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mscontext_alias"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mscontext aliases scontext",
        )
    )
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "alias", coverpoint, covergroup),
        ]
    )

    ######################################
    coverpoint = "cp_sdtrig_mcontext_smode"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "S-mode access to mcontext raises illegal instruction",
        )
    )
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "mcontext", coverpoint, covergroup),
        ]
    )

    return [test_data.end_test_chunk()]


def _generate_mcontrol6_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate mcontrol6 address/data match trigger tests."""
    covergroup = "SdtrigSm_mcontrol6_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    store_data = (
        "zero",
        "below",
        "equal",
        "above",
        "high_diff",
        "low_diff",
        "all_ones_ish",
        "napot_below",
        "napot_above",
    )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_priv_mode"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires on a store of a known token across all 32\nm/s/u/vs/vu priv-enable combinations",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for priv in range(32):  # priv_all
        binname = f"priv_{priv:05b}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_execute_adr"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when PC == tdata2 (select=address, execute)",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for rel in ("match", "nomatch"):  # rel_exec_adr
        for perm in PERM_XSL:
            binname = f"exec_adr_{rel}_perm_{perm}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_load_store_adr"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when access address == tdata2 (select=address)",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for addrval in ("addval", "addzero"):  # addrval_scratch
        for insn in ("lw", "sw"):  # load_store
            for perm in PERM_XSL:
                binname = f"addr_{addrval}_{insn}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_execute_data"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when instruction encoding == tdata2 (select=data)",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for rel in ("match", "nomatch"):  # rel_exec_data
        for perm in PERM_XSL:
            binname = f"exec_data_{rel}_perm_{perm}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_load_store_data"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when load/store data == tdata2 (select=data)",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for addrval in ("addval", "addzero"):  # addrval_scratch
        for insn in ("lw", "sw"):  # load_store
            for perm in PERM_XSL:
                binname = f"data_{addrval}_{insn}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_execute_size"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 execute match across access sizes",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tdata2_nop in ("nop", "c_nop"):  # tdata2_nop_sizes
        for nop in ("nop", "c_nop"):  # nop_sizes
            for size in SIZE_ALL:
                binname = f"td2_{tdata2_nop}_insn_{nop}_size_{size}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_load_store_size"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 load/store match across access sizes",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    # base RV32I set; RV64 adds lwu/ld/sd, F/D/Zc* add more (see loadstore_all in svh)
    loadstore = ("lb", "lbu", "lh", "lhu", "lw", "sb", "sh", "sw")
    for insn in loadstore:
        for size in SIZE_ALL:
            for perm in PERM_XSL:
                binname = f"{insn}_size_{size}_perm_{perm}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_match"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 match types equal / ge / lt / not-equal",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for match in ("eq", "ge", "lt", "neq"):  # match_grp
        for data in store_data:
            binname = f"match_{match}_data_{data}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_match_napot"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 NAPOT and not-NAPOT match types",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for match in ("napot", "not_napot"):  # match_napot_grp
        for data in store_data:
            binname = f"match_{match}_data_{data}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_match_mask"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 mask-low / mask-high match types",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for match in ("mask_low", "mask_high", "not_mask_low", "not_mask_high"):  # match_mask_grp
        for data in store_data:
            binname = f"match_{match}_data_{data}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    ######################################
    coverpoint = "cp_sdtrig_mcontrol6_chain_adr"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "chained mcontrol6 triggers fire only when both match the same\n"
            "instruction (trig0 chain=1 address, trig1 chain=0 data)",
        )
    )
    # chain uses fixed triggers 0 and 1 (chain_pair/select_pair are single-bin)
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "chain_adr", coverpoint, covergroup),
        ]
    )

    return [test_data.end_test_chunk()]


def _generate_icount_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate icount instruction-count trigger tests."""
    covergroup = "SdtrigSm_icount_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    count_val = ("zero", "one", "many")

    ######################################
    coverpoint = "cp_sdtrig_icount_hardwired"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "icount priv/action hard-wired field behavior",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for priv in range(32):  # icount_priv_all
        binname = f"priv_{priv:05b}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_icount_instr"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "icount fires after count instructions",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for count in count_val:
        binname = f"count_{count}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_icount_trap"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "icount count decrement across a trap",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for count in count_val:
        binname = f"count_{count}"
        lines.extend(
            [
                "",
                add_tc(test_data, mode, binname, coverpoint, covergroup),
            ]
        )

    ######################################
    coverpoint = "cp_sdtrig_icount_eq0"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "icount pending bit when count reaches 0",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for count in count_val:
        for pending in (0, 1):  # tdata1[8]
            binname = f"count_{count}_pending_{pending}"
            lines.extend(
                [
                    "",
                    add_tc(test_data, mode, binname, coverpoint, covergroup),
                ]
            )

    return [test_data.end_test_chunk()]


def _generate_itrigger_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate itrigger interrupt trigger tests."""
    covergroup = "SdtrigSm_itrigger_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    # one-hot tdata2 interrupt-code bins (RV64 / no-H spelling)
    intcode = ("ssi", "msi", "sti", "mti", "sei", "mei", "lcofi")

    ######################################
    coverpoint = "cp_sdtrig_itrigger"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "itrigger fires on each interrupt cause in the tdata2 mask",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for code in intcode:
        for priv in range(32):  # itrigger_priv_all
            for hit in ("nofire", "fire"):
                for tval in ("zero", "nonzero"):  # tval_zero
                    binname = f"code_{code}_priv_{priv:05b}_hit_{hit}_tval_{tval}"
                    lines.extend(
                        [
                            "",
                            add_tc(test_data, mode, binname, coverpoint, covergroup),
                        ]
                    )

    ######################################
    coverpoint = "cp_sdtrig_itrigger_nmi"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "itrigger nmi bit",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for code in intcode:
        for priv in range(32):  # itrigger_priv_all
            for nmi in ("off", "on"):  # tdata1[10]
                binname = f"code_{code}_priv_{priv:05b}_nmi_{nmi}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    return [test_data.end_test_chunk()]


def _generate_etrigger_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate etrigger exception trigger tests."""
    covergroup = "SdtrigSm_etrigger_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    ######################################
    coverpoint = "cp_sdtrig_etrigger"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "etrigger fires on each exception cause in the tdata2 mask",
        )
    )
    # one-hot tdata2 exception-code bins (base set; U/S/H/etc. gated in svh)
    excode = ("iam", "iacc", "ill", "bp", "lam", "lacc", "sam", "sacc", "ecu", "ecs", "ecm", "ipf", "lpf", "spf")
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for code in excode:
        for priv in range(32):  # etrigger_priv_all
            for tval in ("zero", "nonzero"):  # tval_zero
                binname = f"code_{code}_priv_{priv:05b}_tval_{tval}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    return [test_data.end_test_chunk()]


def _generate_textra_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate textra32/64 (tdata3) context-matching tests."""
    covergroup = "SdtrigSm_textra_cg"
    tc = test_data.begin_test_chunk()
    lines: list[str] = tc.code

    trig_type4 = ("icount", "itrigger", "etrigger", "mcontrol6")
    # RV64 spelling; RV32 bins differ (see svh)
    mhvalue = ("match", "zero", "half")
    svalue = ("aaaaaaaa", "bbbbbbaa", "bbbbaabb", "bbaabbbb", "aabbbbbb", "bbbbbbbb")
    svalue_asid = ("below", "equal", "above")

    ######################################
    coverpoint = "cp_sdtrig_textra_mcontext"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "textra mhselect/mhvalue match against mcontext",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tt in trig_type4:
        for mhv in mhvalue:
            for rel in ("match", "nomatch"):  # rel_mhvalue
                binname = f"type_{tt}_mhvalue_{mhv}_rel_{rel}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_textra_scontext"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "textra sselect=scontext svalue/sbytemask match against scontext",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tt in trig_type4:
        for sv in svalue:
            for mask in range(16):  # sbytemask (RV64: 4 bits; RV32: 2 bits -> range(4))
                for rel in ("match", "nomatch"):  # rel_scontext
                    binname = f"type_{tt}_svalue_{sv}_mask_{mask:04b}_rel_{rel}"
                    lines.extend(
                        [
                            "",
                            add_tc(test_data, mode, binname, coverpoint, covergroup),
                        ]
                    )

    ######################################
    coverpoint = "cp_sdtrig_textra_asid"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "textra sselect=asid match against satp.ASID",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tt in trig_type4:
        for sv in svalue_asid:
            for rel in ("match", "nomatch"):  # rel_asid
                binname = f"type_{tt}_asid_{sv}_rel_{rel}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_textra_mcontext_smode"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "textra mcontext match evaluated in S-mode",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tt in trig_type4:
        for mhv in mhvalue:
            for rel in ("match", "nomatch"):  # rel_mhvalue
                binname = f"type_{tt}_mhvalue_{mhv}_rel_{rel}"
                lines.extend(
                    [
                        "",
                        add_tc(test_data, mode, binname, coverpoint, covergroup),
                    ]
                )

    ######################################
    coverpoint = "cp_sdtrig_textra_scontext_smode"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "textra scontext match evaluated in S-mode",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    for tt in trig_type4:
        for sv in svalue:
            for mask in range(16):  # sbytemask
                for rel in ("match", "nomatch"):  # rel_scontext
                    binname = f"type_{tt}_svalue_{sv}_mask_{mask:04b}_rel_{rel}"
                    lines.extend(
                        [
                            "",
                            add_tc(test_data, mode, binname, coverpoint, covergroup),
                        ]
                    )

    ######################################
    coverpoint = "cp_sdtrig_smode_fields_hardwired"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "svalue/sselect read 0 when S-mode is not supported",
        )
    )
    # TODO: sweep all triggers via CSRW(tselect, trig); using trigger 0 for now
    lines.extend(
        [
            "",
            add_tc(test_data, mode, "hardwired", coverpoint, covergroup),
        ]
    )

    return [test_data.end_test_chunk()]


def _generate_parameters(test_data: TestData) -> list[TestChunk]:
    """Emit the UDB trigger-CSR availability.
    TODO: replace this with UDB-autogenerated parameters.
    """
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            # TODO: Change to uppercase
            "#define UDB_NUM_TRIGGERS 4",
            "#define UDB_tdata1_AVAILABLE",
            "#define UDB_tdata2_AVAILABLE",
            "#define UDB_tdata3_AVAILABLE",
            "#define UDB_tinfo_AVAILABLE",
            "#define UDB_scontext_AVAILABLE",
            "#define UDB_mcontext_AVAILABLE",
            "//#define UDB_tcontrol_AVAILABLE",
            "//#define UDB_hcontext_AVAILABLE",
            "//#define UDB_mscontext_AVAILABLE",
        ]
    )
    return [test_data.end_test_chunk()]


# ── Suite assembly ─────────────────────────────────────────────────────────


def generate_sdtrig_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the full Sdtrig suite for ``mode`` ("Sm"/"S"/"U") as test chunks."""
    # TODO: Eventually split covergroups into their own file with chunk function
    test_chunks: list[TestChunk] = []
    test_chunks.extend(_generate_parameters(test_data))
    test_chunks.extend(_generate_access_tests(test_data, mode))
    # test_chunks.extend(_generate_native_triggers_tests(test_data, mode))
    # test_chunks.extend(_generate_a_tests(test_data, mode))
    # test_chunks.extend(_generate_combined_accesses_tests(test_data, mode))
    # test_chunks.extend(_generate_cache_operations_tests(test_data, mode))
    # test_chunks.extend(_generate_address_matches_tests(test_data, mode))
    # test_chunks.extend(_generate_csr_tests(test_data, mode))
    # test_chunks.extend(_generate_mcontrol6_tests(test_data, mode))
    # test_chunks.extend(_generate_icount_tests(test_data, mode))
    # test_chunks.extend(_generate_itrigger_tests(test_data, mode))
    # test_chunks.extend(_generate_etrigger_tests(test_data, mode))
    # test_chunks.extend(_generate_textra_tests(test_data, mode))
    return test_chunks
