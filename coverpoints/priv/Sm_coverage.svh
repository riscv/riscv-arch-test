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

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    mcause: coverpoint ins.current.insn[31:20] {
        bins mcause = {CSR_MCAUSE};
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
    cp_mcause_write_exception: cross priv_mode_m, csrrw, mcause, mcause_exception_values, mcause_exception; // CSR write of mcause in M mode with interesting values
    cp_mcause_write_interrupt: cross priv_mode_m, csrrw, mcause, mcause_interrupt_values, mcause_interrupt; // CSR write of mcause in M mode with interesting values
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
endgroup

covergroup Sm_mcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mcsrname_ro : coverpoint ins.current.insn[31:20] { // extended set for access tests, including read-only CSRs
        bins mvendorid  = {CSR_MVENDORID};
        bins marchid    = {CSR_MARCHID};
        bins mimpid     = {CSR_MIMPID};
        bins mhartid    = {CSR_MHARTID};
        bins mconfigptr = {CSR_MCONFIGPTR};
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
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

    mcsrname : coverpoint ins.current.insn[31:20] { // excludes read-only CSRs
        bins mstatus    = {CSR_MSTATUS};
        bins medeleg    = {CSR_MEDELEG};
        bins mideleg    = {CSR_MIDELEG};
        bins mie        = {CSR_MIE};
        bins mtvec      = {CSR_MTVEC};
        bins mcounteren = {CSR_MCOUNTEREN};
        bins mscratch   = {CSR_MSCRATCH};
        bins mepc       = {CSR_MEPC};
        bins mcause     = {CSR_MCAUSE};
        bins mtval      = {CSR_MTVAL};
        bins mip        = {CSR_MIP};
        bins menvcfg    = {CSR_MENVCFG};
        bins mcountinhibit = {CSR_MCOUNTINHIBIT};
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
        `ifdef MSECCFG_SUPPORTED // update this in four places when UDB gives a name to this parameter
            bins mseccfg  = {CSR_MSECCFG};
        `endif
        `ifdef XLEN32
            bins mstatush = {CSR_MSTATUSH};
            // bins medelegh = {12'h312}; // move this to Sm1p13 coverpoints
            bins menvcfgh = {CSR_MENVCFGH};
            `ifdef MSECCFG_SUPPORTED // update this in four places when UDB gives a name to this parameter
                bins mseccfgh = {CSR_MSECCFGH};
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
        `ifdef XLEN32
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
        bins b_1[] = { [0:`XLEN-1] };
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
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }
    rs1_ones: coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }

    old_mcountinhibit_cy: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcountinhibit", "cy") {
        bins zero = {1'b0};
        `ifdef COUNTINHIBIT_EN_0
            bins one = {1'b1}; // only if counter can be inhibited
        `endif
    }
    old_mcountinhibit_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcountinhibit", "ir") {
        bins zero = {1'b0};
        `ifdef COUNTINHIBIT_EN_2
            bins one = {1'b1}; // only if counter can be inhibited
        `endif
    }

    mcycle: coverpoint ins.current.insn[31:20] {
        bins mcycle = {CSR_MCYCLE};
    }
    minstret: coverpoint ins.current.insn[31:20] {
        bins minstret = {CSR_MINSTRET};
    }
    time_csr: coverpoint ins.current.insn[31:20] {
        bins time_csr = {CSR_TIME};
    }
    `ifdef XLEN32
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
        wildcard bins csrc_11  = {CSRC} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b11); // clear misa.MXL
        wildcard bins csrs_11  = {CSRS} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b11); // set misa.MXL = 11
        wildcard bins csrw_00  = {CSRW} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b00); // write misa.MXL = 00
        wildcard bins csrw_01  = {CSRW} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b01); // write misa.MXL = 01
        wildcard bins csrw_10  = {CSRW} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b10); // write misa.MXL = 10
        wildcard bins csrw_11  = {CSRW} iff (ins.current.rs1_val[XLEN-1:XLEN-2] == 2'b11); // write misa.MXL = 11
        wildcard bins csrr     = {CSRR};                                                   // read misa
    }

    cp_mcsr_access:             cross priv_mode_m, mcsrname, csraccesses;
    cp_mcsr_access_ro:          cross priv_mode_m, mcsrname_ro, csraccesses;
    cp_mcsrwalk :               cross priv_mode_m, mcsrname, csrop, walking_ones;
    cp_csr_insufficient_priv:   cross priv_mode_m, csrr, csr_debug, nonzerord;
    cp_csr_ro:                  cross priv_mode_m, csrrw, csr_ro, rs1_ones;

    // counters
    cp_cntr_access :            cross priv_mode_m, mcounters, cntraccesses;
    cp_inhibit_mcycle :         cross priv_mode_m, csrr, mcycle, old_mcountinhibit_cy;
    cp_inhibit_minstret :       cross priv_mode_m, csrr, minstret, old_mcountinhibit_ir;

    // misa
    cp_misa_mxl :               cross priv_mode_m, misa, misa_mxl_accesses;

    `ifdef TIME_CSR_IMPLEMENTED
        cp_mtime_write :        cross priv_mode_m, csrr,  time_csr; // assumes mtime has been written
        `ifdef XLEN32
            cp_mtimeh_write :   cross priv_mode_m, csrr,  timeh_csr; // assumes mtimeh has been written
        `endif
    `endif
endgroup

function void sm_sample(int hart, int issue, ins_t ins);
    //if (ins.ins_str == "csrrw" || ins.ins_str == "csrrs" || ins.ins_str == "csrrc")
    //    $display("PC = %h (%s) csr = %h rs1_val = %h", ins.current.pc_rdata,ins.current.disass, ins.current.insn[31:20], ins.current.rs1_val);
    Sm_mcause_cg.sample(ins);
    Sm_mstatus_cg.sample(ins);
    Sm_mprivinst_cg.sample(ins);
    Sm_mcsr_cg.sample(ins);
endfunction
