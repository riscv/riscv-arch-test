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

// Software check exceptions are supported for both Zicfilp and Zicfiss
`ifdef ZICFILP_SUPPORTED
    `define SOFTWARE_CHECK_SUPPORTED
`endif
`ifdef ZICFISS_SUPPORTED
    `ifndef SOFTWARE_CHECK_SUPPORTED
        `define SOFTWARE_CHECK_SUPPORTED
    `endif
`endif

covergroup S_scause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    scause: coverpoint ins.current.insn[31:20] {
        bins scause = {CSR_SCAUSE};
    }
    scause_interrupt : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins interrupt = {1};
    }
    scause_exception : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins exception = {0};
    }
    scause_exception_values: coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        // values are WLRL. Exclude reserved and custom and possibly unimplemented fields unless SS1P12 or higher is supported
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
        bins b_12_instruction_page_fault = {12};
        bins b_13_load_page_fault = {13};
        bins b_15_store_page_fault = {15};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            // Exception code is required to hold the values 0-31 in Ss1p12 or higher.
            bins b_10_ecall_vs = {10}; // only can be triggered in hardware if H supported but scause must be able to hold 0-31
            bins b_11_ecall_m = {11}; // never delegated to S mode but scause must be able to hold 0-31
            bins b_14_reserved = {14};
            bins b_16_double_trap = {16}; // never delegated to S mode
            bins b_17_reserved = {17};
            bins b_18_software_check = {18}; // only can be triggered in hardware if SOFTWARE_CHECK_SUPPORTED but scause must be able to hold 0-31
            bins b_19_hardware_error = {19}; // scause must be able to hold 0-31
            // These can only be triggered in hardware if H supported, but scause must be able to hold 0-31
            bins b_20_instr_guest_page_fault = {20};
            bins b_21_load_guest_page_fault = {21};
            bins b_22_virtual_instruction = {22};
            bins b_23_store_guest_page_fault = {23};
            bins b_31_24_custom[] = {[31:24]}; // scause must be able to hold 0-31
        `endif
        //bins b_47_32_reserved = {[47:32]};
        //bins b_63_48_custom = {[63:48]};
    }
    scause_interrupt_values: coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        // values are WLRL. Exclude reserved and custom fields unless SS1P12 or higher is supported
        bins b_1_supervisor_software = {1};
        bins b_3_machine_software = {3};
        bins b_5_supervisor_timer = {5};
        bins b_7_machine_timer = {7};
        bins b_9_supervisor_external = {9};
        bins b_11_machine_external = {11};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            // scause Exception Code required to hold the values 0-31
            bins b_0_reserved = {0};
            bins b_2_vs_software = {2};
            bins b_4_reserved = {4};
            bins b_6_vs_timer = {6};
            bins b_8_reserved = {8};
            bins b_10_vs_external = {10};
            bins b_12_supervisor_guest_external = {12};
            bins b_13_counter_overflow = {13};
            bins b_14_reserved = {14};
            bins b_15_reserved = {15};
            bins b_31_16_custom[] = {[31:16]}; // designated for platform use
        `endif
    }

    // main coverpoints
    cp_scause_write_exception: cross priv_mode_s, csrrw, scause, scause_exception_values, scause_exception; // CSR write of scause in S mode with interesting values
    cp_scause_write_interrupt: cross priv_mode_s, csrrw, scause, scause_interrupt_values, scause_interrupt; // CSR write of scause in S mode with interesting values

endgroup


