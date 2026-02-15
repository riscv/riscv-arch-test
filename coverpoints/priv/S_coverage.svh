///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 3 December 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_S

covergroup S_scause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    scause: coverpoint ins.current.insn[31:20] {
        bins mcause = {CSR_SCAUSE};
    }
    scause_interrupt : coverpoint ins.current.rs1_val[XLEN-1] {
        bins interrupt = {1};
    }
    scause_exception : coverpoint ins.current.rs1_val[XLEN-1] {
        bins exception = {0};
    }
    scause_exception_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
        // exclude reserved and custom fields
        bins b_0_instruction_address_misaligned = {0};
        bins b_1_instruction_address_fault = {1};
        bins b_2_illegal_instruction = {2};
        bins b_3_breakpoint = {3};
        bins b_4_load_address_misaligned = {4};
        bins b_5_load_access_fault = {5};
        bins b_6_store_address_misaligned = {6};
        bins b_7_store_access_fault = {7};
        bins b_8_ecall_u = {8};
        bins b_9_ecall_s = {9};
        bins b_10_ecall_vs = {10};
        bins b_11_ecall_m = {11};
        bins b_12_instruction_page_fault = {12};
        bins b_13_load_page_fault = {13};
        //bins b_14_reserved = {14};
        bins b_15_store_page_fault = {15};
        bins b_16_double_trap = {16};
        //bins b_17_reserved = {17};
        bins b_18_software_check = {18};
        bins b_19_hardware_error = {19};
        bins b_20_instr_guest_page_fault = {20};
        bins b_21_load_guest_page_fault = {21};
        bins b_22_virtual_instruction = {22};
        bins b_23_store_guest_page_fault = {23};
        //bins b_31_24_custom = {[31:24]};
        //bins b_47_32_reserved = {[47:32]};
        //bins b_63_48_custom = {[63:48]};
    }
    scause_interrupt_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
        // exclude reserved and custom fields
        //bins b_0_reserved = {0};
        bins b_1_supervisor_software = {1};
        bins b_2_vs_software = {2};
        bins b_3_machine_software = {3};
        //bins b_4_reserved = {4};
        bins b_5_supervisor_timer = {5};
        bins b_6_vs_timer = {6};
        bins b_7_machine_timer = {7};
        //bins b_8_reserved = {8};
        bins b_9_supervisor_external = {9};
        bins b_10_vs_external = {10};
        bins b_11_machine_external = {11};
        bins b_12_supervisor_guest_external = {12};
        bins b_13_counter_overflow = {13};
        //bins b_14_reserved = {14};
        //bins b_15_reserved = {15};
    }

    // main coverpoints
    cp_scause_write_exception: cross priv_mode_s, csrrw, scause, scause_exception_values, scause_exception; // CSR write of scause in S mode with interesting values
    cp_scause_write_interrupt: cross priv_mode_s, csrrw, scause, scause_interrupt_values, scause_interrupt; // CSR write of scause in S mode with interesting values
endgroup


covergroup S_sstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cp_sstatus_sd: coverpoint ins.current.rs1_val[XLEN-1]  {
    }
    cp_sstatus_fs: coverpoint ins.current.rs1_val[14:13] {
    }
    cp_sstatus_vs: coverpoint ins.current.rs1_val[10:9] {
    }
    cp_sstatus_xs: coverpoint ins.current.rs1_val[16:15] {
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    sstatus: coverpoint ins.current.insn[31:20] {
        bins mstatus = {CSR_SSTATUS};
    }
    // main coverpoints
    cp_sstatus_sd_write: cross priv_mode_s, csrrw, sstatus, cp_sstatus_sd, cp_sstatus_fs, cp_sstatus_vs, cp_sstatus_xs;

endgroup

covergroup S_sprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    privinstrs: coverpoint ins.current.insn  {
        bins ecall  = {ECALL};
        bins ebreak = {EBREAK};
    }
    mret: coverpoint ins.current.insn  {
        bins mret   = {MRET};
    }
    sret: coverpoint ins.current.insn  {
        bins sret   = {SRET};
    }
    // old_mstatus_mprv: coverpoint ins.prev.csr[12'h300][17] {
    // }
    old_mstatus_tsr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tsr")[0] {
    }
    old_sstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
    }
    old_mstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spp")[0] {
    }
    old_mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] {
        bins U_mode = {2'b00};
        bins S_mode = {2'b01};
        bins M_mode = {2'b11};
    }
    old_mstatus_mprv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0] {
    }
    old_mstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spie")[0] {
    }
    old_mstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
    }
    old_mstatus_mie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
    }
    old_mstatus_mpie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie")[0] {
    }
    old_sstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] {
    }
    old_sstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0] {
    }
    // main coverpoints
    cp_sprivinst: cross priv_mode_s, privinstrs;
    cp_mret_s:    cross priv_mode_s, mret;
    cp_sret_s:    cross priv_mode_s, sret, old_sstatus_spp, old_sstatus_spie, old_sstatus_sie, old_mstatus_tsr;
    cp_mret_m:    cross priv_mode_m, mret, old_mstatus_mpp, old_mstatus_mprv, old_mstatus_mpie, old_mstatus_mie;
    cp_sret_m:    cross priv_mode_m, sret, old_mstatus_spp, old_mstatus_mprv, old_mstatus_spie, old_mstatus_sie, old_mstatus_tsr;
