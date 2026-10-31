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

// Software check exceptions are supported for both Zicfilp and Zicfiss
`ifdef ZICFILP_SUPPORTED
    `define SOFTWARE_CHECK_SUPPORTED
`endif
`ifdef ZICFISS_SUPPORTED
    `ifndef SOFTWARE_CHECK_SUPPORTED
        `define SOFTWARE_CHECK_SUPPORTED
    `endif
`endif

covergroup Sm_mcause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    mcause: coverpoint ins.current.insn[31:20] {
        bins mcause = {CSR_MCAUSE};
    }
    mcause_interrupt : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins interrupt = {1};
    }
    mcause_exception : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins exception = {0};
    }
    mcause_exception_values: coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        // exclude reserved and custom fields
        bins b_0_instruction_address_misaligned = {0};
        bins b_1_instruction_address_fault = {1};
        bins b_2_illegal_instruction = {2};
        bins b_3_breakpoint = {3};
        bins b_4_load_address_misaligned = {4};
        bins b_5_load_access_fault = {5};
        bins b_6_store_address_misaligned = {6};
        bins b_7_store_access_fault = {7};
        `ifdef U_SUPPORTED
            bins b_8_ecall_u = {8};
        `endif
        `ifdef S_SUPPORTED
            bins b_9_ecall_s = {9};
        `endif
        `ifdef H_SUPPORTED
            bins b_10_ecall_vs = {10};
        `endif
        bins b_11_ecall_m = {11};
        bins b_12_instruction_page_fault = {12};
        bins b_13_load_page_fault = {13};
        //bins b_14_reserved = {14};
        bins b_15_store_page_fault = {15};
        `ifdef SSDBLTRP_SUPPORTED
            bins b_16_double_trap = {16}; // never delegated to S mode
        `endif
        //bins b_17_reserved = {17};
        `ifdef SOFTWARE_CHECK_SUPPORTED
            bins b_18_software_check = {18};
        `endif
        // bins b_19_hardware_error = {19}; // unclear how to trigger on all implementations
        `ifdef H_SUPPORTED
            bins b_20_instr_guest_page_fault = {20};
            bins b_21_load_guest_page_fault = {21};
            bins b_22_virtual_instruction = {22};
            bins b_23_store_guest_page_fault = {23};
        `endif
        //bins b_31_24_custom = {[31:24]};
        //bins b_47_32_reserved = {[47:32]};
        //bins b_63_48_custom = {[63:48]};
    }
    mcause_interrupt_values: coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        // exclude reserved and custom fields
        //bins b_0_reserved = {0};
        bins b_1_supervisor_software = {1};
        `ifdef H_SUPPORTED
            bins b_2_vs_software = {2};
        `endif
        bins b_3_machine_software = {3};
        //bins b_4_reserved = {4};
        bins b_5_supervisor_timer = {5};
        `ifdef H_SUPPORTED
            bins b_6_vs_timer = {6};
        `endif
        bins b_7_machine_timer = {7};
        //bins b_8_reserved = {8};
        bins b_9_supervisor_external = {9};
        `ifdef H_SUPPORTED
            bins b_10_vs_external = {10};
        `endif
        bins b_11_machine_external = {11};
        `ifdef H_SUPPORTED
            bins b_12_supervisor_guest_external = {12};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            bins b_13_counter_overflow = {13};
        `endif
        //bins b_14_reserved = {14};
        //bins b_15_reserved = {15};
    }

    // main coverpoints
    // This is Sm machine-mode testing, so all coverpoints are in Machine mode.
    cp_mcause_write_exception: cross priv_mode_m, csrrw, mcause, mcause_exception_values, mcause_exception; // CSR write of mcause in M mode with interesting values
    cp_mcause_write_interrupt: cross priv_mode_m, csrrw, mcause, mcause_interrupt_values, mcause_interrupt; // CSR write of mcause in M mode with interesting values

endgroup


covergroup Sm_mstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // SD COVERPOINTS
    // Cross-product of trying to write mstatus.SD, .FS, .XS, .VS
    cp_mstatus_sd: coverpoint ins.current.rs1_val[`UDB_MXLEN-1]  {
    }
    cp_mstatus_fs: coverpoint ins.current.rs1_val[14:13] {
    }
    cp_mstatus_vs: coverpoint ins.current.rs1_val[10:9] {
    }
    cp_mstatus_xs: coverpoint ins.current.rs1_val[16:15] {
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    mstatus: coverpoint ins.current.insn[31:20] {
        bins mstatus = {CSR_MSTATUS};
    }
    cp_mstatus_sd_write: cross priv_mode_m, csrrw, mstatus, cp_mstatus_sd, cp_mstatus_fs, cp_mstatus_vs, cp_mstatus_xs;
endgroup

covergroup Sm_mprivinst_cg with function sample(ins_t ins);
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
    old_mstatus_tsr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tsr")[0] {
    }
    old_mstatus_mprv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0] {
    }
    old_mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins M_mode = {2'b11};
        `ifdef S_SUPPORTED
            bins S_mode = {2'b01};
        `endif
        `ifdef U_SUPPORTED
            bins U_mode = {2'b00};
        `endif
    }
    old_mstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spp")[0] {
    }
    old_mstatus_mpie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie")[0] {
    }
    old_mstatus_mie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
    }
    old_mstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spie")[0] {
    }
    old_mstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
    }

    cp_mprivinst: cross priv_mode_m, privinstrs;
    cp_mret:      cross priv_mode_m, mret, old_mstatus_mpp, old_mstatus_mprv, old_mstatus_mpie, old_mstatus_mie;
    cp_sret:      cross priv_mode_m, sret, old_mstatus_mprv, old_mstatus_spp, old_mstatus_spie, old_mstatus_sie, old_mstatus_tsr;

    `ifdef S_SUPPORTED
        // this version needs to be in Sm because it exercises TSR, which would cause a trap loop if illegal instructions are delegated to S-mode
        old_sstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
        }
        old_sstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] {
        }
        old_sstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0] {
        }
        cp_sret_s:     cross priv_mode_s, sret, old_sstatus_spp, old_sstatus_spie, old_sstatus_sie, old_mstatus_tsr;

        // sfence.vma is here rather than in S because it exercises mstatus.TVM, which only M-mode can set.
        // It is only tested where some Sv mode exists, because a hart with satp.MODE read-only
        // zero may raise an illegal instruction for it (norm:satp-mode_roz_sfence_illegal).
        // Sv48 and Sv57 imply Sv39, so Sv39 and Sv32 between them cover every case.
        `ifdef SV39_SUPPORTED
            `define SM_SFENCE_VMA_LEGAL
        `elsif SV32_SUPPORTED
            `define SM_SFENCE_VMA_LEGAL
        `endif
        `ifdef SM_SFENCE_VMA_LEGAL
            sfence: coverpoint ins.current.insn  {
                wildcard bins sfence_vma = {SFENCE_VMA};
            }
            old_mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm")[0] {
            }
            cp_sfence_tvm: cross priv_mode_m_s, sfence, old_mstatus_tvm;
        `endif
    `endif
endgroup

