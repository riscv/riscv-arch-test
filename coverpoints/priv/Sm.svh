///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SM
covergroup Sm_mcause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw_mcause: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b001101000010_?????_001_?????_1110011};  // csrrw to mcause
    }
    mcause_interrupt : coverpoint ins.current.rs1_val[XLEN-1] {
        bins interrupt = {1};
    }
    mcause_exception : coverpoint ins.current.rs1_val[XLEN-1] {
        bins exception = {0};
    }
    mcause_exception_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
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
    mcause_interrupt_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
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
    // This is Sm machine-mode testing, so all coverpoints are in Machine mode.
    cp_mcause_write_exception: cross csrrw_mcause, priv_mode_m, mcause_exception_values, mcause_exception; // CSR write of mcause in M mode with interesting values
    cp_mcause_write_interrupt: cross csrrw_mcause, priv_mode_m, mcause_interrupt_values, mcause_interrupt; // CSR write of mcause in M mode with interesting values
endgroup


covergroup Sm_mstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // SD COVERPOINTS
    // Cross-product of trying to write mstatus.SD, .FS, .XS, .VS
    cp_mstatus_sd: coverpoint ins.current.rs1_val[XLEN-1]  {
    }
    cp_mstatus_fs: coverpoint ins.current.rs1_val[14:13] {
    }
    cp_mstatus_vs: coverpoint ins.current.rs1_val[10:9] {
    }
    cp_mstatus_xs: coverpoint ins.current.rs1_val[16:15] {
    }
    csrrw_mstatus: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b001100000000_?????_001_?????_1110011};  // csrrw to mstatus
    }
    cp_mstatus_sd_write: cross priv_mode_m, csrrw_mstatus, cp_mstatus_sd, cp_mstatus_fs, cp_mstatus_vs, cp_mstatus_xs;
endgroup

covergroup Sm_mprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    privinstrs: coverpoint ins.current.insn  {
        bins ecall  = {32'h00000073};
        bins ebreak = {32'h00100073};
    }
    mret: coverpoint ins.current.insn  {
        bins mret   = {32'h30200073};
    }
    sret: coverpoint ins.current.insn  {
        bins sret   = {32'h10200073};
    }
    old_mstatus_tsr: coverpoint ins.prev.csr[12'h300][22] {
    }
    old_mstatus_mprv: coverpoint ins.prev.csr[12'h300][17] {
    }
    old_mstatus_mpp: coverpoint ins.prev.csr[12'h300][12:11] {
        bins M_mode = {2'b11};
    }
    old_mstatus_spp: coverpoint ins.prev.csr[12'h300][8] {
    }
    old_mstatus_mpie: coverpoint ins.prev.csr[12'h300][7] {
    }
    old_mstatus_mie: coverpoint ins.prev.csr[12'h300][3] {
    }
    old_mstatus_spie: coverpoint ins.prev.csr[12'h300][5] {
    }
    old_mstatus_sie: coverpoint ins.prev.csr[12'h300][1] {
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`XLEN-1] };
    }

    mcsrname_all : coverpoint ins.current.insn[31:20] { // extended set for access tests, including read-only CSRs
        bins mstatus  = {12'h300};
        bins misa     = {12'h301};
        bins medeleg  = {12'h302};
        bins mideleg  = {12'h303};
        bins mie      = {12'h304};
        bins mtvec    = {12'h305};
        bins mscratch = {12'h340};
        bins mepc     = {12'h341};
        bins mcause   = {12'h342};
        bins mtval    = {12'h343};
        bins mip      = {12'h344};
        bins menvcfg  = {12'h30A};
        bins mvendorid= {12'hF11};
        bins marchid  = {12'hF12};
        bins mimpid   = {12'hF13};
        bins mhartid  = {12'hF14};
        bins mconfigptr= {12'hF15};
        `ifdef MSECCFG_SUPPORTED // update this in two places when UDB gives a name to this parameter
            bins mseccfg  = {12'h747};
        `endif
        `ifdef XLEN32
            bins mstatush = {12'h310};
            // bins medelegh = {12'h312}; # in Sm1p13 only
            bins menvcfgh = {12'h31A};
            `ifdef MSECCFG_SUPPORTED // update this in two places when UDB gives a name to this parameter
                bins mseccfgh = {12'h757};
            `endif
        `endif
    }

    csraccesses : coverpoint {ins.current.rs1_val, ins.current.insn[14:12]} iff (ins.current.insn[6:0] == 7'b1110011) {
        `ifdef XLEN64
            bins csrrc_all = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_011};
            bins csrrw0    = {67'b00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000_001};
            bins csrrw1    = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_001};
            bins csrrs_all = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_010};
            bins csrr      = {67'b00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000_010};
        `else
            bins csrrc_all = {35'b11111111_11111111_11111111_11111111_011}; // csrc all ones
            bins csrrw0    = {35'b00000000_00000000_00000000_00000000_001}; // csrw all zeros
            bins csrrw1    = {35'b11111111_11111111_11111111_11111111_001}; // csrw all ones
            bins csrrs_all = {35'b11111111_11111111_11111111_11111111_010}; // csrs all ones
            bins csrr      = {35'b00000000_00000000_00000000_00000000_010}; // csrr
        `endif
    }

    mcsrname : coverpoint ins.current.insn[31:20] {
        bins mstatus  = {12'h300};
        bins misa     = {12'h301};
        bins medeleg  = {12'h302};
        bins mideleg  = {12'h303};
        bins mie      = {12'h304};
        bins mtvec    = {12'h305};
        bins mscratch = {12'h340};
        bins mepc     = {12'h341};
        bins mcause   = {12'h342};
        bins mtval    = {12'h343};
        bins mip      = {12'h344};
        bins menvcfg  = {12'h30A};
        `ifdef MSECCFG_SUPPORTED // update this in four places when UDB gives a name to this parameter
            bins mseccfg  = {12'h747};
        `endif
        `ifdef XLEN32
            bins mstatush = {12'h310};
            // bins medelegh = {12'h312}; // move this to Sm1p13 coverpoints
            bins menvcfgh = {12'h31A};
            `ifdef MSECCFG_SUPPORTED // update this in four places when UDB gives a name to this parameter
                bins mseccfgh = {12'h757};
            `endif
        `endif
    }
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    cp_mcsr_access: cross priv_mode_m, mcsrname_all, csraccesses;
    cp_mcsrwalk : cross priv_mode_m, mcsrname, csrop, walking_ones;
    cp_mprivinst: cross privinstrs, priv_mode_m;
    cp_mret: cross mret, priv_mode_m, old_mstatus_mpp, old_mstatus_mprv, old_mstatus_mpie, old_mstatus_mie;
    cp_sret: cross sret, priv_mode_m, old_mstatus_mprv, old_mstatus_spp, old_mstatus_spie, old_mstatus_sie, old_mstatus_tsr;
endgroup

function void sm_sample(int hart, int issue, ins_t ins);
    //if (ins.ins_str == "csrrw" || ins.ins_str == "csrrs" || ins.ins_str == "csrrc")
    //    $display("Smle: PC = %h (%s) rs1_val = %h", ins.current.pc_rdata,ins.current.disass, ins.current.rs1_val);
    Sm_mcause_cg.sample(ins);
    Sm_mstatus_cg.sample(ins);
    Sm_mprivinst_cg.sample(ins);
endfunction
