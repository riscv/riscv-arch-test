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
    load_ok: coverpoint ins.current.insn {
        wildcard bins lw = {LW} iff (!ins.current.trap);
    }
    store_ok: coverpoint ins.current.insn {
        wildcard bins sw = {SW} iff (!ins.current.trap);
    }
    fetch_ok: coverpoint ins.current.trap {
        bins no_trap = {1'b0};
    }

    satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
        `ifdef SV39_SUPPORTED
            bins sv39 = {4'b1000};
        `endif
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

function void svrsw60t59b_sample(int hart, int issue, ins_t ins);
    Svrsw60t59b_cg.sample(ins);
endfunction
