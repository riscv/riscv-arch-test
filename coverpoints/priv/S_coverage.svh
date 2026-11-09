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

// scause must hold every code 0-31 from Ss1p12; before that, only the codes of supported causes
`ifdef S1P12P0_OR_LATER_SUPPORTED
    `define SCAUSE_HOLDS_SOFTWARE_CHECK
    `define SCAUSE_HOLDS_COUNTER_OVERFLOW
`endif
`ifdef SOFTWARE_CHECK_SUPPORTED
    `ifndef SCAUSE_HOLDS_SOFTWARE_CHECK
        `define SCAUSE_HOLDS_SOFTWARE_CHECK
    `endif
`endif
`ifdef SSCOFPMF_SUPPORTED
    `ifndef SCAUSE_HOLDS_COUNTER_OVERFLOW
        `define SCAUSE_HOLDS_COUNTER_OVERFLOW
    `endif
`endif
`ifdef S1P12P0_OR_LATER_SUPPORTED
    `define SCAUSE_HOLDS_H_CAUSES
`endif
`ifdef H_SUPPORTED
    `ifndef SCAUSE_HOLDS_H_CAUSES
        `define SCAUSE_HOLDS_H_CAUSES
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
            bins b_11_ecall_m = {11}; // never delegated to S mode but scause must be able to hold 0-31
            bins b_14_reserved = {14};
            bins b_16_double_trap = {16}; // never delegated to S mode
            bins b_17_reserved = {17};
            bins b_19_hardware_error = {19}; // scause must be able to hold 0-31
            bins b_31_24_custom[] = {[24:31]}; // scause must be able to hold 0-31
        `endif
        `ifdef SCAUSE_HOLDS_SOFTWARE_CHECK
            bins b_18_software_check = {18}; // Zicfilp or Zicfiss, or any code 0-31 in Ss1p12 or higher
        `endif
        `ifdef SCAUSE_HOLDS_H_CAUSES
            // H, or any code 0-31 in Ss1p12 or higher
            bins b_10_ecall_vs = {10};
            bins b_20_instr_guest_page_fault = {20};
            bins b_21_load_guest_page_fault = {21};
            bins b_22_virtual_instruction = {22};
            bins b_23_store_guest_page_fault = {23};
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
            bins b_4_reserved = {4};
            bins b_8_reserved = {8};
            bins b_14_reserved = {14};
            bins b_15_reserved = {15};
            bins b_31_16_custom[] = {[16:31]}; // designated for platform use
        `endif
        `ifdef SCAUSE_HOLDS_COUNTER_OVERFLOW
            bins b_13_counter_overflow = {13}; // Sscofpmf, or any code 0-31 in Ss1p12 or higher
        `endif
        `ifdef SCAUSE_HOLDS_H_CAUSES
            // H, or any code 0-31 in Ss1p12 or higher
            bins b_2_vs_software = {2};
            bins b_6_vs_timer = {6};
            bins b_10_vs_external = {10};
            bins b_12_supervisor_guest_external = {12};
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
    old_sstatus_spp: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0] {
    }
    old_sstatus_spie: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spie")[0] {
    }
    old_sstatus_sie: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "sie")[0] {
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
        // counters tested in S_Zicntr
    }
    satp : coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
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

    // Real addresses are valid even when address translation is off, so these are not gated on
    // Sv* support (the walk coverpoints below are). The generator emits the csrw immediately
    // after `auipc xN, 0`, so the pc value written equals the csrw's pc - 4; the scratch value
    // is scratch + 0xA8, an offset chosen so no walk, zero, or all-ones pattern shares its low byte.
    stvec: coverpoint ins.current.insn[31:20] {
        bins stvec = {CSR_STVEC};
    }
    sepc: coverpoint ins.current.insn[31:20] {
        bins sepc = {CSR_SEPC};
    }
    stval: coverpoint ins.current.insn[31:20] {
        bins stval = {CSR_STVAL};
    }
    // stval must hold 0 and, when the illegal instruction encoding is reported in it, every ILEN-bit value
    stval_zero: coverpoint ins.current.rs1_val {
        bins zero = {0};
    }
    xaddr_pc: coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch: coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    `ifdef UDB_REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION
        stval_ilen_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:31] };
        }
        stval_ilen_ones: coverpoint ins.current.rs1_val {
            bins ones = {32'hFFFFFFFF};
        }
    `endif

    // Valid virtual address walks: stvec, sepc, and stval must hold every canonical virtual address.
    // Canonical addresses have bits XLEN-1:VALEN-1 equal, so bit VALEN-2 is the msb walked on its own
    // (31 for Sv32, where VALEN = XLEN).
    `ifdef SV57_SUPPORTED
        `define S_VADDR_WALK_MSB 55
    `elsif SV48_SUPPORTED
        `define S_VADDR_WALK_MSB 46
    `elsif SV39_SUPPORTED
        `define S_VADDR_WALK_MSB 37
    `elsif SV32_SUPPORTED
        `define S_VADDR_WALK_MSB 31
    `endif
    `ifdef S_VADDR_WALK_MSB
        // stvec: BASE holds the address with MODE = Direct, so bits 1:0 stay 0
        stvec_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [2:`S_VADDR_WALK_MSB] };
        }
        stvec_vaddr_walk0: coverpoint $clog2(~(ins.current.rs1_val | 3))
                           iff ($onehot(~(ins.current.rs1_val | 3))) {
            bins b_0[] = { [2:`S_VADDR_WALK_MSB] };
        }
        // sepc: bit 0 is always 0; bit 1 is 0 unless Zca allows 2-byte instruction alignment
        sepc_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`S_VADDR_WALK_MSB] };
        }
        sepc_vaddr_walk0: coverpoint $clog2(~(ins.current.rs1_val))
                            iff ($onehot(~(ins.current.rs1_val))) {
            bins b_0[] = { [0:`S_VADDR_WALK_MSB] };
        }
        // stval: any byte address is a valid virtual address
        stval_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`S_VADDR_WALK_MSB] };
        }
        stval_vaddr_walk0: coverpoint $clog2(~ins.current.rs1_val) iff ($onehot(~ins.current.rs1_val)) {
            bins b_0[] = { [0:`S_VADDR_WALK_MSB] };
        }

        cp_stvec_vaddr_walk1:     cross priv_mode_s, csrw, stvec, stvec_vaddr_walk1;
        cp_stvec_vaddr_walk0:     cross priv_mode_s, csrw, stvec, stvec_vaddr_walk0;
        cp_sepc_vaddr_walk1:      cross priv_mode_s, csrw, sepc, sepc_vaddr_walk1;
        cp_sepc_vaddr_walk0:      cross priv_mode_s, csrw, sepc, sepc_vaddr_walk0;
        cp_stval_vaddr_walk1:     cross priv_mode_s, csrw, stval, stval_vaddr_walk1;
        cp_stval_vaddr_walk0:     cross priv_mode_s, csrw, stval, stval_vaddr_walk0;
    `endif

    cp_scsr_access:           cross priv_mode_s, csrname, csraccesses;
    cp_satp:                  cross priv_mode_s, csrr, satp;
    cp_scsrwalk:              cross priv_mode_s, csrwalk, csrop, walking_ones;
    cp_ucsr_from_s:           cross priv_mode_s, csruname, csraccesses;
    cp_csr_insufficient_priv: cross priv_mode_s, csrr, csr_machine, nonzerord;
    cp_csr_ro:                cross priv_mode_s, csrw, csr_sro;
    cp_stvec_vaddr_pc:        cross priv_mode_s, csrw, stvec, xaddr_pc;
    cp_stvec_vaddr_scratch:   cross priv_mode_s, csrw, stvec, xaddr_scratch;
    cp_sepc_vaddr_pc:         cross priv_mode_s, csrw, sepc, xaddr_pc;
    cp_sepc_vaddr_scratch:    cross priv_mode_s, csrw, sepc, xaddr_scratch;
    cp_stval_vaddr_pc:        cross priv_mode_s, csrw, stval, xaddr_pc;
    cp_stval_vaddr_scratch:   cross priv_mode_s, csrw, stval, xaddr_scratch;
    cp_stval_zero:            cross priv_mode_s, csrw, stval, stval_zero;
    `ifdef UDB_REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION
        cp_stval_ilen_walk1:  cross priv_mode_s, csrw, stval, stval_ilen_walk1;
        cp_stval_ilen_ones:   cross priv_mode_s, csrw, stval, stval_ilen_ones;
    `endif
endgroup

// S_F, S_V and S_VF tests (S_F-NN.S, S_V_*-NN.S, S_VF-NN.S) are part of the S suite and run only
// when F, Zve32x or Zve32f is also supported. They parallel Sm_F, Sm_V and Sm_VF in Sm_coverage.svh,
// using sstatus in S-mode, and share their coverpoints through the general/RISCV_coverage_priv_*
// includes.
`ifdef F_SUPPORTED
covergroup S_F_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_f_coverpoints.svh"

    sstatus_FS: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "fs")[1:0] {
        bins off     = {2'b00};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins initial_state = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean   = {2'b10};
        `endif
        bins dirty   = {2'b11};
    }
    sstatus_FS_off_dirty: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }

    // main coverpoints
    cp_fcsr_access:           cross priv_mode_s, fcsrname, csraccesses, sstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with sstatus.FS
    cp_sstatus_FS_transition: cross priv_mode_s, deterministic_instrs, sstatus_FS;
    cp_sstatus_FS_transition_nondeterministic: cross priv_mode_s, nondeterministic_instrs, sstatus_FS_off_dirty;
endgroup
`endif

`ifdef ZVE32X_SUPPORTED
covergroup S_V_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_v_coverpoints.svh"

    // crosses of the shared vector coverpoints
    cp_vcsrrswc                 : cross priv_mode_s, vcsrs, csrops;
    cp_vcsrs_walking1s          : cross priv_mode_s, writable_vcsrs, csrw, walking_ones_rs1;
    cp_sew_lmul_vsetvl          : cross priv_mode_s, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(rs2_sew) intersect { 3'b000 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_sew_lmul_vset_i_vli      : cross priv_mode_s, vset_i_vli_instructions, vset_sew, vset_lmul {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(vset_sew) intersect { 3'b000 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_vill_vsetvl              : cross priv_mode_s, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal, rs2_sew_all_supported, rs2_lmul_8;
    cp_vill_vset_i_vli          : cross priv_mode_s, vset_i_vli_instructions, vtype_prev_vill_set, current_vset_sew_all_supported, current_vset_lmul_8;
    cp_vill_vsetvl_rs2_vill     : cross priv_mode_s, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal_no_msb, rs2_sew_all_supported, rs2_lmul_8, rs2_vill_set;
    cp_vsetvl_rs2_vill          : cross priv_mode_s, vsetvl_instruction, rs2_vill_set, rs2_sew_supported, rs2_lmul_1, rs2_vtype_legal_no_msb, vtype_prev_vill_clear;
    cp_vtype_vill_set_vl_0      : cross priv_mode_s, vsetvl_instruction, rs1_non_zero, rs2_vill_set, vl_nonzero;
    cp_vsetvl_i_rd_nx0_rs1_x0   : cross priv_mode_s, vsetvl_i_instructions, vl_not_max, rd_n0, rs1_x0, vtype_all_sew_supported, vtype_all_lmul_supported {
        // SEW > LMUL*ELEN sets vill=1 and forces vtype.vsew/vlmul to 0,
        // so these BEFORE-state (sew, lmul) pairs are architecturally unreachable.
        ignore_bins illegal_sew_lmul =
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.half))   ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.sixteen)   && binsof(vtype_all_lmul_supported.eighth));
    }
    cp_vsetvl_i_rd_x0_rs1_x0    : cross priv_mode_s, vsetvl_i_instructions, vl_nonzero, rd_x0, rs1_x0, vset_i_vli_vlmax_unchanged;
    cp_vsetvl_i_avl_eq_zero     : cross priv_mode_s, vsetvl_i_instructions, rs1_eq_zero;
    cp_vsetvl_i_avl_eq_vlmax    : cross priv_mode_s, vsetvl_i_instructions, rs1_eq_vlmax;
    cp_vsetvl_i_avl_lt_2x_vlmax : cross priv_mode_s, vsetvl_i_instructions, rs1_lt_2x_vlmax_gt_vlmax;
    cp_vsetvl_i_avl_eq_2x_vlmax : cross priv_mode_s, vsetvl_i_instructions, rs1_eq_2x_vlmax;
    cp_vsetvl_i_avl_gt_2x_vlmax : cross priv_mode_s, vsetvl_i_instructions, rs1_gt_2x_vlmax;
    cp_vsetivli_avl_edges       : cross priv_mode_s, vsetivli_instruction, vtype_all_sew_supported, imm5_edges, vtype_lmul_1;
    cp_vstart_out_of_bounds     : cross priv_mode_s, vstart_csr, csr_write, rs1_2_to_16;
    cp_vl_walking1s_sew_lmul    : cross priv_mode_s, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1 {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            // SEW > LMUL*ELEN sets vill; the tests skip these unless the DUT supports the extra fractional LMULs.
            // Encodings are {vsew, vlmul}. ELEN is at most 64, so ELEN>=128 pairs are never legal.
            ignore_bins illegal_sew_lmul = binsof(vsetivli_prev_sew_lmul) intersect {
                5'b01_101,  // e16, mf8
                5'b10_110,  // e32, mf4
                5'b10_101,  // e32, mf8
                5'b11_111,  // e64, mf2
                5'b11_110,  // e64, mf4
                5'b11_101   // e64, mf8
            };
            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 = binsof(vsetivli_prev_sew_lmul) intersect {
                    5'b00_101,  // e8, mf8
                    5'b01_110,  // e16, mf4
                    5'b10_111   // e32, mf2
                };
            `endif
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////
    // cp_sstatus_vs_*
    // tests sstatus ability to set clean and initial to dirty only when supposed to
    //////////////////////////////////////////////////////////////////////////////////

    // Initial and Clean only when MSTATUS_VS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    sstatus_vs_on : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "vs") {
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    sstatus_vs_inactive    : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "vs") {
        bins inactive = {0};
    }

    cp_sstatus_vs_set_dirty_arithmetic  : cross priv_mode_s, std_vec,        vector_vector_arithmetic_instruction,   sstatus_vs_on;
    cp_sstatus_vs_set_dirty_csr         : cross priv_mode_s, std_vec,        vsetvli_instruction,                    sstatus_vs_on;
    cp_sstatus_vs_set_dirty_vcsr        : cross priv_mode_s, vcsrs_writable, csrops,                                 sstatus_vs_on;

    cp_sstatus_vs_off_arithmetic        : cross priv_mode_s, sstatus_vs_inactive,     vector_vector_arithmetic_instruction iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 );
    cp_sstatus_vs_off_csr               : cross priv_mode_s, sstatus_vs_inactive,     vsetvli_instruction iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 );