covergroup Sm_mcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mcsrname_ro : coverpoint ins.current.insn[31:20] { // extended set for access tests, including read-only CSRs
        bins mvendorid  = {CSR_MVENDORID};
        bins marchid    = {CSR_MARCHID};
        bins mimpid     = {CSR_MIMPID};
        bins mhartid    = {CSR_MHARTID};
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            bins mconfigptr = {CSR_MCONFIGPTR};
        `endif
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

     csraccesses_masked : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val != 0); // csrc mask
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val == 0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val != 0); // csrw mask
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val != 0); // csrs mask
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val == 0); // csrr
    }

    // CSRs whose access tests use masked writes (see csraccesses_masked above)
    mcsrname_masked : coverpoint ins.current.insn[31:20] {
        bins mstatus = {CSR_MSTATUS};
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            bins menvcfg = {CSR_MENVCFG};
        `endif
        `ifdef MSECCFG_SUPPORTED
            bins mseccfg = {CSR_MSECCFG};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef SM1P12P0_OR_LATER_SUPPORTED
                bins mstatush = {CSR_MSTATUSH};
                bins menvcfgh = {CSR_MENVCFGH};
            `endif
            `ifdef MSECCFG_SUPPORTED
                bins mseccfgh = {CSR_MSECCFGH};
            `endif
        `endif
    }

    // counters keep incrementing, so don't write the maximum value that will roll over
    // tests should check value read back is within some tolerance of value written
    cntraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all  = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0     = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw_some = {CSRRW} iff (ins.current.rs1_val != '0); // csrw some ones
        wildcard bins csrrs_some = {CSRRS} iff (ins.current.rs1_val != '0); // csrs some ones
        wildcard bins csrr       = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

    mcsrname : coverpoint ins.current.insn[31:20] { // excludes read-only CSRs and the masked-write CSRs (mcsrname_masked)
        bins medeleg    = {CSR_MEDELEG};
        bins mideleg    = {CSR_MIDELEG};
        bins mie        = {CSR_MIE};
        // bins mtvec      = {CSR_MTVEC}; // warl field has complex write restrictions and is not easy to test
        bins mcounteren = {CSR_MCOUNTEREN};
        bins mscratch   = {CSR_MSCRATCH};
        bins mepc       = {CSR_MEPC};
        // bins mcause     = {CSR_MCAUSE}; // WLRL field; tested with cp_mcause_write_exception and cp_mcause_write_interrupt
        bins mtval      = {CSR_MTVAL};
        bins mip        = {CSR_MIP};
        `ifdef UDB_MCOUNTINHIBIT_IMPLEMENTED
            bins mcountinhibit = {CSR_MCOUNTINHIBIT};
        `endif
        bins mhpmevent3 = {CSR_MHPMEVENT3};
        bins mhpmevent4 = {CSR_MHPMEVENT4};
        bins mhpmevent5 = {CSR_MHPMEVENT5};
        bins mhpmevent6 = {CSR_MHPMEVENT6};
        bins mhpmevent7 = {CSR_MHPMEVENT7};
        bins mhpmevent8 = {CSR_MHPMEVENT8};
        bins mhpmevent9 = {CSR_MHPMEVENT9};
        bins mhpmevent10= {CSR_MHPMEVENT10};
        bins mhpmevent11= {CSR_MHPMEVENT11};
        bins mhpmevent12= {CSR_MHPMEVENT12};
        bins mhpmevent13= {CSR_MHPMEVENT13};
        bins mhpmevent14= {CSR_MHPMEVENT14};
        bins mhpmevent15= {CSR_MHPMEVENT15};
        bins mhpmevent16= {CSR_MHPMEVENT16};
        bins mhpmevent17= {CSR_MHPMEVENT17};
        bins mhpmevent18= {CSR_MHPMEVENT18};
        bins mhpmevent19= {CSR_MHPMEVENT19};
        bins mhpmevent20= {CSR_MHPMEVENT20};
        bins mhpmevent21= {CSR_MHPMEVENT21};
        bins mhpmevent22= {CSR_MHPMEVENT22};
        bins mhpmevent23= {CSR_MHPMEVENT23};
        bins mhpmevent24= {CSR_MHPMEVENT24};
        bins mhpmevent25= {CSR_MHPMEVENT25};
        bins mhpmevent26= {CSR_MHPMEVENT26};
        bins mhpmevent27= {CSR_MHPMEVENT27};
        bins mhpmevent28= {CSR_MHPMEVENT28};
        bins mhpmevent29= {CSR_MHPMEVENT29};
        bins mhpmevent30= {CSR_MHPMEVENT30};
        bins mhpmevent31= {CSR_MHPMEVENT31};
        `ifdef UDB_MXLEN_32
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins medelegh = {CSR_MEDELEGH};
            `endif
        `endif
    }
    mcounters : coverpoint ins.current.insn[31:20] {
        bins mcycle      = {CSR_MCYCLE};
        bins minstret    = {CSR_MINSTRET};
        bins mhpmcounter3 = {CSR_MHPMCOUNTER3};
        bins mhpmcounter4 = {CSR_MHPMCOUNTER4};
        bins mhpmcounter5 = {CSR_MHPMCOUNTER5};
        bins mhpmcounter6 = {CSR_MHPMCOUNTER6};
        bins mhpmcounter7 = {CSR_MHPMCOUNTER7};
        bins mhpmcounter8 = {CSR_MHPMCOUNTER8};
        bins mhpmcounter9 = {CSR_MHPMCOUNTER9};
        bins mhpmcounter10= {CSR_MHPMCOUNTER10};
        bins mhpmcounter11= {CSR_MHPMCOUNTER11};
        bins mhpmcounter12= {CSR_MHPMCOUNTER12};
        bins mhpmcounter13= {CSR_MHPMCOUNTER13};
        bins mhpmcounter14= {CSR_MHPMCOUNTER14};
        bins mhpmcounter15= {CSR_MHPMCOUNTER15};
        bins mhpmcounter16= {CSR_MHPMCOUNTER16};
        bins mhpmcounter17= {CSR_MHPMCOUNTER17};
        bins mhpmcounter18= {CSR_MHPMCOUNTER18};
        bins mhpmcounter19= {CSR_MHPMCOUNTER19};
        bins mhpmcounter20= {CSR_MHPMCOUNTER20};
        bins mhpmcounter21= {CSR_MHPMCOUNTER21};
        bins mhpmcounter22= {CSR_MHPMCOUNTER22};
        bins mhpmcounter23= {CSR_MHPMCOUNTER23};
        bins mhpmcounter24= {CSR_MHPMCOUNTER24};
        bins mhpmcounter25= {CSR_MHPMCOUNTER25};
        bins mhpmcounter26= {CSR_MHPMCOUNTER26};
        bins mhpmcounter27= {CSR_MHPMCOUNTER27};
        bins mhpmcounter28= {CSR_MHPMCOUNTER28};
        bins mhpmcounter29= {CSR_MHPMCOUNTER29};
        bins mhpmcounter30= {CSR_MHPMCOUNTER30};
        bins mhpmcounter31= {CSR_MHPMCOUNTER31};
        `ifdef UDB_MXLEN_32
            bins mcycleh      = {CSR_MCYCLEH};
            bins minstreth    = {CSR_MINSTRETH};
            bins mhpmcounter3h = {CSR_MHPMCOUNTER3H};
            bins mhpmcounter4h = {CSR_MHPMCOUNTER4H};
            bins mhpmcounter5h = {CSR_MHPMCOUNTER5H};
            bins mhpmcounter6h = {CSR_MHPMCOUNTER6H};
            bins mhpmcounter7h = {CSR_MHPMCOUNTER7H};
            bins mhpmcounter8h = {CSR_MHPMCOUNTER8H};
            bins mhpmcounter9h = {CSR_MHPMCOUNTER9H};
            bins mhpmcounter10h= {CSR_MHPMCOUNTER10H};
            bins mhpmcounter11h= {CSR_MHPMCOUNTER11H};
            bins mhpmcounter12h= {CSR_MHPMCOUNTER12H};
            bins mhpmcounter13h= {CSR_MHPMCOUNTER13H};
            bins mhpmcounter14h= {CSR_MHPMCOUNTER14H};
            bins mhpmcounter15h= {CSR_MHPMCOUNTER15H};
            bins mhpmcounter16h= {CSR_MHPMCOUNTER16H};
            bins mhpmcounter17h= {CSR_MHPMCOUNTER17H};
            bins mhpmcounter18h= {CSR_MHPMCOUNTER18H};
            bins mhpmcounter19h= {CSR_MHPMCOUNTER19H};
            bins mhpmcounter20h= {CSR_MHPMCOUNTER20H};
            bins mhpmcounter21h= {CSR_MHPMCOUNTER21H};
            bins mhpmcounter22h= {CSR_MHPMCOUNTER22H};
            bins mhpmcounter23h= {CSR_MHPMCOUNTER23H};
            bins mhpmcounter24h= {CSR_MHPMCOUNTER24H};
            bins mhpmcounter25h= {CSR_MHPMCOUNTER25H};
            bins mhpmcounter26h= {CSR_MHPMCOUNTER26H};
            bins mhpmcounter27h= {CSR_MHPMCOUNTER27H};
            bins mhpmcounter28h= {CSR_MHPMCOUNTER28H};
            bins mhpmcounter29h= {CSR_MHPMCOUNTER29H};
            bins mhpmcounter30h= {CSR_MHPMCOUNTER30H};
            bins mhpmcounter31h= {CSR_MHPMCOUNTER31H};
        `endif
    }

    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    csr_debug: coverpoint ins.current.insn[31:20]  {
        bins debug_only[] = {[12'h7B0:12'h7BF]};
    }
    csr_ro: coverpoint ins.current.insn[31:20] {
        bins readonly[] = {[12'hC00:12'hFFF]};
    }

    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csrc: coverpoint ins.current.insn {
        wildcard bins csrc = {CSRC};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }
    rs1_ones: coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }

    `ifdef UDB_MCOUNTINHIBIT_IMPLEMENTED
        old_mcountinhibit_cy: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcountinhibit", "cy") {
            bins zero = {1'b0};
            `ifdef UDB_COUNTINHIBIT_EN_0
                bins one = {1'b1}; // only if counter can be inhibited
            `endif
        }
        old_mcountinhibit_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcountinhibit", "ir") {
            bins zero = {1'b0};
            `ifdef UDB_COUNTINHIBIT_EN_2
                bins one = {1'b1}; // only if counter can be inhibited
            `endif
        }
    `endif

    mcycle: coverpoint ins.current.insn[31:20] {
        bins mcycle = {CSR_MCYCLE};
    }
    minstret: coverpoint ins.current.insn[31:20] {
        bins minstret = {CSR_MINSTRET};
    }
    time_csr: coverpoint ins.current.insn[31:20] {
        bins time_csr = {CSR_TIME};
    }
    `ifdef UDB_MXLEN_32
        timeh_csr: coverpoint ins.current.insn[31:20] {
            bins timeh_csr = {CSR_TIMEH};
        }
    `endif

    misa: coverpoint ins.current.insn[31:20] {
        bins misa = {CSR_MISA};
    }
    // only check MISA.MXL.  The other bits are allowed to be 0s even if a feature is implemented.
    // misa.MXL is also allowed to be hardwired to 0 (but should match the reference model)
    misa_mxl_accesses : coverpoint ins.current.insn {
        wildcard bins csrc_11  = {CSRC} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b11); // clear misa.MXL
        wildcard bins csrs_11  = {CSRS} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b11); // set misa.MXL = 11
        wildcard bins csrw_00  = {CSRW} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b00); // write misa.MXL = 00
        wildcard bins csrw_01  = {CSRW} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b01); // write misa.MXL = 01
        wildcard bins csrw_10  = {CSRW} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b10); // write misa.MXL = 10
        wildcard bins csrw_11  = {CSRW} iff (ins.current.rs1_val[`UDB_MXLEN-1:`UDB_MXLEN-2] == 2'b11); // write misa.MXL = 11
        wildcard bins csrr     = {CSRR};                                                   // read misa
    }

    misa_dependencies : coverpoint ins.current.rs1_val[25:0] {
        wildcard bins i1e1   = { 26'b?????????????????1???1???? };
        wildcard bins i0e0   = { 26'b?????????????????1???1???? };
        wildcard bins f0d1   = { 26'b????????????????????0?1??? };
        wildcard bins f1d0q1 = { 26'b?????????1??????????1?0??? };
        wildcard bins s1u0   = { 26'b?????0?1?????????????????? };
        wildcard bins h1s0   = { 26'b???????0??????????1??????? };
        wildcard bins h1s1u0 = { 26'b?????0?1??????????1??????? };
    }

    misa_c_0 : coverpoint ins.current.rs1_val[2] {
        bins c0 = {1'b1};
    }

    pc_1 : coverpoint ins.current.pc_rdata[1] {
        `ifdef ZCA_SUPPORTED
            bins odd = {1'b1}; // check for 2-byte alignment when supported
        `endif
        bins even = {1'b0}; // trivial case of 4-byte alignment
    }

    // mtval must hold 0 and, when the illegal instruction encoding is reported in it, every ILEN-bit value
    mtval: coverpoint ins.current.insn[31:20] {
        bins mtval = {CSR_MTVAL};
    }
    mtval_zero: coverpoint ins.current.rs1_val {
        bins zero = {0};
    }
    // Real addresses are valid even when address translation is off, so these are not gated on
    // Sv* support (the walk coverpoints below are). The generator emits the csrw immediately
    // after `auipc xN, 0`, so the pc value written equals the csrw's pc - 4; the scratch value
    // is scratch + 0xA8, an offset chosen so no walk, zero, or all-ones pattern shares its low byte.
    mepc: coverpoint ins.current.insn[31:20] {
        bins mepc = {CSR_MEPC};
    }
    xaddr_pc: coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch: coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    `ifdef UDB_REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION
        mtval_ilen_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:31] };
        }
        mtval_ilen_ones: coverpoint ins.current.rs1_val {
            bins ones = {32'hFFFFFFFF};
        }
    `endif

    // Valid virtual address walks: mepc and mtval must hold every canonical virtual address.
    // Canonical addresses have bits XLEN-1:VALEN-1 equal, so bit VALEN-2 is the msb walked on its own
    // (31 for Sv32, where VALEN = XLEN).
    `ifdef SV57_SUPPORTED
        `define SM_VADDR_WALK_MSB 55
    `elsif SV48_SUPPORTED
        `define SM_VADDR_WALK_MSB 46
    `elsif SV39_SUPPORTED
        `define SM_VADDR_WALK_MSB 37
    `elsif SV32_SUPPORTED
        `define SM_VADDR_WALK_MSB 31
    `endif
    `ifdef SM_VADDR_WALK_MSB
        // mepc: bit 0 is always 0; bit 1 is 0 unless Zca allows 2-byte instruction alignment
        xepc_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`SM_VADDR_WALK_MSB] };
        }
        xepc_vaddr_walk0: coverpoint $clog2(~(ins.current.rs1_val))
                              iff ($onehot(~(ins.current.rs1_val))) {
            bins b_0[] = { [0:`SM_VADDR_WALK_MSB] };
        }
        // mtval: any byte address is a valid virtual address
        mtval_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`SM_VADDR_WALK_MSB] };
        }
        mtval_vaddr_walk0: coverpoint $clog2(~ins.current.rs1_val) iff ($onehot(~ins.current.rs1_val)) {
            bins b_0[] = { [0:`SM_VADDR_WALK_MSB] };
        }

        cp_mepc_vaddr_walk1:    cross priv_mode_m, csrrw, mepc, xepc_vaddr_walk1;
        cp_mepc_vaddr_walk0:    cross priv_mode_m, csrrw, mepc, xepc_vaddr_walk0;
        cp_mtval_vaddr_walk1:   cross priv_mode_m, csrrw, mtval, mtval_vaddr_walk1;
        cp_mtval_vaddr_walk0:   cross priv_mode_m, csrrw, mtval, mtval_vaddr_walk0;
    `endif

    cp_mcsr_access:             cross priv_mode_m, mcsrname, csraccesses;
    cp_mcsr_access_masked:      cross priv_mode_m, mcsrname_masked, csraccesses_masked;
    cp_mcsr_access_ro:          cross priv_mode_m, mcsrname_ro, csraccesses;
    cp_mcsrwalk :               cross priv_mode_m, mcsrname, csrop, walking_ones {
        // mepc and mtval only have to hold valid virtual addresses; see cp_{mepc,mtval}_vaddr_walk*
        ignore_bins mepc_not_walked  = binsof(mcsrname.mepc);
        ignore_bins mtval_not_walked = binsof(mcsrname.mtval);
    }
    // Avoid testing WPRI bits and those that don't like being poked.
    // Keep the lists below in sync with the masks in Sm.py.
    cp_mcsrwalk_masked :        cross priv_mode_m, mcsrname_masked, csrop, walking_ones {
        ignore_bins mstatus_not_walked = binsof(mcsrname_masked.mstatus) &&
            binsof(walking_ones) intersect {0, 2, 4, 6, [25:30], [32:37], 40, [43:62]};
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            ignore_bins menvcfg_not_walked = binsof(mcsrname_masked.menvcfg) &&
                binsof(walking_ones) intersect {1, [8:31], [34:58]};
        `endif
        `ifdef MSECCFG_SUPPORTED
            ignore_bins mseccfg_not_walked = binsof(mcsrname_masked.mseccfg) &&
                binsof(walking_ones) intersect {[0:7], [11:31], [34:63]};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef SM1P12P0_OR_LATER_SUPPORTED
                ignore_bins mstatush_not_walked = binsof(mcsrname_masked.mstatush) &&
                    binsof(walking_ones) intersect {[0:5], 8, [11:31]};
                ignore_bins menvcfgh_not_walked = binsof(mcsrname_masked.menvcfgh) &&
                    binsof(walking_ones) intersect {[2:26]};
            `endif
            `ifdef MSECCFG_SUPPORTED
                ignore_bins mseccfgh_not_walked = binsof(mcsrname_masked.mseccfgh) &&
                    binsof(walking_ones) intersect {[2:31]};
            `endif
        `endif
    }
    `ifdef SSDBLTRP_SUPPORTED
        // mstatus.SDT is read-only zero while menvcfg.DTE = 0 (the walks, after boot) and writable with DTE = 1
        mstatus_sdt_write : coverpoint ins.current.insn {
            wildcard bins csrs_sdt = {CSRS} iff (ins.current.insn[31:20] == CSR_MSTATUS && ins.current.rs1_val[24]);
            wildcard bins csrc_sdt = {CSRC} iff (ins.current.insn[31:20] == CSR_MSTATUS && ins.current.rs1_val[24]);
        }
        `ifdef UDB_MXLEN_32
            old_menvcfg_dte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "dte")[0];
        `else
            old_menvcfg_dte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "dte")[0];
        `endif
        cp_mstatus_sdt_dte :    cross priv_mode_m, mstatus_sdt_write, old_menvcfg_dte;
    `endif
    cp_mtval_zero:              cross priv_mode_m, csrrw, mtval, mtval_zero;
    cp_mepc_vaddr_pc:           cross priv_mode_m, csrrw, mepc, xaddr_pc;
    cp_mepc_vaddr_scratch:      cross priv_mode_m, csrrw, mepc, xaddr_scratch;
    cp_mtval_vaddr_pc:          cross priv_mode_m, csrrw, mtval, xaddr_pc;
    cp_mtval_vaddr_scratch:     cross priv_mode_m, csrrw, mtval, xaddr_scratch;
    `ifdef UDB_REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION
        cp_mtval_ilen_walk1:    cross priv_mode_m, csrrw, mtval, mtval_ilen_walk1;
        cp_mtval_ilen_ones:     cross priv_mode_m, csrrw, mtval, mtval_ilen_ones;
    `endif
    cp_csr_insufficient_priv:   cross priv_mode_m, csrr, csr_debug, nonzerord;
    cp_csr_ro:                  cross priv_mode_m, csrrw, csr_ro, rs1_ones;

    // counters
    cp_cntr_access :            cross priv_mode_m, mcounters, cntraccesses;
    `ifdef UDB_MCOUNTINHIBIT_IMPLEMENTED
        cp_inhibit_mcycle :     cross priv_mode_m, csrr, mcycle, old_mcountinhibit_cy;
        cp_inhibit_minstret :   cross priv_mode_m, csrr, minstret, old_mcountinhibit_ir;
    `endif

    // misa
    cp_misa_mxl :               cross priv_mode_m, misa, misa_mxl_accesses;
    cp_misa_dependencies :      cross priv_mode_m, csrrw, misa, misa_dependencies;
    cp_misa_clear_c :           cross priv_mode_m, csrc, misa_c_0, pc_1;

    // mepc[1] is masked on reads, including mret's, while misa.C = 0 makes IALIGN = 32
    // Only on harts with Zca whose misa.C is writable, so that IALIGN can change
    `ifdef ZCA_SUPPORTED
        `ifdef UDB_MUTABLE_MISA_C
            csrr_mepc : coverpoint ins.current.insn {
                wildcard bins csrr_mepc = {CSRRS} iff (ins.current.insn[31:20] == CSR_MEPC && ins.current.insn[19:15] == 0);
            }
            mret_insn : coverpoint ins.current.insn {
                wildcard bins mret = {MRET};
            }
            misa_c_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "exts")[2] {
                bins off = {1'b0};
            }
            mepc_bit1 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mepc", "mepc")[1] {
                bins set = {1'b1};
            }
            cp_mepc_ialign32_read :  cross priv_mode_m, csrr_mepc, misa_c_off, mepc_bit1;
            cp_mepc_ialign32_mret :  cross priv_mode_m, mret_insn, misa_c_off, mepc_bit1;
            // sepc[1] likewise, for reads and sret in M-mode and S-mode
            `ifdef S_SUPPORTED
                csrr_sepc : coverpoint ins.current.insn {
                    wildcard bins csrr_sepc = {CSRRS} iff (ins.current.insn[31:20] == CSR_SEPC && ins.current.insn[19:15] == 0);
                }
                sret_insn : coverpoint ins.current.insn {
                    wildcard bins sret = {SRET};
                }
                sepc_bit1 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sepc", "sepc")[1] {
                    bins set = {1'b1};
                }
                cp_sepc_ialign32_read :  cross priv_mode_m_s, csrr_sepc, misa_c_off, sepc_bit1;
                cp_sepc_ialign32_sret :  cross priv_mode_m_s, sret_insn, misa_c_off, sepc_bit1;
            `endif
        `endif
    `endif

    cp_mtime_write :            cross priv_mode_m, csrr,  time_csr; // assumes mtime has been written
    `ifdef UDB_MXLEN_32
        cp_mtimeh_write :       cross priv_mode_m, csrr,  timeh_csr; // assumes mtimeh has been written
    `endif

    `ifdef SM1P13P0_OR_LATER_SUPPORTED
        misa_b_bit: coverpoint ins.current.rs1_val[1] {
            bins b_set   = {1'b1};
            bins b_clear = {1'b0};
        }
        misa_v_bit: coverpoint ins.current.rs1_val[21] {
            bins v_set   = {1'b1};
            bins v_clear = {1'b0};
        }

        cp_misa_b: cross priv_mode_m, misa, csrop, misa_b_bit;
        cp_misa_v: cross priv_mode_m, misa, csrop, misa_v_bit;


        `ifdef RVMODEL_MSIP_ADDRESS
            msip_address: coverpoint ins.current.rs1_val {
                bin msip = {`RVMODEL_MSIP_ADDRESS};
            }
            msip_val: coverpoint ins.current.rs2_val {
                bin zero = {0};
                bin one  = {1};
            }
            cp_msip: cross priv_mode_m, sw, msip_address, msip_val;
        `endif // RVMODEL_MSIP_ADDRESS
    `endif // SM1P13P0_OR_LATER_SUPPORTED

    csrrw_allones: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW} iff (ins.current.rs1_val == '1);
    }
    rs2_ones: coverpoint ins.current.rs2_val {
        bins allones = {'1};
    }

    `ifdef UDB_MXLEN_32
        mcycleh: coverpoint ins.current.insn[31:20] {
            bins mcycleh = {CSR_MCYCLEH};
        }
        minstreth: coverpoint ins.current.insn[31:20] {
            bins minstreth = {CSR_MINSTRETH};
        }
    `endif

    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    `ifdef UDB_MXLEN_64
        sd: coverpoint ins.current.insn {
            wildcard bins sd = {SD};
        }
    `endif

    cp_mcycle_wraparound:   cross priv_mode_m, csrrw_allones, mcycle;
    cp_minstret_wraparound: cross priv_mode_m, csrrw_allones, minstret;

    `ifdef UDB_MXLEN_32
        cp_mcycleh_wraparound:   cross priv_mode_m, csrrw_allones, mcycleh;
        cp_minstreth_wraparound: cross priv_mode_m, csrrw_allones, minstreth;
    `endif

    `ifdef RVMODEL_MTIME_ADDRESS
        `ifdef UDB_MXLEN_64
            mtime_address: coverpoint ins.current.rs1_val + ins.current.imm {
                bins mtime = {`RVMODEL_MTIME_ADDRESS};
            }
            cp_mtime_wraparound: cross priv_mode_m, sd, mtime_address, rs2_ones;
        `else
            mtime_address: coverpoint ins.current.rs1_val + ins.current.imm {
                bins mtime = {`RVMODEL_MTIME_ADDRESS};
            }
            mtimeh_address: coverpoint ins.current.rs1_val + ins.current.imm {
                bins mtimeh = {`RVMODEL_MTIME_ADDRESS + 4};
            }
            cp_mtime_wraparound:  cross priv_mode_m, sw, mtime_address, rs2_ones;
            cp_mtimeh_wraparound: cross priv_mode_m, sw, mtimeh_address, rs2_ones;
        `endif
    `endif

    // tests of S-mode features that need to be done from M-mode
    `ifdef S_SUPPORTED
        scsrname : coverpoint ins.current.insn[31:20] {
            bins sstatus       = {CSR_SSTATUS};
            bins sie           = {CSR_SIE};
            bins stvec         = {CSR_STVEC}; // WARL; the signature checks only MODE[1], which must read 0
            bins scounteren    = {CSR_SCOUNTEREN};
            bins sscratch      = {CSR_SSCRATCH};
            bins sepc          = {CSR_SEPC};
            // bins scause        = {CSR_SCAUSE}; // WLRL field; tested with cp_scause_from_m
            bins stval         = {CSR_STVAL};
            bins sip           = {CSR_SIP};
            `ifdef S1P12P0_OR_LATER_SUPPORTED
              bins senvcfg       = {CSR_SENVCFG};
            `endif
        }
        scause_csr : coverpoint ins.current.insn[31:20] {
            bins scause = {CSR_SCAUSE};
        }
        // the scause Exception Code is WLRL; Ss1p12 and later must hold the values 0-31, Ss1p11 only the supported codes
        scause_wlrl_values : coverpoint ins.current.rs1_val {
            bins code[] = {[0:9], 12, 13, 15};
            `ifdef S1P12P0_OR_LATER_SUPPORTED
              bins code_ss1p12[] = {10, 11, 14, [16:31]};
            `else
              `ifdef SOFTWARE_CHECK_SUPPORTED
                bins code_18_software_check = {18};
              `endif
              `ifdef H_SUPPORTED
                bins code_h[] = {10, [20:23]};
              `endif
            `endif
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
            wildcard bins csrw = {CSRW};
        }
        rs1_prev: coverpoint ins.prev.rs1_val {
            bins zero = { 0 };
            bins nonzero = { [1:$] };
        }
        shadow_int : coverpoint {ins.prev.insn[31:20], ins.current.insn[31:20]} {
            bins mie_sie         = { {CSR_MIE, CSR_SIE} };
            bins mip_sip         = { {CSR_MIP, CSR_SIP} };
            bins sie_mie         = { {CSR_SIE, CSR_MIE} };
            bins sip_mip         = { {CSR_SIP, CSR_MIP} };
        }
        // S-level interrupt delegation bits {LCOFI, SEI, STI, SSI}; the VS bits are read-only without H
        mideleg_s: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "lcofip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "seip")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "stip")[0],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "ssip")[0]} {
            bins none = {4'b0000};
            bins all  = {4'b1111};
        }
        mideleg_s_walking: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "lcofip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "seip")[0],
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "stip")[0],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "ssip")[0]} {
            bins lcofi = {4'b1000};
            bins sei   = {4'b0100};
            bins sti   = {4'b0010};
            bins ssi   = {4'b0001};
        }
        sip_sie: coverpoint ins.current.insn[31:20] {
            bins sip = {CSR_SIP};
            bins sie = {CSR_SIE};
        }
        satp : coverpoint ins.current.insn[31:20] {
            bins satp = {CSR_SATP};
        }
        mstatus_tvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm")[0] {
        }

        cp_scsr_from_m :            cross priv_mode_m, scsrname, csraccesses;
        cp_scause_from_m :          cross priv_mode_m, csrrw, scause_csr, scause_wlrl_values;
        cp_satp_from_m :            cross priv_mode_m, csrr, satp, mstatus_tvm;
        cp_satp_from_s :            cross priv_mode_s, csrr, satp, mstatus_tvm;
        cp_shadow :                 cross priv_mode_m, shadow, csrw_prev, rs1_prev, csrr;
        // sip/sie alias mip/mie only for delegated interrupts
        cp_shadow_deleg :           cross priv_mode_m, shadow_int, csrw_prev, csrr, mideleg_s;
        // delegate one interrupt at a time and read sip/sie
        cp_shadow_deleg_walk :      cross priv_mode_m, csrr, sip_sie, mideleg_s_walking;
    `endif

endgroup

// Sm_F, Sm_V and Sm_VF tests (Sm_F-NN.S, Sm_V_*-NN.S, Sm_VF-NN.S) are part of the Sm suite
// and run only when F, Zve32x or Zve32f is also supported.
`ifdef F_SUPPORTED
covergroup Sm_F_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_f_coverpoints.svh"

    mstatus_FS: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins off     = {2'b00};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins initial_state = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean   = {2'b10};
        `endif
        bins dirty   = {2'b11};
    }
    mstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }

    // main coverpoints
    cp_fcsr_access:           cross priv_mode_m, fcsrname, csraccesses, mstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with mstatus.FS
    cp_mstatus_FS_transition: cross priv_mode_m, deterministic_instrs, mstatus_FS;
    cp_mstatus_FS_transition_nondeterministic: cross priv_mode_m, nondeterministic_instrs, mstatus_FS_off_dirty;
endgroup
`endif

// Sm_V_cg and Sm_VF_cg written by James (Kaden) Cassidy jacassidy@hmc.edu May 29 2025
`ifdef ZVE32X_SUPPORTED
covergroup Sm_V_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_v_coverpoints.svh"

    // crosses of the shared vector coverpoints
    cp_vcsrrswc                 : cross priv_mode_m, vcsrs, csrops;
    cp_vcsrs_walking1s          : cross priv_mode_m, writable_vcsrs, csrw, walking_ones_rs1;
    cp_sew_lmul_vsetvl          : cross priv_mode_m, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew {
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
    cp_sew_lmul_vset_i_vli      : cross priv_mode_m, vset_i_vli_instructions, vset_sew, vset_lmul {
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
    cp_vill_vsetvl              : cross priv_mode_m, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal, rs2_sew_all_supported, rs2_lmul_8;
    cp_vill_vset_i_vli          : cross priv_mode_m, vset_i_vli_instructions, vtype_prev_vill_set, current_vset_sew_all_supported, current_vset_lmul_8;
    cp_vill_vsetvl_rs2_vill     : cross priv_mode_m, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal_no_msb, rs2_sew_all_supported, rs2_lmul_8, rs2_vill_set;
    cp_vsetvl_rs2_vill          : cross priv_mode_m, vsetvl_instruction, rs2_vill_set, rs2_sew_supported, rs2_lmul_1, rs2_vtype_legal_no_msb, vtype_prev_vill_clear;
    cp_vtype_vill_set_vl_0      : cross priv_mode_m, vsetvl_instruction, rs1_non_zero, rs2_vill_set, vl_nonzero;
    cp_vsetvl_i_rd_nx0_rs1_x0   : cross priv_mode_m, vsetvl_i_instructions, vl_not_max, rd_n0, rs1_x0, vtype_all_sew_supported, vtype_all_lmul_supported {
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
    cp_vsetvl_i_rd_x0_rs1_x0    : cross priv_mode_m, vsetvl_i_instructions, vl_nonzero, rd_x0, rs1_x0, vset_i_vli_vlmax_unchanged;
    cp_vsetvl_i_avl_eq_zero     : cross priv_mode_m, vsetvl_i_instructions, rs1_eq_zero;
    cp_vsetvl_i_avl_eq_vlmax    : cross priv_mode_m, vsetvl_i_instructions, rs1_eq_vlmax;
    cp_vsetvl_i_avl_lt_2x_vlmax : cross priv_mode_m, vsetvl_i_instructions, rs1_lt_2x_vlmax_gt_vlmax;
    cp_vsetvl_i_avl_eq_2x_vlmax : cross priv_mode_m, vsetvl_i_instructions, rs1_eq_2x_vlmax;
    cp_vsetvl_i_avl_gt_2x_vlmax : cross priv_mode_m, vsetvl_i_instructions, rs1_gt_2x_vlmax;
    cp_vsetivli_avl_edges       : cross priv_mode_m, vsetivli_instruction, vtype_all_sew_supported, imm5_edges, vtype_lmul_1;
    cp_vstart_out_of_bounds     : cross priv_mode_m, vstart_csr, csr_write, rs1_2_to_16;
    cp_vl_walking1s_sew_lmul    : cross priv_mode_m, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1 {
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
    // cp_mstatus_vs_*
    // tests mstatus ability to set clean and initial to dirty only when supposed to
    //////////////////////////////////////////////////////////////////////////////////

    // Initial and Clean only when MSTATUS_VS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    mstatus_vs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    mstatus_vs_inactive    : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    cp_mstatus_vs_set_dirty_arithmetic  : cross priv_mode_m, std_vec,        vector_vector_arithmetic_instruction,   mstatus_vs_on;
    cp_mstatus_vs_set_dirty_csr         : cross priv_mode_m, std_vec,        vsetvli_instruction,                    mstatus_vs_on;
    cp_mstatus_vs_set_dirty_vcsr        : cross priv_mode_m, vcsrs_writable, csrops,                                 mstatus_vs_on;

    cp_mstatus_vs_off_arithmetic        : cross priv_mode_m, mstatus_vs_inactive,     vector_vector_arithmetic_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );
    cp_mstatus_vs_off_csr               : cross priv_mode_m, mstatus_vs_inactive,     vsetvli_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );

endgroup
`endif

`ifdef ZVE32F_SUPPORTED
covergroup Sm_VF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_vf_coverpoints.svh"

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    // Initial and Clean only when MSTATUS_FS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    mstatus_fs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    mstatus_fs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins off = {0};
    }

    cp_vectorfp_mstatus_fs_state_affecting_register : cross priv_mode_m, std_vec, vfmv_f_s, mstatus_fs_on;
    cp_vectorfp_mstatus_fs_state_affecting_csr      : cross priv_mode_m, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_on, fflags_modified_after_clear;
    cp_vectorfp_mstatus_fs_state_nonaffecting       : cross priv_mode_m, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_on, vs1_zero, vs2_zero;
    cp_vectorfp_mstatus_fs_off                      : cross priv_mode_m, std_trap_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_off, vs1_zero, vs2_zero;

endgroup
`endif

`ifdef ZICNTR_SUPPORTED
covergroup Sm_Zicntr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    csraccess: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }
    counters_mcounteren: coverpoint {ins.current.insn[31:20], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[31:0] } {
      bins cycle_enabled         = {44'b110000000000_00000000000000000000000000000001};
      bins time_enabled          = {44'b110000000001_00000000000000000000000000000010};
      bins instret_enabled       = {44'b110000000010_00000000000000000000000000000100};
      `ifdef ZIHPM_SUPPORTED
        `ifdef UDB_HPM_COUNTER_EN_3
          bins hpmcounter3_enabled   = {44'b110000000011_00000000000000000000000000001000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_4
          bins hpmcounter4_enabled   = {44'b110000000100_00000000000000000000000000010000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_5
          bins hpmcounter5_enabled   = {44'b110000000101_00000000000000000000000000100000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_6
          bins hpmcounter6_enabled   = {44'b110000000110_00000000000000000000000001000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_7
          bins hpmcounter7_enabled   = {44'b110000000111_00000000000000000000000010000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_8
          bins hpmcounter8_enabled   = {44'b110000001000_00000000000000000000000100000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_9
          bins hpmcounter9_enabled   = {44'b110000001001_00000000000000000000001000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_10
          bins hpmcounter10_enabled  = {44'b110000001010_00000000000000000000010000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_11
          bins hpmcounter11_enabled  = {44'b110000001011_00000000000000000000100000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_12
          bins hpmcounter12_enabled  = {44'b110000001100_00000000000000000001000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_13
          bins hpmcounter13_enabled  = {44'b110000001101_00000000000000000010000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_14
          bins hpmcounter14_enabled  = {44'b110000001110_00000000000000000100000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_15
          bins hpmcounter15_enabled  = {44'b110000001111_00000000000000001000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_16
          bins hpmcounter16_enabled  = {44'b110000010000_00000000000000010000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_17
          bins hpmcounter17_enabled  = {44'b110000010001_00000000000000100000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_18
          bins hpmcounter18_enabled  = {44'b110000010010_00000000000001000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_19
          bins hpmcounter19_enabled  = {44'b110000010011_00000000000010000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_20
          bins hpmcounter20_enabled  = {44'b110000010100_00000000000100000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_21
          bins hpmcounter21_enabled  = {44'b110000010101_00000000001000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_22
          bins hpmcounter22_enabled  = {44'b110000010110_00000000010000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_23
          bins hpmcounter23_enabled  = {44'b110000010111_00000000100000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_24
          bins hpmcounter24_enabled  = {44'b110000011000_00000001000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_25
          bins hpmcounter25_enabled  = {44'b110000011001_00000010000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_26
          bins hpmcounter26_enabled  = {44'b110000011010_00000100000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_27
          bins hpmcounter27_enabled  = {44'b110000011011_00001000000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_28
          bins hpmcounter28_enabled  = {44'b110000011100_00010000000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_29
          bins hpmcounter29_enabled  = {44'b110000011101_00100000000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_30
          bins hpmcounter30_enabled  = {44'b110000011110_01000000000000000000000000000000};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_31
          bins hpmcounter31_enabled  = {44'b110000011111_10000000000000000000000000000000};
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
          bins cycleh_enabled         = {44'b110010000000_00000000000000000000000000000001};
          bins timeh_enabled          = {44'b110010000001_00000000000000000000000000000010};
          bins instreth_enabled       = {44'b110010000010_00000000000000000000000000000100};
          `ifdef ZIHPM_SUPPORTED
            `ifdef UDB_HPM_COUNTER_EN_3
              bins hpmcounter3h_enabled   = {44'b110010000011_00000000000000000000000000001000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_4
              bins hpmcounter4h_enabled   = {44'b110010000100_00000000000000000000000000010000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_5
              bins hpmcounter5h_enabled   = {44'b110010000101_00000000000000000000000000100000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_6
              bins hpmcounter6h_enabled   = {44'b110010000110_00000000000000000000000001000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_7
              bins hpmcounter7h_enabled   = {44'b110010000111_00000000000000000000000010000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_8
              bins hpmcounter8h_enabled   = {44'b110010001000_00000000000000000000000100000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_9
              bins hpmcounter9h_enabled   = {44'b110010001001_00000000000000000000001000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_10
              bins hpmcounter10h_enabled  = {44'b110010001010_00000000000000000000010000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_11
              bins hpmcounter11h_enabled  = {44'b110010001011_00000000000000000000100000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_12
              bins hpmcounter12h_enabled  = {44'b110010001100_00000000000000000001000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_13
              bins hpmcounter13h_enabled  = {44'b110010001101_00000000000000000010000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_14
              bins hpmcounter14h_enabled  = {44'b110010001110_00000000000000000100000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_15
              bins hpmcounter15h_enabled  = {44'b110010001111_00000000000000001000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_16
              bins hpmcounter16h_enabled  = {44'b110010010000_00000000000000010000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_17
              bins hpmcounter17h_enabled  = {44'b110010010001_00000000000000100000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_18
              bins hpmcounter18h_enabled  = {44'b110010010010_00000000000001000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_19
              bins hpmcounter19h_enabled  = {44'b110010010011_00000000000010000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_20
              bins hpmcounter20h_enabled  = {44'b110010010100_00000000000100000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_21
              bins hpmcounter21h_enabled  = {44'b110010010101_00000000001000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_22
              bins hpmcounter22h_enabled  = {44'b110010010110_00000000010000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_23
              bins hpmcounter23h_enabled  = {44'b110010010111_00000000100000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_24
              bins hpmcounter24h_enabled  = {44'b110010011000_00000001000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_25
              bins hpmcounter25h_enabled  = {44'b110010011001_00000010000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_26
              bins hpmcounter26h_enabled  = {44'b110010011010_00000100000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_27
              bins hpmcounter27h_enabled  = {44'b110010011011_00001000000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_28
              bins hpmcounter28h_enabled  = {44'b110010011100_00010000000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_29
              bins hpmcounter29h_enabled  = {44'b110010011101_00100000000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_30
              bins hpmcounter30h_enabled  = {44'b110010011110_01000000000000000000000000000000};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_31
              bins hpmcounter31h_enabled  = {44'b110010011111_10000000000000000000000000000000};
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
          `endif // ZIHPM_SUPPORTED
      `endif // UDB_MXLEN_32
    }

    `ifdef U_SUPPORTED
        cp_mcounteren_access_m: cross csraccess, counters_mcounteren, priv_mode_m;
    `endif

    `ifdef S_SUPPORTED
      mcounteren: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren"){
          bins ones  = {32'b11111111111111111111111111111111};
          bins zeros = {32'b00000000000000000000000000000000};
      }
      counters_scounteren: coverpoint {ins.current.insn[31:20], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scounteren", "scounteren")[31:0]} {
        bins cycle_enabled         = {44'b110000000000_00000000000000000000000000000001};
        bins time_enabled          = {44'b110000000001_00000000000000000000000000000010};
        bins instret_enabled       = {44'b110000000010_00000000000000000000000000000100};
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3_enabled   = {44'b110000000011_00000000000000000000000000001000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4_enabled   = {44'b110000000100_00000000000000000000000000010000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5_enabled   = {44'b110000000101_00000000000000000000000000100000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6_enabled   = {44'b110000000110_00000000000000000000000001000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7_enabled   = {44'b110000000111_00000000000000000000000010000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8_enabled   = {44'b110000001000_00000000000000000000000100000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9_enabled   = {44'b110000001001_00000000000000000000001000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10_enabled  = {44'b110000001010_00000000000000000000010000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11_enabled  = {44'b110000001011_00000000000000000000100000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12_enabled  = {44'b110000001100_00000000000000000001000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13_enabled  = {44'b110000001101_00000000000000000010000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14_enabled  = {44'b110000001110_00000000000000000100000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15_enabled  = {44'b110000001111_00000000000000001000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16_enabled  = {44'b110000010000_00000000000000010000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17_enabled  = {44'b110000010001_00000000000000100000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18_enabled  = {44'b110000010010_00000000000001000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19_enabled  = {44'b110000010011_00000000000010000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20_enabled  = {44'b110000010100_00000000000100000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21_enabled  = {44'b110000010101_00000000001000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22_enabled  = {44'b110000010110_00000000010000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23_enabled  = {44'b110000010111_00000000100000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24_enabled  = {44'b110000011000_00000001000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25_enabled  = {44'b110000011001_00000010000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26_enabled  = {44'b110000011010_00000100000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27_enabled  = {44'b110000011011_00001000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28_enabled  = {44'b110000011100_00010000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29_enabled  = {44'b110000011101_00100000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30_enabled  = {44'b110000011110_01000000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31_enabled  = {44'b110000011111_10000000000000000000000000000000};
          `endif
        `endif // ZIHPM_SUPPORTED

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
        `endif // ZIHPM_SUPPORTED

        `ifdef UDB_MXLEN_32
            bins cycleh_enabled         = {44'b110010000000_00000000000000000000000000000001};
            bins timeh_enabled          = {44'b110010000001_00000000000000000000000000000010};
            bins instreth_enabled       = {44'b110010000010_00000000000000000000000000000100};
            `ifdef ZIHPM_SUPPORTED
              `ifdef UDB_HPM_COUNTER_EN_3
                bins hpmcounter3h_enabled   = {44'b110010000011_00000000000000000000000000001000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_4
                bins hpmcounter4h_enabled   = {44'b110010000100_00000000000000000000000000010000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_5
                bins hpmcounter5h_enabled   = {44'b110010000101_00000000000000000000000000100000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_6
                bins hpmcounter6h_enabled   = {44'b110010000110_00000000000000000000000001000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_7
                bins hpmcounter7h_enabled   = {44'b110010000111_00000000000000000000000010000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_8
                bins hpmcounter8h_enabled   = {44'b110010001000_00000000000000000000000100000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_9
                bins hpmcounter9h_enabled   = {44'b110010001001_00000000000000000000001000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_10
                bins hpmcounter10h_enabled  = {44'b110010001010_00000000000000000000010000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_11
                bins hpmcounter11h_enabled  = {44'b110010001011_00000000000000000000100000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_12
                bins hpmcounter12h_enabled  = {44'b110010001100_00000000000000000001000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_13
                bins hpmcounter13h_enabled  = {44'b110010001101_00000000000000000010000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_14
                bins hpmcounter14h_enabled  = {44'b110010001110_00000000000000000100000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_15
                bins hpmcounter15h_enabled  = {44'b110010001111_00000000000000001000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_16
                bins hpmcounter16h_enabled  = {44'b110010010000_00000000000000010000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_17
                bins hpmcounter17h_enabled  = {44'b110010010001_00000000000000100000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_18
                bins hpmcounter18h_enabled  = {44'b110010010010_00000000000001000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_19
                bins hpmcounter19h_enabled  = {44'b110010010011_00000000000010000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_20
                bins hpmcounter20h_enabled  = {44'b110010010100_00000000000100000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_21
                bins hpmcounter21h_enabled  = {44'b110010010101_00000000001000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_22
                bins hpmcounter22h_enabled  = {44'b110010010110_00000000010000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_23
                bins hpmcounter23h_enabled  = {44'b110010010111_00000000100000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_24
                bins hpmcounter24h_enabled  = {44'b110010011000_00000001000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_25
                bins hpmcounter25h_enabled  = {44'b110010011001_00000010000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_26
                bins hpmcounter26h_enabled  = {44'b110010011010_00000100000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_27
                bins hpmcounter27h_enabled  = {44'b110010011011_00001000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_28
                bins hpmcounter28h_enabled  = {44'b110010011100_00010000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_29
                bins hpmcounter29h_enabled  = {44'b110010011101_00100000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_30
                bins hpmcounter30h_enabled  = {44'b110010011110_01000000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_31
                bins hpmcounter31h_enabled  = {44'b110010011111_10000000000000000000000000000000};
              `endif
            `endif // ZIHPM_SUPPORTED

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
            `endif // ZIHPM_SUPPORTED
        `endif //UDB_MXLEN_32
      }

      cp_scounteren_access_m: cross csraccess, counters_scounteren, mcounteren, priv_mode_m;

    `endif // S_SUPPORTED

    // ---- minstret delta coverpoints ----

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    insn_lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    adr_misaligned_1: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        bins one = {3'b001};  // scratch + 1
    }
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
    `endif
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    mstatus_mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
        bins one = {1};
    }

    insn_add: coverpoint ins.current.insn {
        wildcard bins add = {ADD};
    }
    insn_mret: coverpoint ins.current.insn {
        wildcard bins mret = {MRET};
    }
    insn_sret: coverpoint ins.current.insn {
        wildcard bins sret = {SRET};
    }
    `ifdef ZAWRS_SUPPORTED
        wrs_nto: coverpoint ins.current.insn {
            bins wrs_nto = {WRS_NTO};
        }
        wrs_sto: coverpoint ins.current.insn {
            bins wrs_sto = {WRS_STO};
        }
    `endif

    prev_minstret_read: coverpoint ins.prev.insn {
        wildcard bins csrr_minstret = {32'b101100000010_00000_010_?????_1110011};
    }
    prev_ecall_li: coverpoint ins.prev.insn {
        bins li_a0 = {32'h07300513};  // addi a0, x0, 0x73 (RVTEST_TSBI_ECALL_TEST)
    }
    mip_mtip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mtip")[0] {
        bins one = {1};
    }
    mie_mtie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mtie")[0] {
        bins one = {1};
    }
    mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[31:0] {
        bins zero = {0};
    }

    // retiring instructions
    cp_instret_add:  cross priv_mode_m, insn_add, prev_minstret_read;
    cp_instret_mret: cross priv_mode_m, insn_mret, prev_minstret_read;
    `ifdef S_SUPPORTED
        cp_instret_sret: cross priv_mode_m, insn_sret, prev_minstret_read;
    `endif

    // instructions that trap before retiring
    cp_instret_ecall:  cross priv_mode_m, ecall, prev_ecall_li;
    cp_instret_ebreak: cross priv_mode_m, ebreak, prev_minstret_read;
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        cp_instret_load_access_fault: cross priv_mode_m, insn_lw, illegal_address, prev_minstret_read;
    `endif
    cp_instret_load_misaligned: cross priv_mode_m, insn_lw, adr_misaligned_1, prev_minstret_read;

    // wfi and wrs
    `ifdef UDB_WFI_FINITE
        cp_instret_wfi_timeout: cross priv_mode_m, wfi, mie_zero, prev_minstret_read;
    `endif
    `ifdef UDB_MTI_INTR_IMPL
        cp_instret_wfi_pending: cross priv_mode_m, wfi, mip_mtip_one, mie_mtie_one, mstatus_mie_zero, prev_minstret_read;
        cp_instret_wfi_taken:   cross priv_mode_m, wfi, mie_mtie_one, mstatus_mie_one;
    `endif
    `ifdef ZAWRS_SUPPORTED
        cp_instret_wrs_nto: cross priv_mode_m, wrs_nto, prev_minstret_read;
        cp_instret_wrs_sto: cross priv_mode_m, wrs_sto, prev_minstret_read;
    `endif

endgroup
`endif

`ifdef H_SUPPORTED
`include "general/RISCV_coverage_hypervisor.svh"

covergroup Sm_H_mcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }
    csraccesses_masked : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val != 0); // csrc mask
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val == 0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val != 0); // csrw mask
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val != 0); // csrs mask
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val == 0); // csrr
    }
    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // Machine, HS and VS H-extension CSRs accessed and walked without masked writes.  Keep in sync with HCommon.py.
    hcsrname : coverpoint ins.current.insn[31:20] {
        bins hedeleg    = {CSR_HEDELEG};
        bins hideleg    = {CSR_HIDELEG};
        bins hie        = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie      = {CSR_HGEIE};
        bins hip        = {CSR_HIP};
        bins hvip       = {CSR_HVIP};
        `ifdef ZICNTR_SUPPORTED
            bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        bins vsstatus   = {CSR_VSSTATUS};
        bins vsie       = {CSR_VSIE};
        bins vstval     = {CSR_VSTVAL};
        bins vsip       = {CSR_VSIP};
        bins vstvec     = {CSR_VSTVEC};
        bins vsscratch  = {CSR_VSSCRATCH};
        bins vsepc      = {CSR_VSEPC};
        `ifdef SSTC_SUPPORTED
            bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef ZICNTR_SUPPORTED
                bins htimedeltah = {CSR_HTIMEDELTAH};
            `endif
            `ifdef SSTC_SUPPORTED
                bins vstimecmph = {CSR_VSTIMECMPH};
            `endif
        `endif
    }
    // CSRs that need only hold zero: the readback is checked after writing zero and after clearing every bit
    hcsrname_zero : coverpoint ins.current.insn[31:20] {
        bins mtval2 = {CSR_MTVAL2};
        bins mtinst = {CSR_MTINST};
        bins htval  = {CSR_HTVAL};
        bins htinst = {CSR_HTINST};
        bins hgatp  = {CSR_HGATP};
        bins vsatp  = {CSR_VSATP};
        `ifdef UDB_MXLEN_32
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins hedelegh = {CSR_HEDELEGH};
            `endif
        `endif
    }
    // CSRs whose access and walk tests write only the checked fields
    hcsrname_masked : coverpoint ins.current.insn[31:20] {
        bins hstatus = {CSR_HSTATUS};
        bins henvcfg = {CSR_HENVCFG};
        `ifdef UDB_MXLEN_32
            bins henvcfgh = {CSR_HENVCFGH};
        `endif
    }
    hgeip : coverpoint ins.current.insn[31:20] {
        bins hgeip = {CSR_HGEIP};
    }

    cp_hcsr_access:         cross priv_mode_m, hcsrname, csraccesses;
    cp_hcsr_access_zero:    cross priv_mode_m, hcsrname_zero, csraccesses;
    cp_hcsr_access_masked:  cross priv_mode_m, hcsrname_masked, csraccesses_masked;
    cp_hcsr_access_ro:      cross priv_mode_m, hgeip, csraccesses;
    cp_hcsrwalk:            cross priv_mode_m, hcsrname, csrop, walking_ones {
        // vsepc and vstval may legalize invalid addresses, so they are walked with valid addresses instead
        ignore_bins vaddr = binsof(hcsrname.vsepc) || binsof(hcsrname.vstval);
    }
    // Keep the lists below in sync with the masks in HCommon.py
    cp_hcsrwalk_masked:     cross priv_mode_m, hcsrname_masked, csrop, walking_ones {
        ignore_bins hstatus_not_walked = binsof(hcsrname_masked.hstatus) &&
            binsof(walking_ones) intersect {[0:5], [10:19], [23:63]};
        ignore_bins henvcfg_not_walked = binsof(hcsrname_masked.henvcfg) &&
            binsof(walking_ones) intersect {1, [8:31], [34:60]};
        `ifdef UDB_MXLEN_32
            ignore_bins henvcfgh_not_walked = binsof(hcsrname_masked.henvcfgh) &&
                binsof(walking_ones) intersect {[2:28]};
        `endif
    }

    // hgatp and vsatp: walk a 1 and a 0 through the non-MODE bits with a legal MODE
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    atpname : coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39X4_TRANSLATION
                bins hgatp = {CSR_HGATP};
            `endif
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins vsatp = {CSR_VSATP};
            `endif
        `else
            `ifdef UDB_SV32X4_TRANSLATION
                bins hgatp = {CSR_HGATP};
            `endif
            `ifdef UDB_SV32_VSMODE_TRANSLATION
                bins vsatp = {CSR_VSATP};
            `endif
        `endif
    }
    `ifdef UDB_MXLEN_64
        atp_walk1 : coverpoint $clog2(ins.current.rs1_val[59:0])
            iff (ins.current.rs1_val[63:60] == 8 && $onehot(ins.current.rs1_val[59:0])) {
            bins b[] = {[0:59]};
        }
        atp_walk0 : coverpoint $clog2(~ins.current.rs1_val[59:0])
            iff (ins.current.rs1_val[63:60] == 8 && $onehot(~ins.current.rs1_val[59:0])) {
            bins b[] = {[0:59]};
        }
    `else
        atp_walk1 : coverpoint $clog2(ins.current.rs1_val[30:0])
            iff (ins.current.rs1_val[31] && $onehot(ins.current.rs1_val[30:0])) {
            bins b[] = {[0:30]};
        }
        atp_walk0 : coverpoint $clog2(~ins.current.rs1_val[30:0])
            iff (ins.current.rs1_val[31] && $onehot(~ins.current.rs1_val[30:0])) {
            bins b[] = {[0:30]};
        }
    `endif
    cp_atpwalk1:            cross priv_mode_m, csrrw, atpname, atp_walk1;
    cp_atpwalk0:            cross priv_mode_m, csrrw, atpname, atp_walk0;

    // vsepc and vstval hold every address that sepc and stval hold: the current pc, an address in scratch, and each
    // canonical virtual address with one bit walked.  vsepc bit 0 is always 0, and bit 1 is 0 unless Zca allows
    // 2-byte instruction alignment.
    vsepc : coverpoint ins.current.insn[31:20] {
        bins vsepc = {CSR_VSEPC};
    }
    vstval : coverpoint ins.current.insn[31:20] {
        bins vstval = {CSR_VSTVAL};
    }
    xaddr_pc : coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch : coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    cp_vsepc_vaddr_pc:       cross priv_mode_m, csrrw, vsepc, xaddr_pc;
    cp_vsepc_vaddr_scratch:  cross priv_mode_m, csrrw, vsepc, xaddr_scratch;
    cp_vstval_vaddr_pc:      cross priv_mode_m, csrrw, vstval, xaddr_pc;
    cp_vstval_vaddr_scratch: cross priv_mode_m, csrrw, vstval, xaddr_scratch;
    `ifdef H_VADDR_WALK_MSB
        vaddr_walk1 : coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`H_VADDR_WALK_MSB] };
        }
        vaddr_walk0 : coverpoint $clog2(~ins.current.rs1_val) iff ($onehot(~ins.current.rs1_val)) {
            bins b_0[] = { [0:`H_VADDR_WALK_MSB] };
        }
        cp_vsepc_vaddr_walk1:    cross priv_mode_m, csrrw, vsepc, vaddr_walk1;
        cp_vsepc_vaddr_walk0:    cross priv_mode_m, csrrw, vsepc, vaddr_walk0;
        cp_vstval_vaddr_walk1:   cross priv_mode_m, csrrw, vstval, vaddr_walk1;
        cp_vstval_vaddr_walk0:   cross priv_mode_m, csrrw, vstval, vaddr_walk0;
    `endif

    // Read an S CSR right after writing its VS replica
    csrw_prev : coverpoint ins.prev.insn {
        wildcard bins csrw = {CSRW};
    }
    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    replica_pair : coverpoint {ins.prev.insn[31:20], ins.current.insn[31:20]} {
        bins sstatus  = {{CSR_VSSTATUS, CSR_SSTATUS}};
        bins sie      = {{CSR_VSIE, CSR_SIE}};
        bins stvec    = {{CSR_VSTVEC, CSR_STVEC}};
        bins sscratch = {{CSR_VSSCRATCH, CSR_SSCRATCH}};
        bins sepc     = {{CSR_VSEPC, CSR_SEPC}};
        bins scause   = {{CSR_VSCAUSE, CSR_SCAUSE}};
        bins stval    = {{CSR_VSTVAL, CSR_STVAL}};
        bins sip      = {{CSR_VSIP, CSR_SIP}};
        // satp always supports Sv39 (RV64) or Sv32 (RV32), but vsatp need not
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins satp = {{CSR_VSATP, CSR_SATP}};
            `endif
        `elsif UDB_SV32_VSMODE_TRANSLATION
            bins satp = {{CSR_VSATP, CSR_SATP}};
        `endif
    }
    cp_replica:             cross priv_mode_m, csrw_prev, csrr, replica_pair;

    // In VS-mode, S CSR names access the VS replicas.  VS-mode ecalls go to M-mode, so M-mode can check that
    // the S CSRs keep their values
    csrw : coverpoint ins.current.insn {
        wildcard bins csrw = {CSRW};
    }
    sreplicated : coverpoint ins.current.insn[31:20] {
        bins sstatus  = {CSR_SSTATUS};
        bins sie      = {CSR_SIE};
        bins stvec    = {CSR_STVEC};
        bins sscratch = {CSR_SSCRATCH};
        bins sepc     = {CSR_SEPC};
        bins scause   = {CSR_SCAUSE};
        bins stval    = {CSR_STVAL};
        bins sip      = {CSR_SIP};
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins satp = {CSR_SATP};
            `endif
        `elsif UDB_SV32_VSMODE_TRANSLATION
            bins satp = {CSR_SATP};
        `endif
    }
    cp_replica_vs:          cross priv_mode_vs, csrw, sreplicated;

    // mtval must not be read-only zero with H
    mtval : coverpoint ins.current.insn[31:20] {
        bins mtval = {CSR_MTVAL};
    }
    rs1_ones : coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }
    cp_mtvala:              cross priv_mode_m, csrrw, mtval, rs1_ones;

    // vsepc[1] is masked on reads, including sret's in VS-mode, while misa.C = 0 makes IALIGN = 32
    // Only on harts with Zca whose misa.C is writable, so that IALIGN can change
    `ifdef ZCA_SUPPORTED
        `ifdef UDB_MUTABLE_MISA_C
            csrr_vsepc : coverpoint ins.current.insn {
                wildcard bins csrr_vsepc = {CSRRS} iff (ins.current.insn[31:20] == CSR_VSEPC && ins.current.insn[19:15] == 0);
            }
            // In VS-mode the trace records vsepc accesses under sepc
            csrr_sepc : coverpoint ins.current.insn {
                wildcard bins csrr_sepc = {CSRRS} iff (ins.current.insn[31:20] == CSR_SEPC && ins.current.insn[19:15] == 0);
            }
            sret_insn : coverpoint ins.current.insn {
                wildcard bins sret = {SRET};
            }
            misa_c_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "exts")[2] {
                bins off = {1'b0};
            }
            vsepc_bit1 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsepc", "vsepc")[1] {
                bins set = {1'b1};
            }
            sepc_bit1 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sepc", "sepc")[1] {
                bins set = {1'b1};
            }
            cp_vsepc_ialign32_read :    cross priv_mode_m_s, csrr_vsepc,  misa_c_off, vsepc_bit1;
            cp_vsepc_ialign32_vs_read : cross priv_mode_vs, csrr_sepc, misa_c_off, sepc_bit1;
            cp_vsepc_ialign32_sret :    cross priv_mode_vs, sret_insn, misa_c_off, sepc_bit1;
        `endif
    `endif
endgroup

covergroup Sm_H_tvm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mstatus_tvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins off = {0};
        bins on  = {1};
    }
    hstatus_vtvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }
    csr_rw : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }
    // mstatus.TVM = 1 traps satp and hgatp accesses in HS-mode, but not vsatp accesses; hstatus.VTVM does not affect HS-mode
    atp_hs : coverpoint ins.current.insn[31:20] {
        bins satp  = {CSR_SATP};
        bins hgatp = {CSR_HGATP};
        bins vsatp = {CSR_VSATP};
    }
    satp : coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }
    hfence : coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    sfence : coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }

    cp_tvm_hs:  cross priv_mode_hs, atp_hs, csr_rw, mstatus_tvm, hstatus_vtvm;
    cp_tvm_vs:  cross priv_mode_vs, satp, csr_rw, mstatus_tvm, hstatus_vtvm;
    cp_hfence:  cross priv_mode_m_hs_vs_u_vu, hfence, mstatus_tvm, hstatus_vtvm;
    cp_sfence:  cross priv_mode_m_hs_vs_u_vu, sfence, mstatus_tvm, hstatus_vtvm;
endgroup

covergroup Sm_H_inst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef H_TWO_STAGE
        hlv : coverpoint ins.current.insn {
            wildcard bins hlv_b  = {HLV_B};
            wildcard bins hlv_bu = {HLV_BU};
            wildcard bins hlv_h  = {HLV_H};
            wildcard bins hlv_hu = {HLV_HU};
            wildcard bins hlv_w  = {HLV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hlv_wu = {HLV_WU};
                wildcard bins hlv_d  = {HLV_D};
            `endif
        }
        hlvx : coverpoint ins.current.insn {
            wildcard bins hlvx_hu = {HLVX_HU};
            wildcard bins hlvx_wu = {HLVX_WU};
        }
        hsv : coverpoint ins.current.insn {
            wildcard bins hsv_b = {HSV_B};
            wildcard bins hsv_h = {HSV_H};
            wildcard bins hsv_w = {HSV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hsv_d = {HSV_D};
            `endif
        }
        cp_hlv:  cross priv_mode_m, hlv;
        cp_hlvx: cross priv_mode_m, hlvx;
        cp_hsv:  cross priv_mode_m, hsv;

        hlv_hsv : coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare  = {0};
            bins paged = {[1:15]};
        }
        guest_page_fault : coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
            bins load_store = {6'b110101, 6'b110111};
        }
        // Guest-page faults on the final translation (vsatp Bare) and on an implicit VS-stage access
        cp_guest_page_fault: cross priv_mode_m, hlv_hsv, vsatp_mode, guest_page_fault;
    `endif

    mret : coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    sret : coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    old_mpp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins u = {0};
        bins s = {1};
        bins m = {3};
    }
    `ifdef UDB_MXLEN_64
        old_mpv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv") {
    `else
        old_mpv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv") {
    `endif
        bins off = {0};
        bins on  = {1};
    }
    old_mpie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie") {
        bins off = {0};
        bins on  = {1};
    }
    old_spp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spp") {
        bins u = {0};
        bins s = {1};
    }
    old_spie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spie") {
        bins off = {0};
        bins on  = {1};
    }
    old_spv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") {
        bins off = {0};
        bins on  = {1};
    }

    cp_mret_m:  cross priv_mode_m, mret, old_mpp, old_mpv, old_mpie;
    cp_sret_m:  cross priv_mode_m, sret, old_spp, old_spv, old_spie;
endgroup
`endif

// Counter reads and htimedelta observed from M-mode with H.
// Written: David_Harris@hmc.edu 24 September 2026
`ifdef ZICNTR_SUPPORTED
`ifdef H_SUPPORTED
covergroup Sm_Zicntr_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // The counter accessed: one that exists and whose mcounteren, hcounteren and scounteren bits are writable
    counter: coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MCOUNTENABLE_EN_0 `ifdef UDB_HCOUNTENABLE_EN_0 `ifdef UDB_SCOUNTENABLE_EN_0
            bins cycle_csr = {CSR_CYCLE};
            `ifdef UDB_MXLEN_32
                bins cycleh_csr = {CSR_CYCLEH};
            `endif
        `endif `endif `endif
        `ifdef UDB_MCOUNTENABLE_EN_1 `ifdef UDB_HCOUNTENABLE_EN_1 `ifdef UDB_SCOUNTENABLE_EN_1
            bins time_csr = {CSR_TIME};
            `ifdef UDB_MXLEN_32
                bins timeh_csr = {CSR_TIMEH};
            `endif
        `endif `endif `endif
        `ifdef UDB_MCOUNTENABLE_EN_2 `ifdef UDB_HCOUNTENABLE_EN_2 `ifdef UDB_SCOUNTENABLE_EN_2
            bins instret_csr = {CSR_INSTRET};
            `ifdef UDB_MXLEN_32
                bins instreth_csr = {CSR_INSTRETH};
            `endif
        `endif `endif `endif
        `ifdef ZIHPM_SUPPORTED
            `ifdef UDB_HPM_COUNTER_EN_3 `ifdef UDB_MCOUNTENABLE_EN_3 `ifdef UDB_HCOUNTENABLE_EN_3 `ifdef UDB_SCOUNTENABLE_EN_3
                bins hpmcounter3_csr = {CSR_HPMCOUNTER3};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter3h_csr = {CSR_HPMCOUNTER3H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_4 `ifdef UDB_MCOUNTENABLE_EN_4 `ifdef UDB_HCOUNTENABLE_EN_4 `ifdef UDB_SCOUNTENABLE_EN_4
                bins hpmcounter4_csr = {CSR_HPMCOUNTER4};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter4h_csr = {CSR_HPMCOUNTER4H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_5 `ifdef UDB_MCOUNTENABLE_EN_5 `ifdef UDB_HCOUNTENABLE_EN_5 `ifdef UDB_SCOUNTENABLE_EN_5
                bins hpmcounter5_csr = {CSR_HPMCOUNTER5};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter5h_csr = {CSR_HPMCOUNTER5H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_6 `ifdef UDB_MCOUNTENABLE_EN_6 `ifdef UDB_HCOUNTENABLE_EN_6 `ifdef UDB_SCOUNTENABLE_EN_6
                bins hpmcounter6_csr = {CSR_HPMCOUNTER6};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter6h_csr = {CSR_HPMCOUNTER6H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_7 `ifdef UDB_MCOUNTENABLE_EN_7 `ifdef UDB_HCOUNTENABLE_EN_7 `ifdef UDB_SCOUNTENABLE_EN_7
                bins hpmcounter7_csr = {CSR_HPMCOUNTER7};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter7h_csr = {CSR_HPMCOUNTER7H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_8 `ifdef UDB_MCOUNTENABLE_EN_8 `ifdef UDB_HCOUNTENABLE_EN_8 `ifdef UDB_SCOUNTENABLE_EN_8
                bins hpmcounter8_csr = {CSR_HPMCOUNTER8};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter8h_csr = {CSR_HPMCOUNTER8H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_9 `ifdef UDB_MCOUNTENABLE_EN_9 `ifdef UDB_HCOUNTENABLE_EN_9 `ifdef UDB_SCOUNTENABLE_EN_9
                bins hpmcounter9_csr = {CSR_HPMCOUNTER9};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter9h_csr = {CSR_HPMCOUNTER9H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_10 `ifdef UDB_MCOUNTENABLE_EN_10 `ifdef UDB_HCOUNTENABLE_EN_10 `ifdef UDB_SCOUNTENABLE_EN_10
                bins hpmcounter10_csr = {CSR_HPMCOUNTER10};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter10h_csr = {CSR_HPMCOUNTER10H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_11 `ifdef UDB_MCOUNTENABLE_EN_11 `ifdef UDB_HCOUNTENABLE_EN_11 `ifdef UDB_SCOUNTENABLE_EN_11
                bins hpmcounter11_csr = {CSR_HPMCOUNTER11};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter11h_csr = {CSR_HPMCOUNTER11H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_12 `ifdef UDB_MCOUNTENABLE_EN_12 `ifdef UDB_HCOUNTENABLE_EN_12 `ifdef UDB_SCOUNTENABLE_EN_12
                bins hpmcounter12_csr = {CSR_HPMCOUNTER12};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter12h_csr = {CSR_HPMCOUNTER12H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_13 `ifdef UDB_MCOUNTENABLE_EN_13 `ifdef UDB_HCOUNTENABLE_EN_13 `ifdef UDB_SCOUNTENABLE_EN_13
                bins hpmcounter13_csr = {CSR_HPMCOUNTER13};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter13h_csr = {CSR_HPMCOUNTER13H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_14 `ifdef UDB_MCOUNTENABLE_EN_14 `ifdef UDB_HCOUNTENABLE_EN_14 `ifdef UDB_SCOUNTENABLE_EN_14
                bins hpmcounter14_csr = {CSR_HPMCOUNTER14};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter14h_csr = {CSR_HPMCOUNTER14H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_15 `ifdef UDB_MCOUNTENABLE_EN_15 `ifdef UDB_HCOUNTENABLE_EN_15 `ifdef UDB_SCOUNTENABLE_EN_15
                bins hpmcounter15_csr = {CSR_HPMCOUNTER15};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter15h_csr = {CSR_HPMCOUNTER15H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_16 `ifdef UDB_MCOUNTENABLE_EN_16 `ifdef UDB_HCOUNTENABLE_EN_16 `ifdef UDB_SCOUNTENABLE_EN_16
                bins hpmcounter16_csr = {CSR_HPMCOUNTER16};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter16h_csr = {CSR_HPMCOUNTER16H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_17 `ifdef UDB_MCOUNTENABLE_EN_17 `ifdef UDB_HCOUNTENABLE_EN_17 `ifdef UDB_SCOUNTENABLE_EN_17
                bins hpmcounter17_csr = {CSR_HPMCOUNTER17};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter17h_csr = {CSR_HPMCOUNTER17H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_18 `ifdef UDB_MCOUNTENABLE_EN_18 `ifdef UDB_HCOUNTENABLE_EN_18 `ifdef UDB_SCOUNTENABLE_EN_18
                bins hpmcounter18_csr = {CSR_HPMCOUNTER18};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter18h_csr = {CSR_HPMCOUNTER18H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_19 `ifdef UDB_MCOUNTENABLE_EN_19 `ifdef UDB_HCOUNTENABLE_EN_19 `ifdef UDB_SCOUNTENABLE_EN_19
                bins hpmcounter19_csr = {CSR_HPMCOUNTER19};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter19h_csr = {CSR_HPMCOUNTER19H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_20 `ifdef UDB_MCOUNTENABLE_EN_20 `ifdef UDB_HCOUNTENABLE_EN_20 `ifdef UDB_SCOUNTENABLE_EN_20
                bins hpmcounter20_csr = {CSR_HPMCOUNTER20};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter20h_csr = {CSR_HPMCOUNTER20H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_21 `ifdef UDB_MCOUNTENABLE_EN_21 `ifdef UDB_HCOUNTENABLE_EN_21 `ifdef UDB_SCOUNTENABLE_EN_21
                bins hpmcounter21_csr = {CSR_HPMCOUNTER21};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter21h_csr = {CSR_HPMCOUNTER21H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_22 `ifdef UDB_MCOUNTENABLE_EN_22 `ifdef UDB_HCOUNTENABLE_EN_22 `ifdef UDB_SCOUNTENABLE_EN_22
                bins hpmcounter22_csr = {CSR_HPMCOUNTER22};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter22h_csr = {CSR_HPMCOUNTER22H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_23 `ifdef UDB_MCOUNTENABLE_EN_23 `ifdef UDB_HCOUNTENABLE_EN_23 `ifdef UDB_SCOUNTENABLE_EN_23
                bins hpmcounter23_csr = {CSR_HPMCOUNTER23};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter23h_csr = {CSR_HPMCOUNTER23H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_24 `ifdef UDB_MCOUNTENABLE_EN_24 `ifdef UDB_HCOUNTENABLE_EN_24 `ifdef UDB_SCOUNTENABLE_EN_24
                bins hpmcounter24_csr = {CSR_HPMCOUNTER24};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter24h_csr = {CSR_HPMCOUNTER24H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_25 `ifdef UDB_MCOUNTENABLE_EN_25 `ifdef UDB_HCOUNTENABLE_EN_25 `ifdef UDB_SCOUNTENABLE_EN_25
                bins hpmcounter25_csr = {CSR_HPMCOUNTER25};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter25h_csr = {CSR_HPMCOUNTER25H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_26 `ifdef UDB_MCOUNTENABLE_EN_26 `ifdef UDB_HCOUNTENABLE_EN_26 `ifdef UDB_SCOUNTENABLE_EN_26
                bins hpmcounter26_csr = {CSR_HPMCOUNTER26};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter26h_csr = {CSR_HPMCOUNTER26H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_27 `ifdef UDB_MCOUNTENABLE_EN_27 `ifdef UDB_HCOUNTENABLE_EN_27 `ifdef UDB_SCOUNTENABLE_EN_27
                bins hpmcounter27_csr = {CSR_HPMCOUNTER27};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter27h_csr = {CSR_HPMCOUNTER27H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_28 `ifdef UDB_MCOUNTENABLE_EN_28 `ifdef UDB_HCOUNTENABLE_EN_28 `ifdef UDB_SCOUNTENABLE_EN_28
                bins hpmcounter28_csr = {CSR_HPMCOUNTER28};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter28h_csr = {CSR_HPMCOUNTER28H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_29 `ifdef UDB_MCOUNTENABLE_EN_29 `ifdef UDB_HCOUNTENABLE_EN_29 `ifdef UDB_SCOUNTENABLE_EN_29
                bins hpmcounter29_csr = {CSR_HPMCOUNTER29};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter29h_csr = {CSR_HPMCOUNTER29H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_30 `ifdef UDB_MCOUNTENABLE_EN_30 `ifdef UDB_HCOUNTENABLE_EN_30 `ifdef UDB_SCOUNTENABLE_EN_30
                bins hpmcounter30_csr = {CSR_HPMCOUNTER30};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter30h_csr = {CSR_HPMCOUNTER30H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_31 `ifdef UDB_MCOUNTENABLE_EN_31 `ifdef UDB_HCOUNTENABLE_EN_31 `ifdef UDB_SCOUNTENABLE_EN_31
                bins hpmcounter31_csr = {CSR_HPMCOUNTER31};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter31h_csr = {CSR_HPMCOUNTER31H};
                `endif
            `endif `endif `endif `endif
        `endif
    }

    // The enable bit of the accessed counter in mcounteren
    mcounteren_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[int'(ins.current.insn[24:20])] {
        bins disabled = {0};
        bins enabled  = {1};
    }

    csraccess: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }

    // htimedelta = {0, 2^30, 2^32-1, 2^60, -1, -2^30, -2^60} while time and timeh are read
    csrr_time: coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRR) {
        bins read_time = {CSR_TIME};
        `ifdef UDB_MXLEN_32
            bins read_timeh = {CSR_TIMEH};
        `endif
    }
    `ifdef UDB_MXLEN_64
        htimedelta: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedelta", "htimedelta") {
    `else
        htimedelta: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedeltah", "htimedeltah")[31:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedelta", "htimedelta")[31:0]} {
    `endif
        bins zero       = {64'h0000000000000000};
        bins pos_2p30   = {64'h0000000040000000};
        bins pos_2p32m1 = {64'h00000000FFFFFFFF};
        bins pos_2p60   = {64'h1000000000000000};
        bins neg_1      = {64'hFFFFFFFFFFFFFFFF};
        bins neg_2p30   = {64'hFFFFFFFFC0000000};
        bins neg_2p60   = {64'hF000000000000000};
    }

    // mcounteren, hcounteren and scounteren hold the same enable bit for the accessed counter
    cp_mhscounteren_access_m: cross csraccess, counter, mcounteren_bit, priv_mode_m
        iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[int'(ins.current.insn[24:20])] ==
                 get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hcounteren", "hcounteren")[int'(ins.current.insn[24:20])] &&
             get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[int'(ins.current.insn[24:20])] ==
                 get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scounteren", "scounteren")[int'(ins.current.insn[24:20])]);
    cp_delta_m: cross csrr_time, htimedelta, priv_mode_m;
endgroup
`endif
`endif

function void sm_sample(int hart, int issue, ins_t ins);
    Sm_mcause_cg.sample(ins);
    Sm_mstatus_cg.sample(ins);
    Sm_mprivinst_cg.sample(ins);
    Sm_mcsr_cg.sample(ins);
    `ifdef F_SUPPORTED
        Sm_F_cg.sample(ins);
    `endif
    `ifdef ZVE32X_SUPPORTED
        Sm_V_cg.sample(ins);
    `endif
    `ifdef ZVE32F_SUPPORTED
        Sm_VF_cg.sample(ins);
    `endif
    `ifndef EXCLUDE_SM
        `ifdef ZICNTR_SUPPORTED
            Sm_Zicntr_cg.sample(ins);
            `ifdef H_SUPPORTED
                Sm_Zicntr_H_cg.sample(ins);
            `endif
        `endif
        `ifdef H_SUPPORTED
            Sm_H_mcsr_cg.sample(ins);
            Sm_H_tvm_cg.sample(ins);
            Sm_H_inst_cg.sample(ins);
        `endif
        `ifdef H_SUPPORTED
            Sm_H_mcsr_cg.sample(ins);
            Sm_H_tvm_cg.sample(ins);
            Sm_H_inst_cg.sample(ins);
        `endif
    `endif
    //$display("Sm_sample: PC = %h (%s) misa %b rs1 %b, misa_c0 %b, pc_1 %b",
    //    ins.current.pc_rdata, ins.current.disass, ins.current.insn[31:20] == CSR_MISA, ins.current.rs1_val[25:0],
    //    ins.current.rs1_val[2], ins.current.pc_rdata[1]);
endfunction