covergroup S_sstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cp_sstatus_sd: coverpoint ins.current.rs1_val[`UDB_MXLEN-1]  {
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
        bins sstatus = {CSR_SSTATUS};
    }
    // main coverpoints
    cp_sstatus_sd_write: cross priv_mode_s, csrrw, sstatus, cp_sstatus_sd, cp_sstatus_fs, cp_sstatus_vs, cp_sstatus_xs;

    `ifdef S1P13P0_OR_LATER_SUPPORTED
        `ifdef UDB_MXLEN_64
            uxl_write_attempt: coverpoint ins.current.rs1_val[33:32] {
                bins attempt_1 = {2'b01};
                bins attempt_2 = {2'b10};
            }
            csrop: coverpoint ins.current.insn {
                wildcard bins csrrw = {CSRRW};
            }
             // main coverpoints
            cp_sxlen_ge_uxlen: cross priv_mode_s, csrop, sstatus, uxl_write_attempt;
        `endif // UDB_MXLEN_64
    `endif // S1P13P0_OR_LATER_SUPPORTED

endgroup

covergroup S_sprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    privinstrs: coverpoint ins.current.insn  {
        bins          ecall      = {ECALL};
        bins          ebreak     = {EBREAK};
        bins          mret       = {MRET};
        wildcard bins sfence_vma = {SFENCE_VMA};
    }
    sret: coverpoint ins.current.insn  {
        bins sret   = {SRET};
    }
    old_sstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
    }
    old_sstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] {
    }
    old_sstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0] {
    }
    // main coverpoints
    cp_sprivinst: cross priv_mode_s, privinstrs;
    cp_sret_s:    cross priv_mode_s, sret, old_sstatus_spp, old_sstatus_spie, old_sstatus_sie;
endgroup

covergroup S_scsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // walking_ones_nonmode: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
    //     `ifdef UDB_MXLEN_64
    //         bins b_1[] = { [0:`UDB_MXLEN-5] };
    //     `else
    //         bins b_1[] = { [0:`UDB_MXLEN-2] };
    //     `endif
    // }


    csrname : coverpoint ins.current.insn[31:20] {
        bins sstatus       = {CSR_SSTATUS};
        bins sie           = {CSR_SIE};
        // bins stvec         = {CSR_STVEC}; // warl field has complex write restrictions and is not easy to test
        bins  scounteren    = {CSR_SCOUNTEREN};
        bins sscratch      = {CSR_SSCRATCH};
        bins sepc          = {CSR_SEPC};
        // bins scause        = {CSR_SCAUSE}; // WLRL field; tested with cp_scause_write_*
        bins stval         = {CSR_STVAL};
        bins sip           = {CSR_SIP};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
          bins senvcfg       = {CSR_SENVCFG};
        `endif
    }
    csrwalk: coverpoint ins.current.insn[31:20] {
        bins sstatus       = {CSR_SSTATUS};
        bins sie           = {CSR_SIE};
        bins scounteren    = {CSR_SCOUNTEREN};
        bins sscratch      = {CSR_SSCRATCH};
        bins sip           = {CSR_SIP};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
          bins senvcfg     = {CSR_SENVCFG};
        `endif
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
        // counters tested in ZicntrS
    }
    // satp : coverpoint ins.current.insn[31:20] {
    //     bins satp          = {CSR_SATP};
    // }

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
        bins machine_1a[] = {[12'h700:12'h7A9]};
        // ignore mscontext at 0x7aa, which is accessible from S mode
        bins machine_1b[] = {[12'h7AB:12'h7FF]};
        bins machine_2[] = {[12'hB00:12'hBFF]};
        bins machine_3[] = {[12'hF00:12'hFFF]};
    }
    csr_sro: coverpoint ins.current.insn[31:20]  {
        bins sro[] = {[12'hC00:12'hEFF]};
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    csrw: coverpoint ins.current.insn  {
        wildcard bins csrw = {CSRRW};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }

    cp_scsr_access:           cross priv_mode_s, csrname, csraccesses;
    cp_scsrwalk:              cross priv_mode_s, csrwalk, csrop, walking_ones;
    cp_ucsr_from_s:           cross priv_mode_s, csruname, csraccesses;
    cp_csr_insufficient_priv: cross priv_mode_s, csrr, csr_machine, nonzerord;
    cp_csr_ro:                cross priv_mode_s, csrw, csr_sro;

// waived because behavior of other fields is UNSPECIFIED when satp.MODE=Bare
//    cp_csr_satp:              cross priv_mode_s, satp, csrop, walking_ones_nonmode;

endgroup

function void s_sample(int hart, int issue, ins_t ins);
    S_scause_cg.sample(ins);
    S_sstatus_cg.sample(ins);
    S_sprivinst_cg.sample(ins);
    S_scsr_cg.sample(ins);
endfunction