endgroup

covergroup S_scsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`XLEN-1] };
    }

    walking_ones_nonmode: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        `ifdef XLEN64
            bins b_1[] = { [0:`XLEN-5] };
        `else
            bins b_1[] = { [0:`XLEN-2] };
        `endif
    }


    csrname : coverpoint ins.current.insn[31:20] {
        bins sstatus       = {CSR_SSTATUS};
        bins sie           = {CSR_SIE};
        bins stvec         = {CSR_STVEC};
        bins scounteren    = {CSR_SCOUNTEREN};
        bins sscratch      = {CSR_SSCRATCH};
        bins sepc          = {CSR_SEPC};
        bins scause        = {CSR_SCAUSE};
        bins stval         = {CSR_STVAL};
        bins sip           = {CSR_SIP};
        bins senvcfg       = {CSR_SENVCFG};
    }
    csruname : coverpoint ins.current.insn[31:20] {
        `ifdef F_SUPPORTED
            bins fcsr      = {CSR_FCSR};
            bins fflags    = {CSR_FFLAGS};
            bins frm       = {CSR_FRM};
        `endif
        `ifdef V_SUPPORTED
            bins vstart = {CSR_VSTART};
            bins vxsat  = {CSR_VXSAT};
            bins vxrm   = {CSR_VXRM};
            bins vcsr   = {CSR_VCSR};
            bins vl     = {CSR_VL};
            bins vtype  = {CSR_VTYPE};
            bins vlenb  = {CSR_VLENB};
        `endif
    }
    satp : coverpoint ins.current.insn[31:20] {
        bins satp          = {CSR_SATP};
    }

    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

    csr_machine: coverpoint ins.current.insn[31:20]  {
        bins machine_0[] = {[12'h300:12'h3FF]};
        bins machine_1[] = {[12'h700:12'h7FF]};
        bins machine_2[] = {[12'hB00:12'hBFF]};
        bins machine_3[] = {[12'hF00:12'hFFF]};
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }
    shadow : coverpoint {ins.prev.insn[31:20], ins.current.insn[31:20]} {
        bins mstatus_sstatus = { {CSR_MSTATUS, CSR_SSTATUS} };
        bins mie_sie         = { {CSR_MIE, CSR_SIE} };
        bins mip_sip         = { {CSR_MIP, CSR_SIP} };
        bins sstatus_mstatus = { {CSR_SSTATUS, CSR_MSTATUS} };
        bins sie_mie         = { {CSR_SIE, CSR_MIE} };
        bins sip_mip         = { {CSR_SIP, CSR_MIP} };
    }
    csrw_prev: coverpoint ins.prev.insn {
        wildcard bins csrr = {CSRR};
    }
    rs1_prev: coverpoint ins.prev.rs1_val {
        bins zero = { 0  };
        bins ones = { -1 };
    }

    cp_scsr_access:           cross priv_mode_s, csrname, csraccesses;
    cp_scsrwalk:              cross priv_mode_s, csrname, csrop, walking_ones;
    cp_scsr_from_m:           cross priv_mode_m, csrname, csraccesses;
    cp_ucsr_from_s:           cross priv_mode_s, csruname, csraccesses;
    cp_shadow :               cross priv_mode_m, shadow, csrw_prev, rs1_prev, csrr;
    cp_csr_satp:              cross priv_mode_s, satp, csrop, walking_ones_nonmode;
    cp_csr_insufficient_priv: cross priv_mode_s, csrr, csr_machine, nonzerord;
endgroup

function void s_sample(int hart, int issue, ins_t ins);
    S_scause_cg.sample(ins);
    S_sstatus_cg.sample(ins);
    S_sprivinst_cg.sample(ins);
    S_scsr_cg.sample(ins);
endfunction
