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
            bins b_31_24_custom[] = {[24:31]}; // scause must be able to hold 0-31
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

    sstatus_FS: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs")[1:0] {
    }
    sstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs")[1:0] {
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
    cp_sew_lmul_vsetvl          : cross priv_mode_s, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew;
    cp_sew_lmul_vset_i_vli      : cross priv_mode_s, vset_i_vli_instructions, vset_sew, vset_lmul;
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
    cp_vl_walking1s_sew_lmul    : cross priv_mode_s, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1;

    //////////////////////////////////////////////////////////////////////////////////
    // cp_sstatus_vs_*
    // tests sstatus ability to set clean and initial to dirty only when supposed to
    //////////////////////////////////////////////////////////////////////////////////

    sstatus_vs_initial_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") {
        bins first = {1};
        bins clean  = {2};
    }

    sstatus_vs_inactive    : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") {
        bins inactive = {0};
    }

    cp_sstatus_vs_set_dirty_arithmetic  : cross priv_mode_s, std_vec,        vector_vector_arithmetic_instruction,   sstatus_vs_initial_clean;
    cp_sstatus_vs_set_dirty_csr         : cross priv_mode_s, std_vec,        vsetvli_instruction,                    sstatus_vs_initial_clean;
    cp_sstatus_vs_set_dirty_vcsr        : cross priv_mode_s, vcsrs_writable, csrops,                                 sstatus_vs_initial_clean;

    // misa is not visible in S-mode, so unlike Sm_V these do not cross misa_v_active
    cp_sstatus_vs_off_arithmetic        : cross priv_mode_s, sstatus_vs_inactive,     vector_vector_arithmetic_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );
    cp_sstatus_vs_off_csr               : cross priv_mode_s, sstatus_vs_inactive,     vsetvli_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );

endgroup
`endif

`ifdef ZVE32F_SUPPORTED
covergroup S_VF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_vf_coverpoints.svh"

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    sstatus_fs_initial_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs") {
        bins first_state = {1};
        bins clean  = {2};
    }

    sstatus_fs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs") {
        bins off = {0};
    }

    cp_vectorfp_sstatus_fs_state_affecting_register : cross priv_mode_s, std_vec, vfmv_f_s, sstatus_fs_initial_clean;
    cp_vectorfp_sstatus_fs_state_affecting_csr      : cross priv_mode_s, std_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_initial_clean, fflags_modified_after_clear;
    cp_vectorfp_sstatus_fs_state_nonaffecting       : cross priv_mode_s, std_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_initial_clean, vs1_zero, vs2_zero;
    cp_vectorfp_sstatus_fs_off                      : cross priv_mode_s, std_trap_vec, vector_vector_arithmetic_fp_instruction, sstatus_fs_off, vs1_zero, vs2_zero;

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
endfunction
