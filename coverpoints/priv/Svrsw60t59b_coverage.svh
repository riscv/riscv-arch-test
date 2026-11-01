///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David_Harris@hmc.edu October 2026
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVRSW60T59B

// Each testcase sets PTE bits 60:59 in a leaf or non-leaf PTE and accesses the page, which must not fault.
// The trace reports the leaf PTE of a walk that completes, so the coverpoints sample the leaf cases; the
// signature checks the non-leaf cases.
covergroup Svrsw60t59b_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    rsw60t59b_PTE_i: coverpoint ins.current.pte_i[60:59] {
        bins bit_59 = {2'b01};
        bins bit_60 = {2'b10};
        bins both   = {2'b11};
    }
    rsw60t59b_PTE_d: coverpoint ins.current.pte_d[60:59] {
        bins bit_59 = {2'b01};
        bins bit_60 = {2'b10};
        bins both   = {2'b11};
    }

    // Accesses that complete: the trace marks no read, write or execute access, so name the instruction.
    // Only instructions in the page under test have bits 60:59 set in pte_i.
    load_ok: coverpoint ins.current.insn iff (!ins.current.trap) {
        wildcard bins lw = {LW};
    }
    store_ok: coverpoint ins.current.insn iff (!ins.current.trap) {
        wildcard bins sw = {SW};
    }
    // The first instruction of the page under test, reached by the jalr, completes
    fetch_ok: coverpoint ins.prev.insn iff (!ins.current.trap) {
        wildcard bins jalr = {JALR};
    }

    satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
        bins sv39 = {4'b1000};
        `ifdef SV48_SUPPORTED
            bins sv48 = {4'b1001};
        `endif
        `ifdef SV57_SUPPORTED
            bins sv57 = {4'b1010};
        `endif
    }

    cp_load:  cross rsw60t59b_PTE_d, load_ok,  satp_mode, priv_mode_s_u;
    cp_store: cross rsw60t59b_PTE_d, store_ok, satp_mode, priv_mode_s_u;
    cp_fetch: cross rsw60t59b_PTE_i, fetch_ok, satp_mode, priv_mode_s_u;
endgroup

`ifdef H_SUPPORTED
// Svrsw60t59b in the VS-stage (hgatp = Bare) and in the G-stage (vsatp = Bare), from VS-mode and VU-mode.  As in
// Svrsw60t59b_cg, the coverpoints sample the leaf cases and the signature checks the non-leaf cases.
covergroup Svrsw60t59b_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    rsw60t59b_PTE_i: coverpoint ins.current.pte_i[60:59] {
        bins bit_59 = {2'b01};
        bins bit_60 = {2'b10};
        bins both   = {2'b11};
    }
    rsw60t59b_PTE_d: coverpoint ins.current.pte_d[60:59] {
        bins bit_59 = {2'b01};
        bins bit_60 = {2'b10};
        bins both   = {2'b11};
    }

    // Accesses that complete: the trace marks no read, write or execute access, so name the instruction.
    // Only instructions in the page under test have bits 60:59 set in pte_i.
    load_ok: coverpoint ins.current.insn iff (!ins.current.trap) {
        wildcard bins lw = {LW};
    }
    store_ok: coverpoint ins.current.insn iff (!ins.current.trap) {
        wildcard bins sw = {SW};
    }
    // The first instruction of the page under test, reached by the jalr, completes
    fetch_ok: coverpoint ins.prev.insn iff (!ins.current.trap) {
        wildcard bins jalr = {JALR};
    }

    vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            bins sv39 = {8};
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            bins sv48 = {9};
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            bins sv57 = {10};
        `endif
    }
    hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        `ifdef UDB_SV39X4_TRANSLATION
            bins sv39x4 = {8};
        `endif
        `ifdef UDB_SV48X4_TRANSLATION
            bins sv48x4 = {9};
        `endif
        `ifdef UDB_SV57X4_TRANSLATION
            bins sv57x4 = {10};
        `endif
    }
    vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }

    cp_vsatp_load:  cross rsw60t59b_PTE_d, load_ok,  vsatp_mode, hgatp_bare, priv_mode_vs_vu;
    cp_vsatp_store: cross rsw60t59b_PTE_d, store_ok, vsatp_mode, hgatp_bare, priv_mode_vs_vu;
    cp_vsatp_fetch: cross rsw60t59b_PTE_i, fetch_ok, vsatp_mode, hgatp_bare, priv_mode_vs_vu;
    cp_hgatp_load:  cross rsw60t59b_PTE_d, load_ok,  vsatp_bare, hgatp_mode, priv_mode_vs_vu;
    cp_hgatp_store: cross rsw60t59b_PTE_d, store_ok, vsatp_bare, hgatp_mode, priv_mode_vs_vu;
    cp_hgatp_fetch: cross rsw60t59b_PTE_i, fetch_ok, vsatp_bare, hgatp_mode, priv_mode_vs_vu;
endgroup
`endif // H_SUPPORTED

function void svrsw60t59b_sample(int hart, int issue, ins_t ins);
    Svrsw60t59b_cg.sample(ins);
    `ifdef H_SUPPORTED
        Svrsw60t59b_H_cg.sample(ins);
    `endif
endfunction
