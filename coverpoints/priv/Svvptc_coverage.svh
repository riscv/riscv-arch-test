///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David_Harris@hmc.edu October 2026
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVVPTC

// Each testcase takes a page fault on a PTE with V=0, sets V=1 with a plain store and no SFENCE.VMA,
// and retries the access; the signature checks the retry. The coverpoints sample the page fault.
covergroup Svvptc_cg with function sample(ins_t ins, bit load_fault, bit store_fault, bit fetch_fault);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    load_page_fault: coverpoint load_fault {
        bins fault = {1};
    }
    store_page_fault: coverpoint store_fault {
        bins fault = {1};
    }
    fetch_page_fault: coverpoint fetch_fault {
        bins fault = {1};
    }

    `ifdef UDB_MXLEN_64
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
    `else
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    cp_load:  cross load_page_fault,  satp_mode, priv_mode_s_u;
    cp_store: cross store_page_fault, satp_mode, priv_mode_s_u;
    cp_fetch: cross fetch_page_fault, satp_mode, priv_mode_s_u;
endgroup

function void svvptc_sample(int hart, int issue, ins_t ins);
    `XLEN_BITS cause = get_csr_val(hart, issue, `SAMPLE_AFTER, "scause", "code");
    bit        trapped = ins.current.csr_wb[CSR_SCAUSE];

    // A fetch page fault is reported on the jump to the page.
    Svvptc_cg.sample(ins,
                     trapped && (ins.current.insn ==? LW) && cause == `UDB_MXLEN'(LOAD_PAGE_FAULT),
                     trapped && (ins.current.insn ==? SW) && cause == `UDB_MXLEN'(STORE_AMO_PAGE_FAULT),
                     trapped && (ins.current.insn ==? JALR) && cause == `UDB_MXLEN'(INSTRUCTION_PAGE_FAULT));
endfunction
