///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — vector accesses to a shadow stack page
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
//
// Split out from ZicfissU because it needs V in the suite's march string and vector
// state set up before any access. The shadow stack rules do not special-case vector:
// a shadow stack page is readable by anything that only loads, and writable only by
// SSPUSH, C.SSPUSH and SSAMOSWAP. Vector loads therefore succeed and vector stores
// fault, including when the access starts on an adjacent page and runs into the SS page.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSV
covergroup ZicfissV_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── Vector accessor building blocks ───────────────────────────────────
    vector_unit_load: coverpoint ins.current.insn {
        wildcard bins vle8  = {VLE8_V};
        wildcard bins vle16 = {VLE16_V};
        wildcard bins vle32 = {VLE32_V};
    }
    vector_unit_store: coverpoint ins.current.insn {
        wildcard bins vse8  = {VSE8_V};
        wildcard bins vse16 = {VSE16_V};
        wildcard bins vse32 = {VSE32_V};
    }
    vector_strided: coverpoint ins.current.insn {
        wildcard bins vlse8  = {VLSE8_V};
        wildcard bins vlse32 = {VLSE32_V};
    }
    vector_indexed: coverpoint ins.current.insn {
        wildcard bins vluxei8 = {VLUXEI8_V};
        wildcard bins vsuxei8 = {VSUXEI8_V};
    }

    // ── Page building blocks ──────────────────────────────────────────────
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
    // Where the access starts relative to the shadow stack page. An access that
    // begins on the adjacent page and runs into the SS page must still fault on the
    // element that lands there.
    access_origin: coverpoint ins.current.rs1_val[12] {
        bins on_ss_page       = {1'b0};
        bins on_adjacent_page = {1'b1};
    }
    // MXR must not affect whether a load may read the R=0 shadow stack page.
    sstatus_mxr: coverpoint ins.prev.csr[CSR_SSTATUS][19] {
        bins mxr_clear = {1'b0};
        bins mxr_set   = {1'b1};
    }

    // ── Main coverpoints ──────────────────────────────────────────────────
    // Vector loads only read, so they are permitted on a shadow stack page.
    cp_ss_vector_load:          cross priv_mode_u, vector_unit_load, pte_ss_page, sstatus_mxr;

    // Vector stores are not in the set permitted to write a shadow stack page.
    cp_ss_vector_store:         cross priv_mode_u, vector_unit_store, pte_ss_page;

    // Strided and indexed forms, including accesses that begin on the adjacent page.
    cp_ss_vector_strided:       cross priv_mode_u, vector_strided, pte_ss_page, access_origin;
    cp_ss_vector_indexed:       cross priv_mode_u, vector_indexed, pte_ss_page, access_origin;

endgroup

function void zicfissv_sample(int hart, int issue, ins_t ins);
    ZicfissV_cg.sample(ins);
endfunction
