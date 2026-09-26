///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shtvala: guest-page faults from VS-mode and VU-mode write htval with the faulting guest physical address.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHTVALA

`include "general/RISCV_coverage_hypervisor.svh"

covergroup Shtvala_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef H_TWO_STAGE
        lw : coverpoint ins.current.insn {
            wildcard bins lw = {LW};
        }
        sw : coverpoint ins.current.insn {
            wildcard bins sw = {SW};
        }
        jalr : coverpoint ins.current.insn {
            wildcard bins jalr = {JALR};
        }
        instr_guest_page_fault : coverpoint ins.current.csr[CSR_SCAUSE] {
            bins scause = {20};
        }
        load_guest_page_fault : coverpoint ins.current.csr[CSR_SCAUSE] {
            bins scause = {21};
        }
        store_guest_page_fault : coverpoint ins.current.csr[CSR_SCAUSE] {
            bins scause = {23};
        }
        // The access whose guest physical address htval holds (>> 2): the final access, whose address has the
        // page offset of the virtual address, or the implicit read of a VS-stage PTE, after which htinst holds a
        // pseudoinstruction.  The test sets htval to a random value before each trap.
        htval_gpa : coverpoint {
            ins.current.csr[CSR_HTINST] == (`UDB_MXLEN == 64 ? 'h3000 : 'h2000),
            ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval") << 2) & 'hFFF) ==
                ((ins.current.rs1_val + ins.current.imm) & 'hFFF)
        } {
            bins final_gpa    = {2'b01};
            bins implicit_gpa = {2'b10};
        }

        cp_load_guest_page_fault:  cross priv_mode_vs_vu, lw,   load_guest_page_fault,  htval_gpa;
        cp_store_guest_page_fault: cross priv_mode_vs_vu, sw,   store_guest_page_fault, htval_gpa;
        cp_instr_guest_page_fault: cross priv_mode_vs_vu, jalr, instr_guest_page_fault, htval_gpa;
    `endif
endgroup

function void shtvala_sample(int hart, int issue, ins_t ins);
    Shtvala_cg.sample(ins);
endfunction
