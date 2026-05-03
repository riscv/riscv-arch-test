///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Sstvala Coverage
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//


`define COVER_SSTVALA

covergroup Sstvala_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    cause_instr_misaligned: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[5:0] {
            bins set = {6'd0};
    }

    stval_equals_vaddr_d:   coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval") == ins.current.virt_adr_d {
            bins match = {1'b1};
    }

    stval_equals_vaddr_i:   coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval") == ins.current.virt_adr_i {
            bins match = {1'b1};
    }

    stval_equals_insn: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval")[31:0] == ins.current.insn[31:0] {
           bins match = {1'b1};
}

    medeleg_instr_ma: coverpoint ins.current.csr[CSR_MEDELEG][0] {
            bins delegated = {1'b1};
    }
    medeleg_load_ma: coverpoint ins.current.csr[CSR_MEDELEG][4] {
            bins delegated = {1'b1};
    }
    medeleg_store_ma: coverpoint ins.current.csr[CSR_MEDELEG][6] {
            bins delegated = {1'b1};
    }
    medeleg_illegal: coverpoint ins.current.csr[CSR_MEDELEG][2] {
            bins delegated = {1'b1};
    }

    medeleg_instr_pf: coverpoint ins.current.csr[CSR_MEDELEG][12] {
            bins delegated = {1'b1};
    }
    medeleg_load_pf: coverpoint ins.current.csr[CSR_MEDELEG][13] {
            bins delegated = {1'b1};
    }
    medeleg_store_pf: coverpoint ins.current.csr[CSR_MEDELEG][15] {
            bins delegated = {1'b1};
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    medeleg_instr_af: coverpoint ins.current.csr[CSR_MEDELEG][1] {
            bins delegated = {1'b1};
    }
    medeleg_load_af: coverpoint ins.current.csr[CSR_MEDELEG][5] {
            bins delegated = {1'b1};
    }
    medeleg_store_af: coverpoint ins.current.csr[CSR_MEDELEG][7] {
            bins delegated = {1'b1};
    }
    `endif

    // -----------------------------------------------------------------------
    // Instruction type bins
    // -----------------------------------------------------------------------

    lw_insn: coverpoint ins.current.insn {
            wildcard bins lw = {LW};
    }
    sw_insn: coverpoint ins.current.insn {
            wildcard bins sw = {SW};
    }
    jalr_insn: coverpoint ins.prev.insn {
            wildcard bins jalr = {JALR};
    }
    jalr_insn_curr: coverpoint ins.current.insn {
            wildcard bins jalr = {JALR};
    }

    illegalops: coverpoint ins.current.insn {
            bins zeros = {'0};
            bins ones  = {'1};
    }

    vaddr_d_misaligned: coverpoint {ins.current.rs1_val + ins.current.imm}[1:0] {
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    illegal_data_address: coverpoint ins.current.rs1_val + ins.current.imm {
            bins fault_addr = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    illegal_instr_address: coverpoint ins.current.rs1_val + ins.current.imm {
            bins fault_addr = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    `endif

    pf_stval: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval") {
    `ifdef XLEN64
            bins sv39_page = {64'h0000000140300000};
    `else
            bins sv32_page = {32'hC0300000};
    `endif
}


    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    cp_load_access_fault:  cross priv_mode_s, illegal_data_address,  stval_equals_vaddr_d, medeleg_load_af,  lw_insn;
    cp_store_access_fault: cross priv_mode_s, illegal_data_address,  stval_equals_vaddr_d, medeleg_store_af, sw_insn;
    cp_instr_access_fault: cross priv_mode_s, illegal_instr_address, stval_equals_vaddr_i, medeleg_instr_af, jalr_insn_curr;
    `endif

    cp_load_address_misaligned:  cross priv_mode_s, lw_insn, stval_equals_vaddr_d, vaddr_d_misaligned, medeleg_load_ma;
    cp_store_address_misaligned: cross priv_mode_s, sw_insn, stval_equals_vaddr_d, vaddr_d_misaligned, medeleg_store_ma;

    `ifndef COVER_ZCA
    cp_instr_adr_misaligned_jalr: cross priv_mode_s, jalr_insn, cause_instr_misaligned, stval_equals_vaddr_i, medeleg_instr_ma;
    `endif

    // -----------------------------------------------------------------------
    // Illegal instruction cross
    // -----------------------------------------------------------------------

    cp_illegal_instruction: cross priv_mode_s, illegalops, stval_equals_insn, medeleg_illegal;

    // -----------------------------------------------------------------------
    // Page-fault crosses
    // -----------------------------------------------------------------------
    cp_stval_load_page_fault:  cross priv_mode_s, lw_insn,        medeleg_load_pf,  pf_stval;
    cp_stval_store_page_fault: cross priv_mode_s, sw_insn,        medeleg_store_pf, pf_stval;
    cp_stval_instr_page_fault: cross priv_mode_s, jalr_insn_curr, medeleg_instr_pf, pf_stval;


endgroup

function void sstvala_sample(int hart, int issue, ins_t ins);
    Sstvala_cg.sample(ins);
endfunction
