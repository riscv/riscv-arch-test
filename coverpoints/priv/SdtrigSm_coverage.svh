///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Angela Zheng, angela20061015@gmail.com, 10 September 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SDTRIGSM

covergroup SdtrigSm_trig_module_reg_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    type_disabled: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins disabled = {4'd15};
    }
    tdata1_type_six: coverpoint ins.current.rs1_val[XLEN-1:XLEN-4] {
        bins mcontrol6 = {4'd6};
    }
    priv_bits: coverpoint ins.current.rs1_val[26:0] {
        bins priv = {27'b001_1000_0000_0000_0000_0101_1000};
    }
    csr_tselect:  coverpoint ins.current.insn[31:20] {
        bins tselect = {CSR_TSELECT};
    }
    csr_tdata: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
        bins tdata2 = {CSR_TDATA2};
        bins tdata3 = {CSR_TDATA3};
    }
    csr_tdata1: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
    }
    csr_tinfo: coverpoint ins.current.insn[31:20] {
        bins tinfo = {CSR_TINFO};
    }
    csr_global_reg: coverpoint ins.current.insn[31:20] {
        bins tselect  = {CSR_TSELECT};
        bins tcontrol = {CSR_TCONTROL};
        bins mcontext = {CSR_MCONTEXT};
        bins scontext = {CSR_SCONTEXT};
        `ifdef H_SUPPORTED
            bins hcontext = {CSR_HCONTEXT};
        `endif
    }
    csr_local_reg: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
        bins tdata2 = {CSR_TDATA2};
        bins tdata3 = {CSR_TDATA3};
        bins tinfo  = {CSR_TINFO};
    }
    csr_access: coverpoint ins.current.insn{
        wildcard bins csrrw0 = {CSRRW} iff (ins.current.rs1_val == '0);
        wildcard bins csrrw1 = {CSRRW} iff (ins.current.rs1_val == '1);
    }
    csrr: coverpoint ins.current.insn{
        wildcard bins csrr = {CSRR};
    }
    csrw: coverpoint ins.current.insn{
        wildcard bins csrw = {CSRW};
    }

    // main coverpoints
    cp_tdata_write:           cross priv_mode_m, triggernum, type_disabled, csr_tdata, csr_access;          // NTRIG * 3 CSRs * 2 values
    cp_csr_access_global:     cross priv_mode_m, csr_global_reg, csr_access;                                // 5 CSRs * 2 values
    cp_csr_access_local:      cross priv_mode_m, triggernum, csr_local_reg, csr_access;                     // NTRIG * 4 CSRs * 2 values
    cp_tselect_trigs:         cross priv_mode_m, triggernum, csrr, csr_tselect;                             // NTRIG
    cp_tdata1_mode_hardwired: cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_type_six, priv_bits;  // NTRIG
    cp_tinfo_read_only:       cross priv_mode_m, triggernum, csr_tinfo, csr_access;                         // NTRIG
endgroup

function void sdtrigsm_sample(int hart, int issue, ins_t ins);
    SdtrigSm_trig_module_reg_cg.sample(ins);
endfunction