endgroup
`endif

`ifdef ZVE32F_SUPPORTED
covergroup S_VF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_vf_coverpoints.svh"

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 &
                        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    // Initial and Clean only when MSTATUS_FS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    sstatus_fs_on : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "fs") {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    sstatus_fs_off : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "fs") {
        bins off = {0};
    }

    cp_vectorfp_sstatus_fs_state_affecting_register : cross priv_mode_s, std_vec, vfmv_f_s, sstatus_fs_on;
    cp_vectorfp_sstatus_fs_state_affecting_csr      : cross priv_mode_s, std_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_on, fflags_modified_after_clear;
    cp_vectorfp_sstatus_fs_state_nonaffecting       : cross priv_mode_s, std_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_on, vs1_zero, vs2_zero;
    cp_vectorfp_sstatus_fs_off                      : cross priv_mode_s, std_trap_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_off, vs1_zero, vs2_zero;

endgroup
`endif

`ifdef ZICNTR_SUPPORTED
covergroup S_Zicntr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // counter access in supervisor mode

    mcounteren_ones: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCOUNTEREN){
        bins ones = {32'b11111111111111111111111111111111};
    }
    mcounteren_zeros: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCOUNTEREN){
        bins zeros = {32'b0};
    }
    counters_scounteren: coverpoint {ins.current.insn[31:20], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCOUNTEREN)[31:0]} {
    `ifdef UDB_SCOUNTENABLE_EN_0
    bins cycle_enabled         = {44'b110000000000_00000000000000000000000000000001};
    `endif
    `ifdef UDB_SCOUNTENABLE_EN_1
    bins time_enabled          = {44'b110000000001_00000000000000000000000000000010};
    `endif
    `ifdef UDB_SCOUNTENABLE_EN_2
    bins instret_enabled       = {44'b110000000010_00000000000000000000000000000100};
    `endif
    `ifdef ZIHPM_SUPPORTED
      `ifdef UDB_HPM_COUNTER_EN_3
        `ifdef UDB_SCOUNTENABLE_EN_3
        bins hpmcounter3_enabled   = {44'b110000000011_00000000000000000000000000001000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_4
        `ifdef UDB_SCOUNTENABLE_EN_4
        bins hpmcounter4_enabled   = {44'b110000000100_00000000000000000000000000010000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_5
        `ifdef UDB_SCOUNTENABLE_EN_5
        bins hpmcounter5_enabled   = {44'b110000000101_00000000000000000000000000100000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_6
        `ifdef UDB_SCOUNTENABLE_EN_6
        bins hpmcounter6_enabled   = {44'b110000000110_00000000000000000000000001000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_7
        `ifdef UDB_SCOUNTENABLE_EN_7
        bins hpmcounter7_enabled   = {44'b110000000111_00000000000000000000000010000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_8
        `ifdef UDB_SCOUNTENABLE_EN_8
        bins hpmcounter8_enabled   = {44'b110000001000_00000000000000000000000100000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_9
        `ifdef UDB_SCOUNTENABLE_EN_9
        bins hpmcounter9_enabled   = {44'b110000001001_00000000000000000000001000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_10
        `ifdef UDB_SCOUNTENABLE_EN_10
        bins hpmcounter10_enabled  = {44'b110000001010_00000000000000000000010000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_11
        `ifdef UDB_SCOUNTENABLE_EN_11
        bins hpmcounter11_enabled  = {44'b110000001011_00000000000000000000100000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_12
        `ifdef UDB_SCOUNTENABLE_EN_12
        bins hpmcounter12_enabled  = {44'b110000001100_00000000000000000001000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_13
        `ifdef UDB_SCOUNTENABLE_EN_13
        bins hpmcounter13_enabled  = {44'b110000001101_00000000000000000010000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_14
        `ifdef UDB_SCOUNTENABLE_EN_14
        bins hpmcounter14_enabled  = {44'b110000001110_00000000000000000100000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_15
        `ifdef UDB_SCOUNTENABLE_EN_15
        bins hpmcounter15_enabled  = {44'b110000001111_00000000000000001000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_16
        `ifdef UDB_SCOUNTENABLE_EN_16
        bins hpmcounter16_enabled  = {44'b110000010000_00000000000000010000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_17
        `ifdef UDB_SCOUNTENABLE_EN_17
        bins hpmcounter17_enabled  = {44'b110000010001_00000000000000100000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_18
        `ifdef UDB_SCOUNTENABLE_EN_18
        bins hpmcounter18_enabled  = {44'b110000010010_00000000000001000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_19
        `ifdef UDB_SCOUNTENABLE_EN_19
        bins hpmcounter19_enabled  = {44'b110000010011_00000000000010000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_20
        `ifdef UDB_SCOUNTENABLE_EN_20
        bins hpmcounter20_enabled  = {44'b110000010100_00000000000100000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_21
        `ifdef UDB_SCOUNTENABLE_EN_21
        bins hpmcounter21_enabled  = {44'b110000010101_00000000001000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_22
        `ifdef UDB_SCOUNTENABLE_EN_22
        bins hpmcounter22_enabled  = {44'b110000010110_00000000010000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_23
        `ifdef UDB_SCOUNTENABLE_EN_23
        bins hpmcounter23_enabled  = {44'b110000010111_00000000100000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_24
        `ifdef UDB_SCOUNTENABLE_EN_24
        bins hpmcounter24_enabled  = {44'b110000011000_00000001000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_25
        `ifdef UDB_SCOUNTENABLE_EN_25
        bins hpmcounter25_enabled  = {44'b110000011001_00000010000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_26
        `ifdef UDB_SCOUNTENABLE_EN_26
        bins hpmcounter26_enabled  = {44'b110000011010_00000100000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_27
        `ifdef UDB_SCOUNTENABLE_EN_27
        bins hpmcounter27_enabled  = {44'b110000011011_00001000000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_28
        `ifdef UDB_SCOUNTENABLE_EN_28
        bins hpmcounter28_enabled  = {44'b110000011100_00010000000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_29
        `ifdef UDB_SCOUNTENABLE_EN_29
        bins hpmcounter29_enabled  = {44'b110000011101_00100000000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_30
        `ifdef UDB_SCOUNTENABLE_EN_30
        bins hpmcounter30_enabled  = {44'b110000011110_01000000000000000000000000000000};
        `endif
      `endif
      `ifdef UDB_HPM_COUNTER_EN_31
        `ifdef UDB_SCOUNTENABLE_EN_31
        bins hpmcounter31_enabled  = {44'b110000011111_10000000000000000000000000000000};
        `endif
      `endif
    `endif

    bins cycle_disabled         = {44'b110000000000_11111111111111111111111111111110};
    bins time_disabled          = {44'b110000000001_11111111111111111111111111111101};
    bins instret_disabled       = {44'b110000000010_11111111111111111111111111111011};
    `ifdef ZIHPM_SUPPORTED
      `ifdef UDB_HPM_COUNTER_EN_3
        bins hpmcounter3_disabled   = {44'b110000000011_11111111111111111111111111110111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_4
        bins hpmcounter4_disabled   = {44'b110000000100_11111111111111111111111111101111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_5
        bins hpmcounter5_disabled   = {44'b110000000101_11111111111111111111111111011111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_6
        bins hpmcounter6_disabled   = {44'b110000000110_11111111111111111111111110111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_7
        bins hpmcounter7_disabled   = {44'b110000000111_11111111111111111111111101111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_8
        bins hpmcounter8_disabled   = {44'b110000001000_11111111111111111111111011111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_9
        bins hpmcounter9_disabled   = {44'b110000001001_11111111111111111111110111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_10
        bins hpmcounter10_disabled  = {44'b110000001010_11111111111111111111101111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_11
        bins hpmcounter11_disabled  = {44'b110000001011_11111111111111111111011111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_12
        bins hpmcounter12_disabled  = {44'b110000001100_11111111111111111110111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_13
        bins hpmcounter13_disabled  = {44'b110000001101_11111111111111111101111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_14
        bins hpmcounter14_disabled  = {44'b110000001110_11111111111111111011111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_15
        bins hpmcounter15_disabled  = {44'b110000001111_11111111111111110111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_16
        bins hpmcounter16_disabled  = {44'b110000010000_11111111111111101111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_17
        bins hpmcounter17_disabled  = {44'b110000010001_11111111111111011111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_18
        bins hpmcounter18_disabled  = {44'b110000010010_11111111111110111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_19
        bins hpmcounter19_disabled  = {44'b110000010011_11111111111101111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_20
        bins hpmcounter20_disabled  = {44'b110000010100_11111111111011111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_21
        bins hpmcounter21_disabled  = {44'b110000010101_11111111110111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_22
        bins hpmcounter22_disabled  = {44'b110000010110_11111111101111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_23
        bins hpmcounter23_disabled  = {44'b110000010111_11111111011111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_24
        bins hpmcounter24_disabled  = {44'b110000011000_11111110111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_25
        bins hpmcounter25_disabled  = {44'b110000011001_11111101111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_26
        bins hpmcounter26_disabled  = {44'b110000011010_11111011111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_27
        bins hpmcounter27_disabled  = {44'b110000011011_11110111111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_28
        bins hpmcounter28_disabled  = {44'b110000011100_11101111111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_29
        bins hpmcounter29_disabled  = {44'b110000011101_11011111111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_30
        bins hpmcounter30_disabled  = {44'b110000011110_10111111111111111111111111111111};
      `endif
      `ifdef UDB_HPM_COUNTER_EN_31
        bins hpmcounter31_disabled  = {44'b110000011111_01111111111111111111111111111111};
      `endif
    `endif

    `ifdef UDB_MXLEN_32
        `ifdef UDB_SCOUNTENABLE_EN_0
        bins cycleh_enabled         = {44'b110010000000_00000000000000000000000000000001};
        `endif
        `ifdef UDB_SCOUNTENABLE_EN_1
        bins timeh_enabled          = {44'b110010000001_00000000000000000000000000000010};
        `endif
        `ifdef UDB_SCOUNTENABLE_EN_2
        bins instreth_enabled       = {44'b110010000010_00000000000000000000000000000100};
        `endif
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            `ifdef UDB_SCOUNTENABLE_EN_3
            bins hpmcounter3h_enabled   = {44'b110010000011_00000000000000000000000000001000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            `ifdef UDB_SCOUNTENABLE_EN_4
            bins hpmcounter4h_enabled   = {44'b110010000100_00000000000000000000000000010000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            `ifdef UDB_SCOUNTENABLE_EN_5
            bins hpmcounter5h_enabled   = {44'b110010000101_00000000000000000000000000100000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            `ifdef UDB_SCOUNTENABLE_EN_6
            bins hpmcounter6h_enabled   = {44'b110010000110_00000000000000000000000001000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            `ifdef UDB_SCOUNTENABLE_EN_7
            bins hpmcounter7h_enabled   = {44'b110010000111_00000000000000000000000010000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            `ifdef UDB_SCOUNTENABLE_EN_8
            bins hpmcounter8h_enabled   = {44'b110010001000_00000000000000000000000100000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            `ifdef UDB_SCOUNTENABLE_EN_9
            bins hpmcounter9h_enabled   = {44'b110010001001_00000000000000000000001000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            `ifdef UDB_SCOUNTENABLE_EN_10
            bins hpmcounter10h_enabled  = {44'b110010001010_00000000000000000000010000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            `ifdef UDB_SCOUNTENABLE_EN_11
            bins hpmcounter11h_enabled  = {44'b110010001011_00000000000000000000100000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            `ifdef UDB_SCOUNTENABLE_EN_12
            bins hpmcounter12h_enabled  = {44'b110010001100_00000000000000000001000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            `ifdef UDB_SCOUNTENABLE_EN_13
            bins hpmcounter13h_enabled  = {44'b110010001101_00000000000000000010000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            `ifdef UDB_SCOUNTENABLE_EN_14
            bins hpmcounter14h_enabled  = {44'b110010001110_00000000000000000100000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            `ifdef UDB_SCOUNTENABLE_EN_15
            bins hpmcounter15h_enabled  = {44'b110010001111_00000000000000001000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            `ifdef UDB_SCOUNTENABLE_EN_16
            bins hpmcounter16h_enabled  = {44'b110010010000_00000000000000010000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            `ifdef UDB_SCOUNTENABLE_EN_17
            bins hpmcounter17h_enabled  = {44'b110010010001_00000000000000100000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            `ifdef UDB_SCOUNTENABLE_EN_18
            bins hpmcounter18h_enabled  = {44'b110010010010_00000000000001000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            `ifdef UDB_SCOUNTENABLE_EN_19
            bins hpmcounter19h_enabled  = {44'b110010010011_00000000000010000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            `ifdef UDB_SCOUNTENABLE_EN_20
            bins hpmcounter20h_enabled  = {44'b110010010100_00000000000100000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            `ifdef UDB_SCOUNTENABLE_EN_21
            bins hpmcounter21h_enabled  = {44'b110010010101_00000000001000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            `ifdef UDB_SCOUNTENABLE_EN_22
            bins hpmcounter22h_enabled  = {44'b110010010110_00000000010000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            `ifdef UDB_SCOUNTENABLE_EN_23
            bins hpmcounter23h_enabled  = {44'b110010010111_00000000100000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            `ifdef UDB_SCOUNTENABLE_EN_24
            bins hpmcounter24h_enabled  = {44'b110010011000_00000001000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            `ifdef UDB_SCOUNTENABLE_EN_25
            bins hpmcounter25h_enabled  = {44'b110010011001_00000010000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            `ifdef UDB_SCOUNTENABLE_EN_26
            bins hpmcounter26h_enabled  = {44'b110010011010_00000100000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            `ifdef UDB_SCOUNTENABLE_EN_27
            bins hpmcounter27h_enabled  = {44'b110010011011_00001000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            `ifdef UDB_SCOUNTENABLE_EN_28
            bins hpmcounter28h_enabled  = {44'b110010011100_00010000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            `ifdef UDB_SCOUNTENABLE_EN_29
            bins hpmcounter29h_enabled  = {44'b110010011101_00100000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            `ifdef UDB_SCOUNTENABLE_EN_30
            bins hpmcounter30h_enabled  = {44'b110010011110_01000000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            `ifdef UDB_SCOUNTENABLE_EN_31
            bins hpmcounter31h_enabled  = {44'b110010011111_10000000000000000000000000000000};
            `endif
          `endif
        `endif

        bins cycleh_disabled         = {44'b110010000000_11111111111111111111111111111110};
        bins timeh_disabled          = {44'b110010000001_11111111111111111111111111111101};
        bins instreth_disabled       = {44'b110010000010_11111111111111111111111111111011};
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3h_disabled   = {44'b110010000011_11111111111111111111111111110111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4h_disabled   = {44'b110010000100_11111111111111111111111111101111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5h_disabled   = {44'b110010000101_11111111111111111111111111011111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6h_disabled   = {44'b110010000110_11111111111111111111111110111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7h_disabled   = {44'b110010000111_11111111111111111111111101111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8h_disabled   = {44'b110010001000_11111111111111111111111011111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9h_disabled   = {44'b110010001001_11111111111111111111110111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10h_disabled  = {44'b110010001010_11111111111111111111101111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11h_disabled  = {44'b110010001011_11111111111111111111011111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12h_disabled  = {44'b110010001100_11111111111111111110111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13h_disabled  = {44'b110010001101_11111111111111111101111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14h_disabled  = {44'b110010001110_11111111111111111011111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15h_disabled  = {44'b110010001111_11111111111111110111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16h_disabled  = {44'b110010010000_11111111111111101111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17h_disabled  = {44'b110010010001_11111111111111011111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18h_disabled  = {44'b110010010010_11111111111110111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19h_disabled  = {44'b110010010011_11111111111101111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20h_disabled  = {44'b110010010100_11111111111011111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21h_disabled  = {44'b110010010101_11111111110111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22h_disabled  = {44'b110010010110_11111111101111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23h_disabled  = {44'b110010010111_11111111011111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24h_disabled  = {44'b110010011000_11111110111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25h_disabled  = {44'b110010011001_11111101111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26h_disabled  = {44'b110010011010_11111011111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27h_disabled  = {44'b110010011011_11110111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28h_disabled  = {44'b110010011100_11101111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29h_disabled  = {44'b110010011101_11011111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30h_disabled  = {44'b110010011110_10111111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31h_disabled  = {44'b110010011111_01111111111111111111111111111111};
          `endif
        `endif
    `endif
}
    counters_mcounteren: coverpoint {ins.current.insn[31:20], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCOUNTEREN)[31:0] } {
        `ifdef UDB_MCOUNTENABLE_EN_0
        bins cycle_enabled         = {44'b110000000000_00000000000000000000000000000001};
        `endif
        `ifdef UDB_MCOUNTENABLE_EN_1
        bins time_enabled          = {44'b110000000001_00000000000000000000000000000010};
        `endif
        `ifdef UDB_MCOUNTENABLE_EN_2
        bins instret_enabled       = {44'b110000000010_00000000000000000000000000000100};
        `endif
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            `ifdef UDB_MCOUNTENABLE_EN_3
            bins hpmcounter3_enabled   = {44'b110000000011_00000000000000000000000000001000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            `ifdef UDB_MCOUNTENABLE_EN_4
            bins hpmcounter4_enabled   = {44'b110000000100_00000000000000000000000000010000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            `ifdef UDB_MCOUNTENABLE_EN_5
            bins hpmcounter5_enabled   = {44'b110000000101_00000000000000000000000000100000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            `ifdef UDB_MCOUNTENABLE_EN_6
            bins hpmcounter6_enabled   = {44'b110000000110_00000000000000000000000001000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            `ifdef UDB_MCOUNTENABLE_EN_7
            bins hpmcounter7_enabled   = {44'b110000000111_00000000000000000000000010000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            `ifdef UDB_MCOUNTENABLE_EN_8
            bins hpmcounter8_enabled   = {44'b110000001000_00000000000000000000000100000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            `ifdef UDB_MCOUNTENABLE_EN_9
            bins hpmcounter9_enabled   = {44'b110000001001_00000000000000000000001000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            `ifdef UDB_MCOUNTENABLE_EN_10
            bins hpmcounter10_enabled  = {44'b110000001010_00000000000000000000010000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            `ifdef UDB_MCOUNTENABLE_EN_11
            bins hpmcounter11_enabled  = {44'b110000001011_00000000000000000000100000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            `ifdef UDB_MCOUNTENABLE_EN_12
            bins hpmcounter12_enabled  = {44'b110000001100_00000000000000000001000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            `ifdef UDB_MCOUNTENABLE_EN_13
            bins hpmcounter13_enabled  = {44'b110000001101_00000000000000000010000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            `ifdef UDB_MCOUNTENABLE_EN_14
            bins hpmcounter14_enabled  = {44'b110000001110_00000000000000000100000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            `ifdef UDB_MCOUNTENABLE_EN_15
            bins hpmcounter15_enabled  = {44'b110000001111_00000000000000001000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            `ifdef UDB_MCOUNTENABLE_EN_16
            bins hpmcounter16_enabled  = {44'b110000010000_00000000000000010000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            `ifdef UDB_MCOUNTENABLE_EN_17
            bins hpmcounter17_enabled  = {44'b110000010001_00000000000000100000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            `ifdef UDB_MCOUNTENABLE_EN_18
            bins hpmcounter18_enabled  = {44'b110000010010_00000000000001000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            `ifdef UDB_MCOUNTENABLE_EN_19
            bins hpmcounter19_enabled  = {44'b110000010011_00000000000010000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            `ifdef UDB_MCOUNTENABLE_EN_20
            bins hpmcounter20_enabled  = {44'b110000010100_00000000000100000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            `ifdef UDB_MCOUNTENABLE_EN_21
            bins hpmcounter21_enabled  = {44'b110000010101_00000000001000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            `ifdef UDB_MCOUNTENABLE_EN_22
            bins hpmcounter22_enabled  = {44'b110000010110_00000000010000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            `ifdef UDB_MCOUNTENABLE_EN_23
            bins hpmcounter23_enabled  = {44'b110000010111_00000000100000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            `ifdef UDB_MCOUNTENABLE_EN_24
            bins hpmcounter24_enabled  = {44'b110000011000_00000001000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            `ifdef UDB_MCOUNTENABLE_EN_25
            bins hpmcounter25_enabled  = {44'b110000011001_00000010000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            `ifdef UDB_MCOUNTENABLE_EN_26
            bins hpmcounter26_enabled  = {44'b110000011010_00000100000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            `ifdef UDB_MCOUNTENABLE_EN_27
            bins hpmcounter27_enabled  = {44'b110000011011_00001000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            `ifdef UDB_MCOUNTENABLE_EN_28
            bins hpmcounter28_enabled  = {44'b110000011100_00010000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            `ifdef UDB_MCOUNTENABLE_EN_29
            bins hpmcounter29_enabled  = {44'b110000011101_00100000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            `ifdef UDB_MCOUNTENABLE_EN_30
            bins hpmcounter30_enabled  = {44'b110000011110_01000000000000000000000000000000};
            `endif
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            `ifdef UDB_MCOUNTENABLE_EN_31
            bins hpmcounter31_enabled  = {44'b110000011111_10000000000000000000000000000000};
            `endif
          `endif
        `endif

        bins cycle_disabled         = {44'b110000000000_11111111111111111111111111111110};
        bins time_disabled          = {44'b110000000001_11111111111111111111111111111101};
        bins instret_disabled       = {44'b110000000010_11111111111111111111111111111011};
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3_disabled   = {44'b110000000011_11111111111111111111111111110111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4_disabled   = {44'b110000000100_11111111111111111111111111101111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5_disabled   = {44'b110000000101_11111111111111111111111111011111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6_disabled   = {44'b110000000110_11111111111111111111111110111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7_disabled   = {44'b110000000111_11111111111111111111111101111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8_disabled   = {44'b110000001000_11111111111111111111111011111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9_disabled   = {44'b110000001001_11111111111111111111110111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10_disabled  = {44'b110000001010_11111111111111111111101111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11_disabled  = {44'b110000001011_11111111111111111111011111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12_disabled  = {44'b110000001100_11111111111111111110111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13_disabled  = {44'b110000001101_11111111111111111101111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14_disabled  = {44'b110000001110_11111111111111111011111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15_disabled  = {44'b110000001111_11111111111111110111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16_disabled  = {44'b110000010000_11111111111111101111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17_disabled  = {44'b110000010001_11111111111111011111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18_disabled  = {44'b110000010010_11111111111110111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19_disabled  = {44'b110000010011_11111111111101111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20_disabled  = {44'b110000010100_11111111111011111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21_disabled  = {44'b110000010101_11111111110111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22_disabled  = {44'b110000010110_11111111101111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23_disabled  = {44'b110000010111_11111111011111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24_disabled  = {44'b110000011000_11111110111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25_disabled  = {44'b110000011001_11111101111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26_disabled  = {44'b110000011010_11111011111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27_disabled  = {44'b110000011011_11110111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28_disabled  = {44'b110000011100_11101111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29_disabled  = {44'b110000011101_11011111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30_disabled  = {44'b110000011110_10111111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31_disabled  = {44'b110000011111_01111111111111111111111111111111};
          `endif
        `endif

        `ifdef UDB_MXLEN_32
            `ifdef UDB_MCOUNTENABLE_EN_0
            bins cycleh_enabled         = {44'b110010000000_00000000000000000000000000000001};
            `endif
            `ifdef UDB_MCOUNTENABLE_EN_1
            bins timeh_enabled          = {44'b110010000001_00000000000000000000000000000010};
            `endif
            `ifdef UDB_MCOUNTENABLE_EN_2
            bins instreth_enabled       = {44'b110010000010_00000000000000000000000000000100};
            `endif
            `ifdef ZIHPM_SUPPORTED
              `ifdef UDB_HPM_COUNTER_EN_3
                `ifdef UDB_MCOUNTENABLE_EN_3
                bins hpmcounter3h_enabled   = {44'b110010000011_00000000000000000000000000001000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_4
                `ifdef UDB_MCOUNTENABLE_EN_4
                bins hpmcounter4h_enabled   = {44'b110010000100_00000000000000000000000000010000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_5
                `ifdef UDB_MCOUNTENABLE_EN_5
                bins hpmcounter5h_enabled   = {44'b110010000101_00000000000000000000000000100000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_6
                `ifdef UDB_MCOUNTENABLE_EN_6
                bins hpmcounter6h_enabled   = {44'b110010000110_00000000000000000000000001000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_7
                `ifdef UDB_MCOUNTENABLE_EN_7
                bins hpmcounter7h_enabled   = {44'b110010000111_00000000000000000000000010000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_8
                `ifdef UDB_MCOUNTENABLE_EN_8
                bins hpmcounter8h_enabled   = {44'b110010001000_00000000000000000000000100000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_9
                `ifdef UDB_MCOUNTENABLE_EN_9
                bins hpmcounter9h_enabled   = {44'b110010001001_00000000000000000000001000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_10
                `ifdef UDB_MCOUNTENABLE_EN_10
                bins hpmcounter10h_enabled  = {44'b110010001010_00000000000000000000010000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_11
                `ifdef UDB_MCOUNTENABLE_EN_11
                bins hpmcounter11h_enabled  = {44'b110010001011_00000000000000000000100000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_12
                `ifdef UDB_MCOUNTENABLE_EN_12
                bins hpmcounter12h_enabled  = {44'b110010001100_00000000000000000001000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_13
                `ifdef UDB_MCOUNTENABLE_EN_13
                bins hpmcounter13h_enabled  = {44'b110010001101_00000000000000000010000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_14
                `ifdef UDB_MCOUNTENABLE_EN_14
                bins hpmcounter14h_enabled  = {44'b110010001110_00000000000000000100000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_15
                `ifdef UDB_MCOUNTENABLE_EN_15
                bins hpmcounter15h_enabled  = {44'b110010001111_00000000000000001000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_16
                `ifdef UDB_MCOUNTENABLE_EN_16
                bins hpmcounter16h_enabled  = {44'b110010010000_00000000000000010000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_17
                `ifdef UDB_MCOUNTENABLE_EN_17
                bins hpmcounter17h_enabled  = {44'b110010010001_00000000000000100000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_18
                `ifdef UDB_MCOUNTENABLE_EN_18
                bins hpmcounter18h_enabled  = {44'b110010010010_00000000000001000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_19
                `ifdef UDB_MCOUNTENABLE_EN_19
                bins hpmcounter19h_enabled  = {44'b110010010011_00000000000010000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_20
                `ifdef UDB_MCOUNTENABLE_EN_20
                bins hpmcounter20h_enabled  = {44'b110010010100_00000000000100000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_21
                `ifdef UDB_MCOUNTENABLE_EN_21
                bins hpmcounter21h_enabled  = {44'b110010010101_00000000001000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_22
                `ifdef UDB_MCOUNTENABLE_EN_22
                bins hpmcounter22h_enabled  = {44'b110010010110_00000000010000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_23
                `ifdef UDB_MCOUNTENABLE_EN_23
                bins hpmcounter23h_enabled  = {44'b110010010111_00000000100000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_24
                `ifdef UDB_MCOUNTENABLE_EN_24
                bins hpmcounter24h_enabled  = {44'b110010011000_00000001000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_25
                `ifdef UDB_MCOUNTENABLE_EN_25
                bins hpmcounter25h_enabled  = {44'b110010011001_00000010000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_26
                `ifdef UDB_MCOUNTENABLE_EN_26
                bins hpmcounter26h_enabled  = {44'b110010011010_00000100000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_27
                `ifdef UDB_MCOUNTENABLE_EN_27
                bins hpmcounter27h_enabled  = {44'b110010011011_00001000000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_28
                `ifdef UDB_MCOUNTENABLE_EN_28
                bins hpmcounter28h_enabled  = {44'b110010011100_00010000000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_29
                `ifdef UDB_MCOUNTENABLE_EN_29
                bins hpmcounter29h_enabled  = {44'b110010011101_00100000000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_30
                `ifdef UDB_MCOUNTENABLE_EN_30
                bins hpmcounter30h_enabled  = {44'b110010011110_01000000000000000000000000000000};
                `endif
              `endif
              `ifdef UDB_HPM_COUNTER_EN_31
                `ifdef UDB_MCOUNTENABLE_EN_31
                bins hpmcounter31h_enabled  = {44'b110010011111_10000000000000000000000000000000};
                `endif
              `endif
            `endif

            bins cycleh_disabled         = {44'b110010000000_11111111111111111111111111111110};
            bins timeh_disabled          = {44'b110010000001_11111111111111111111111111111101};
            bins instreth_disabled       = {44'b110010000010_11111111111111111111111111111011};
            `ifdef ZIHPM_SUPPORTED
              `ifdef UDB_HPM_COUNTER_EN_3
                bins hpmcounter3h_disabled   = {44'b110010000011_11111111111111111111111111110111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_4
                bins hpmcounter4h_disabled   = {44'b110010000100_11111111111111111111111111101111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_5
                bins hpmcounter5h_disabled   = {44'b110010000101_11111111111111111111111111011111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_6
                bins hpmcounter6h_disabled   = {44'b110010000110_11111111111111111111111110111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_7
                bins hpmcounter7h_disabled   = {44'b110010000111_11111111111111111111111101111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_8
                bins hpmcounter8h_disabled   = {44'b110010001000_11111111111111111111111011111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_9
                bins hpmcounter9h_disabled   = {44'b110010001001_11111111111111111111110111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_10
                bins hpmcounter10h_disabled  = {44'b110010001010_11111111111111111111101111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_11
                bins hpmcounter11h_disabled  = {44'b110010001011_11111111111111111111011111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_12
                bins hpmcounter12h_disabled  = {44'b110010001100_11111111111111111110111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_13
                bins hpmcounter13h_disabled  = {44'b110010001101_11111111111111111101111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_14
                bins hpmcounter14h_disabled  = {44'b110010001110_11111111111111111011111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_15
                bins hpmcounter15h_disabled  = {44'b110010001111_11111111111111110111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_16
                bins hpmcounter16h_disabled  = {44'b110010010000_11111111111111101111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_17
                bins hpmcounter17h_disabled  = {44'b110010010001_11111111111111011111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_18
                bins hpmcounter18h_disabled  = {44'b110010010010_11111111111110111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_19
                bins hpmcounter19h_disabled  = {44'b110010010011_11111111111101111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_20
                bins hpmcounter20h_disabled  = {44'b110010010100_11111111111011111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_21
                bins hpmcounter21h_disabled  = {44'b110010010101_11111111110111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_22
                bins hpmcounter22h_disabled  = {44'b110010010110_11111111101111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_23
                bins hpmcounter23h_disabled  = {44'b110010010111_11111111011111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_24
                bins hpmcounter24h_disabled  = {44'b110010011000_11111110111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_25
                bins hpmcounter25h_disabled  = {44'b110010011001_11111101111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_26
                bins hpmcounter26h_disabled  = {44'b110010011010_11111011111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_27
                bins hpmcounter27h_disabled  = {44'b110010011011_11110111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_28
                bins hpmcounter28h_disabled  = {44'b110010011100_11101111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_29
                bins hpmcounter29h_disabled  = {44'b110010011101_11011111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_30
                bins hpmcounter30h_disabled  = {44'b110010011110_10111111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_31
                bins hpmcounter31h_disabled  = {44'b110010011111_01111111111111111111111111111111};
              `endif
            `endif
        `endif
    }
    csraccess: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }

    // main coverpoints
    cp_mcounteren_access_s: cross csraccess, counters_mcounteren, priv_mode_s;
    cp_scounteren_access_s: cross csraccess, counters_scounteren, mcounteren_ones, priv_mode_s;
    cp_scounteren_access_u: cross csraccess, counters_scounteren, mcounteren_ones, priv_mode_u;
    // This cross requires equal M/S counter enables. An S read-only-zero
    // bit cannot match the corresponding M enabled bin.
    `ifdef UDB_MCOUNTENABLE_EN_0
    `ifndef UDB_SCOUNTENABLE_EN_0
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `ifdef UDB_MCOUNTENABLE_EN_1
    `ifndef UDB_SCOUNTENABLE_EN_1
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `ifdef UDB_MCOUNTENABLE_EN_2
    `ifndef UDB_SCOUNTENABLE_EN_2
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_3
    `ifdef UDB_MCOUNTENABLE_EN_3
    `ifndef UDB_SCOUNTENABLE_EN_3
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_4
    `ifdef UDB_MCOUNTENABLE_EN_4
    `ifndef UDB_SCOUNTENABLE_EN_4
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_5
    `ifdef UDB_MCOUNTENABLE_EN_5
    `ifndef UDB_SCOUNTENABLE_EN_5
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_6
    `ifdef UDB_MCOUNTENABLE_EN_6
    `ifndef UDB_SCOUNTENABLE_EN_6
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_7
    `ifdef UDB_MCOUNTENABLE_EN_7
    `ifndef UDB_SCOUNTENABLE_EN_7
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_8
    `ifdef UDB_MCOUNTENABLE_EN_8
    `ifndef UDB_SCOUNTENABLE_EN_8
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_9
    `ifdef UDB_MCOUNTENABLE_EN_9
    `ifndef UDB_SCOUNTENABLE_EN_9
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_10
    `ifdef UDB_MCOUNTENABLE_EN_10
    `ifndef UDB_SCOUNTENABLE_EN_10
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_11
    `ifdef UDB_MCOUNTENABLE_EN_11
    `ifndef UDB_SCOUNTENABLE_EN_11
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_12
    `ifdef UDB_MCOUNTENABLE_EN_12
    `ifndef UDB_SCOUNTENABLE_EN_12
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_13
    `ifdef UDB_MCOUNTENABLE_EN_13
    `ifndef UDB_SCOUNTENABLE_EN_13
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_14
    `ifdef UDB_MCOUNTENABLE_EN_14
    `ifndef UDB_SCOUNTENABLE_EN_14
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_15
    `ifdef UDB_MCOUNTENABLE_EN_15
    `ifndef UDB_SCOUNTENABLE_EN_15
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_16
    `ifdef UDB_MCOUNTENABLE_EN_16
    `ifndef UDB_SCOUNTENABLE_EN_16
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_17
    `ifdef UDB_MCOUNTENABLE_EN_17
    `ifndef UDB_SCOUNTENABLE_EN_17
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_18
    `ifdef UDB_MCOUNTENABLE_EN_18
    `ifndef UDB_SCOUNTENABLE_EN_18
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_19
    `ifdef UDB_MCOUNTENABLE_EN_19
    `ifndef UDB_SCOUNTENABLE_EN_19
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_20
    `ifdef UDB_MCOUNTENABLE_EN_20
    `ifndef UDB_SCOUNTENABLE_EN_20
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_21
    `ifdef UDB_MCOUNTENABLE_EN_21
    `ifndef UDB_SCOUNTENABLE_EN_21
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_22
    `ifdef UDB_MCOUNTENABLE_EN_22
    `ifndef UDB_SCOUNTENABLE_EN_22
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_23
    `ifdef UDB_MCOUNTENABLE_EN_23
    `ifndef UDB_SCOUNTENABLE_EN_23
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_24
    `ifdef UDB_MCOUNTENABLE_EN_24
    `ifndef UDB_SCOUNTENABLE_EN_24
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_25
    `ifdef UDB_MCOUNTENABLE_EN_25
    `ifndef UDB_SCOUNTENABLE_EN_25
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_26
    `ifdef UDB_MCOUNTENABLE_EN_26
    `ifndef UDB_SCOUNTENABLE_EN_26
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_27
    `ifdef UDB_MCOUNTENABLE_EN_27
    `ifndef UDB_SCOUNTENABLE_EN_27
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_28
    `ifdef UDB_MCOUNTENABLE_EN_28
    `ifndef UDB_SCOUNTENABLE_EN_28
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_29
    `ifdef UDB_MCOUNTENABLE_EN_29
    `ifndef UDB_SCOUNTENABLE_EN_29
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_30
    `ifdef UDB_MCOUNTENABLE_EN_30
    `ifndef UDB_SCOUNTENABLE_EN_30
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_31
    `ifdef UDB_MCOUNTENABLE_EN_31
    `ifndef UDB_SCOUNTENABLE_EN_31
        `define S_ZICNTR_NEEDS_MSC_EN_FILTER
    `endif
    `endif
    `endif
    `ifdef S_ZICNTR_NEEDS_MSC_EN_FILTER
    cp_mscounteren_access_u: cross csraccess, counters_mcounteren, priv_mode_u iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCOUNTEREN) == get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCOUNTEREN)) {
    `ifdef UDB_MCOUNTENABLE_EN_0
    `ifndef UDB_SCOUNTENABLE_EN_0
        ignore_bins cycle_cannot_match_scounteren = binsof(counters_mcounteren.cycle_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins cycleh_cannot_match_scounteren = binsof(counters_mcounteren.cycleh_enabled);
        `endif
    `endif
    `endif
    `ifdef UDB_MCOUNTENABLE_EN_1
    `ifndef UDB_SCOUNTENABLE_EN_1
        ignore_bins time_cannot_match_scounteren = binsof(counters_mcounteren.time_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins timeh_cannot_match_scounteren = binsof(counters_mcounteren.timeh_enabled);
        `endif
    `endif
    `endif
    `ifdef UDB_MCOUNTENABLE_EN_2
    `ifndef UDB_SCOUNTENABLE_EN_2
        ignore_bins instret_cannot_match_scounteren = binsof(counters_mcounteren.instret_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins instreth_cannot_match_scounteren = binsof(counters_mcounteren.instreth_enabled);
        `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_3
    `ifdef UDB_MCOUNTENABLE_EN_3
    `ifndef UDB_SCOUNTENABLE_EN_3
        ignore_bins hpmcounter3_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter3_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter3h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter3h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_4
    `ifdef UDB_MCOUNTENABLE_EN_4
    `ifndef UDB_SCOUNTENABLE_EN_4
        ignore_bins hpmcounter4_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter4_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter4h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter4h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_5
    `ifdef UDB_MCOUNTENABLE_EN_5
    `ifndef UDB_SCOUNTENABLE_EN_5
        ignore_bins hpmcounter5_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter5_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter5h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter5h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_6
    `ifdef UDB_MCOUNTENABLE_EN_6
    `ifndef UDB_SCOUNTENABLE_EN_6
        ignore_bins hpmcounter6_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter6_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter6h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter6h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_7
    `ifdef UDB_MCOUNTENABLE_EN_7
    `ifndef UDB_SCOUNTENABLE_EN_7
        ignore_bins hpmcounter7_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter7_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter7h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter7h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_8
    `ifdef UDB_MCOUNTENABLE_EN_8
    `ifndef UDB_SCOUNTENABLE_EN_8
        ignore_bins hpmcounter8_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter8_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter8h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter8h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_9
    `ifdef UDB_MCOUNTENABLE_EN_9
    `ifndef UDB_SCOUNTENABLE_EN_9
        ignore_bins hpmcounter9_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter9_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter9h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter9h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_10
    `ifdef UDB_MCOUNTENABLE_EN_10
    `ifndef UDB_SCOUNTENABLE_EN_10
        ignore_bins hpmcounter10_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter10_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter10h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter10h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_11
    `ifdef UDB_MCOUNTENABLE_EN_11
    `ifndef UDB_SCOUNTENABLE_EN_11
        ignore_bins hpmcounter11_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter11_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter11h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter11h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_12
    `ifdef UDB_MCOUNTENABLE_EN_12
    `ifndef UDB_SCOUNTENABLE_EN_12
        ignore_bins hpmcounter12_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter12_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter12h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter12h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_13
    `ifdef UDB_MCOUNTENABLE_EN_13
    `ifndef UDB_SCOUNTENABLE_EN_13
        ignore_bins hpmcounter13_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter13_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter13h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter13h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_14
    `ifdef UDB_MCOUNTENABLE_EN_14
    `ifndef UDB_SCOUNTENABLE_EN_14
        ignore_bins hpmcounter14_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter14_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter14h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter14h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_15
    `ifdef UDB_MCOUNTENABLE_EN_15
    `ifndef UDB_SCOUNTENABLE_EN_15
        ignore_bins hpmcounter15_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter15_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter15h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter15h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_16
    `ifdef UDB_MCOUNTENABLE_EN_16
    `ifndef UDB_SCOUNTENABLE_EN_16
        ignore_bins hpmcounter16_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter16_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter16h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter16h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_17
    `ifdef UDB_MCOUNTENABLE_EN_17
    `ifndef UDB_SCOUNTENABLE_EN_17
        ignore_bins hpmcounter17_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter17_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter17h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter17h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_18
    `ifdef UDB_MCOUNTENABLE_EN_18
    `ifndef UDB_SCOUNTENABLE_EN_18
        ignore_bins hpmcounter18_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter18_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter18h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter18h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_19
    `ifdef UDB_MCOUNTENABLE_EN_19
    `ifndef UDB_SCOUNTENABLE_EN_19
        ignore_bins hpmcounter19_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter19_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter19h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter19h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_20
    `ifdef UDB_MCOUNTENABLE_EN_20
    `ifndef UDB_SCOUNTENABLE_EN_20
        ignore_bins hpmcounter20_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter20_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter20h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter20h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_21
    `ifdef UDB_MCOUNTENABLE_EN_21
    `ifndef UDB_SCOUNTENABLE_EN_21
        ignore_bins hpmcounter21_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter21_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter21h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter21h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_22
    `ifdef UDB_MCOUNTENABLE_EN_22
    `ifndef UDB_SCOUNTENABLE_EN_22
        ignore_bins hpmcounter22_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter22_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter22h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter22h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_23
    `ifdef UDB_MCOUNTENABLE_EN_23
    `ifndef UDB_SCOUNTENABLE_EN_23
        ignore_bins hpmcounter23_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter23_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter23h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter23h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_24
    `ifdef UDB_MCOUNTENABLE_EN_24
    `ifndef UDB_SCOUNTENABLE_EN_24
        ignore_bins hpmcounter24_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter24_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter24h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter24h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_25
    `ifdef UDB_MCOUNTENABLE_EN_25
    `ifndef UDB_SCOUNTENABLE_EN_25
        ignore_bins hpmcounter25_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter25_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter25h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter25h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_26
    `ifdef UDB_MCOUNTENABLE_EN_26
    `ifndef UDB_SCOUNTENABLE_EN_26
        ignore_bins hpmcounter26_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter26_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter26h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter26h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_27
    `ifdef UDB_MCOUNTENABLE_EN_27
    `ifndef UDB_SCOUNTENABLE_EN_27
        ignore_bins hpmcounter27_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter27_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter27h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter27h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_28
    `ifdef UDB_MCOUNTENABLE_EN_28
    `ifndef UDB_SCOUNTENABLE_EN_28
        ignore_bins hpmcounter28_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter28_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter28h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter28h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_29
    `ifdef UDB_MCOUNTENABLE_EN_29
    `ifndef UDB_SCOUNTENABLE_EN_29
        ignore_bins hpmcounter29_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter29_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter29h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter29h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_30
    `ifdef UDB_MCOUNTENABLE_EN_30
    `ifndef UDB_SCOUNTENABLE_EN_30
        ignore_bins hpmcounter30_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter30_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter30h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter30h_enabled);
        `endif
    `endif
    `endif
    `endif
    `ifdef UDB_HPM_COUNTER_EN_31
    `ifdef UDB_MCOUNTENABLE_EN_31
    `ifndef UDB_SCOUNTENABLE_EN_31
        ignore_bins hpmcounter31_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter31_enabled);
        `ifdef UDB_MXLEN_32
        ignore_bins hpmcounter31h_cannot_match_scounteren = binsof(counters_mcounteren.hpmcounter31h_enabled);
        `endif
    `endif
    `endif
    `endif
    }
    `else
    cp_mscounteren_access_u: cross csraccess, counters_mcounteren, priv_mode_u iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCOUNTEREN) == get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCOUNTEREN));
    `endif
    `undef S_ZICNTR_NEEDS_MSC_EN_FILTER
    `ifdef UDB_MCOUNTENABLE_EN_2
    cp_mcounter_inc_inaccessible: cross mcounteren_zeros, priv_mode_s;

    // ---- instret delta coverpoints ----

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    insn_lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    adr_misaligned_1: coverpoint ins.current.eff_addr[2:0] {
        bins one = {3'b001};  // scratch + 1
    }
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        illegal_address: coverpoint ins.current.eff_addr {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS_LOAD};
        }
    `endif
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    insn_add: coverpoint ins.current.insn {
        wildcard bins add = {ADD};
    }
    `ifdef UDB_SCOUNTENABLE_EN_2
    insn_sret: coverpoint ins.current.insn {
        wildcard bins sret = {SRET};
    }
    `endif
    `ifdef ZAWRS_SUPPORTED
        wrs_nto: coverpoint ins.current.insn {
            bins wrs_nto = {WRS_NTO};
        }
        wrs_sto: coverpoint ins.current.insn {
            bins wrs_sto = {WRS_STO};
        }
    `endif
    prev_instret_read: coverpoint ins.prev.insn {
        wildcard bins csrr_instret = {32'b110000000010_00000_010_?????_1110011};  // csrr rd, instret (0xC02)
    }
    prev_ecall_li: coverpoint ins.prev.insn {
        bins li_a0 = {32'h07300513};  // addi a0, x0, 0x73 (RVTEST_TSBI_ECALL_TEST)
    }
    mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MIE)[31:0] {
        bins zero = {0};
    }
    mstatus_sie_zero: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "sie")[0] {
        bins zero = {0};
    }
    `ifdef UDB_SSI_INTR_IMPL
        mip_ssip_one: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MIP, "ssip")[0] {
            bins one = {1};
        }
        mie_ssie_one: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MIE, "ssie")[0] {
            bins one = {1};
        }
    `endif
    `ifdef SSTC_SUPPORTED
        mip_stip_zero: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MIP, "stip")[0] {
            bins zero = {0};
        }
        mie_stie_one: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MIE, "stie")[0] {
            bins one = {1};
        }
    `endif

    // retiring instructions
    cp_instret_add:  cross priv_mode_s, insn_add, prev_instret_read;
    `ifdef UDB_SCOUNTENABLE_EN_2
    cp_instret_sret: cross priv_mode_s, insn_sret, prev_instret_read;
    `endif

    // instructions that trap before retiring
    cp_instret_ecall:  cross priv_mode_s, ecall, prev_ecall_li;
    cp_instret_ebreak: cross priv_mode_s, ebreak, prev_instret_read;
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        cp_instret_load_access_fault: cross priv_mode_s, insn_lw, illegal_address, prev_instret_read;
    `endif
    cp_instret_load_misaligned: cross priv_mode_s, insn_lw, adr_misaligned_1, prev_instret_read;

    // wfi and wrs; the wfi cases wake on delegated supervisor interrupts that sstatus.SIE = 0 keeps from being taken
    `ifdef UDB_WFI_FINITE
        cp_instret_wfi_timeout: cross priv_mode_s, wfi, mie_zero, prev_instret_read;
    `endif
    `ifdef UDB_SSI_INTR_IMPL
        cp_instret_wfi_pending: cross priv_mode_s, wfi, mip_ssip_one, mie_ssie_one, mstatus_sie_zero, prev_instret_read;
    `endif
    `ifdef SSTC_SUPPORTED
        cp_instret_wfi_wake: cross priv_mode_s, wfi, mip_stip_zero, mie_stie_one, mstatus_sie_zero;
    `endif
    `ifdef ZAWRS_SUPPORTED
        cp_instret_wrs_nto: cross priv_mode_s, wrs_nto, prev_instret_read;
        cp_instret_wrs_sto: cross priv_mode_s, wrs_sto, prev_instret_read;
    `endif
    `endif
endgroup
`endif

function void s_sample(int hart, int issue, ins_t ins);
    S_scause_cg.sample(ins);
    S_sstatus_cg.sample(ins);
    S_sprivinst_cg.sample(ins);
    S_scsr_cg.sample(ins);
    `ifdef F_SUPPORTED
        S_F_cg.sample(ins);
    `endif
    `ifdef ZVE32X_SUPPORTED
        S_V_cg.sample(ins);
    `endif
    `ifdef ZVE32F_SUPPORTED
        S_VF_cg.sample(ins);
    `endif
    `ifdef ZICNTR_SUPPORTED
        S_Zicntr_cg.sample(ins);
    `endif
endfunction
