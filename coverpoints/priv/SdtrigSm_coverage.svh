///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Pierce Clark pclark@hmc.edu 2 June 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SDTRIGSM
`define UDB_NUM_TRIGGERS 4 // TODO: replace with UDB param rvtest_config.svh

// TODO: gate per-trigger-type coverage behind the types the DUT actually supports.

covergroup SdtrigSm_sdtrig_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    trig_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins types[] = {[4'd0:4'd15]}; // all 16 trigger types
        ignore_bins reserved = {4'd1, [4'd8:4'd14]}; // reserved encoding
    }
    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    csr_common: coverpoint ins.current.insn[31:20] {
        bins tdata1    = {CSR_TDATA1};
        bins tdata2    = {CSR_TDATA2};
        bins tdata3    = {CSR_TDATA3};
        bins tinfo     = {CSR_TINFO};
        bins tcontrol  = {CSR_TCONTROL};
        bins scontext  = {CSR_SCONTEXT};
        bins mcontext  = {CSR_MCONTEXT};
        `ifdef H_SUPPORTED
            bins hcontext = {CSR_HCONTEXT};
        `endif
    }

    cp_sdtrig_csr_access_common: cross priv_mode_m, triggernum, trig_type, csr_common;
endgroup

`ifdef S_SUPPORTED
covergroup SdtrigSm_native_triggers_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    medeleg_bp: coverpoint ins.current.csr[CSR_MEDELEG][3] {
        bins to_m = {1'b0}; // breakpoint trap to M-mode
        bins to_s = {1'b1}; // breakpoint trap delegated to S-mode
    }
    bp_cause: coverpoint {ins.current.csr[CSR_MCAUSE][XLEN-1], ins.current.csr[CSR_MCAUSE][5:0]} iff (ins.current.trap) {
        bins breakpoint = {7'b0_000011};
    }

    cp_sdtrig_breakpoint_delegate: cross triggernum, medeleg_bp, bp_cause;
endgroup
`endif

// TODO `ifdef UDB_MCONTROL6_SUPPORTED
covergroup SdtrigSm_a_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/sdtrig_mcontrol6_common.svh"

    select_data:   coverpoint ins.current.csr[CSR_TDATA1][21]    { bins data = {1'b1}; }
    size_any:      coverpoint ins.current.csr[CSR_TDATA1][18:16] { bins size_any = {3'b000}; }
    perm_xsl:      coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins exec = {3'b100}; bins store = {3'b010}; bins load = {3'b001};
    }
    addrval_marker: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins marker = {32'hDEADBEEF}; bins zero = {32'h0};
        `endif
        `ifdef UDB_MXLEN_64
            bins marker = {64'hDEADBEEFDEADBEEF}; bins zero = {64'h0};
        `endif
    }

    `ifdef ZALRSC_SUPPORTED
        lrsc: coverpoint ins.current.insn {
            wildcard bins lr_w = {LR_W};
            wildcard bins sc_w = {SC_W};
            `ifdef UDB_MXLEN_64
                wildcard bins lr_d = {LR_D};
                wildcard bins sc_d = {SC_D};
            `endif
        }
    `endif
    `ifdef ZAAMO_SUPPORTED
        amoswap: coverpoint ins.current.insn {
            wildcard bins amoswap_w = {AMOSWAP_W};
            `ifdef UDB_MXLEN_64
                wildcard bins amoswap_d = {AMOSWAP_D};
            `endif
        }
        rd_nonzero: coverpoint ins.current.insn[11:7] { bins nonzero = {[5'd1:5'd31]}; }
    `endif

    `ifdef ZALRSC_SUPPORTED
        cp_sdtrig_lrsc_addr: cross mcontrol6, priv_mode_m, triggernum, addrval_marker, lrsc,
                             select_adr, size_any, chain_off, match_eq, perm_xsl, priv_m;
        cp_sdtrig_lrsc_data: cross mcontrol6, priv_mode_m, triggernum, addrval_marker, lrsc,
                             select_data, size_any, chain_off, match_eq, perm_xsl, priv_m;
    `endif
    `ifdef ZAAMO_SUPPORTED
        cp_sdtrig_amo:       cross mcontrol6, priv_mode_m, triggernum, addrval_marker, amoswap, rd_nonzero,
                             select_adr, size_any, chain_off, match_eq, perm_xsl, priv_m;
    `endif
endgroup

covergroup SdtrigSm_combined_accesses_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/sdtrig_mcontrol6_common.svh"

    size_sew: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
        bins any = {3'b000}; bins s8 = {3'b001}; bins s16 = {3'b010};
        bins s32 = {3'b011}; bins s64 = {3'b101}; bins s128 = {3'b110};
    }
    size_all: coverpoint ins.current.csr[CSR_TDATA1][18:16] { bins size[] = {[3'b000:3'b110]}; }
    perm_store: coverpoint ins.current.csr[CSR_TDATA1][2:0] { bins store = {3'b010}; }
    perm_load:  coverpoint ins.current.csr[CSR_TDATA1][2:0] { bins load  = {3'b001}; }
    perm_store_load: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins store = {3'b010}; bins load = {3'b001};
    }

    // tdata2 = scratch / scratch+8 / 0
    addrval_marker: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins marker  = {32'hDEADBEEF}; bins zero = {32'h0};
        `endif
        `ifdef UDB_MXLEN_64
            bins marker  = {64'hDEADBEEFDEADBEEF}; bins zero = {64'h0};
        `endif
    }
    addrval_multi: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins marker  = {32'hDEADBEEF};
            bins marker8 = {32'hDEADBEF7}; // scratch + 8
            bins zero    = {32'h0};
        `endif
        `ifdef UDB_MXLEN_64
            bins marker  = {64'hDEADBEEFDEADBEEF};
            bins marker8 = {64'hDEADBEEFDEADBEF7}; // scratch + 8
            bins zero    = {64'h0};
        `endif
    }

    `ifdef V_SUPPORTED
        vsew: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
            bins sew8 = {0}; bins sew16 = {1}; bins sew32 = {2}; bins sew64 = {3};
        }
        vector_ls: coverpoint ins.current.insn {
            wildcard bins vse8_v  = {VSE8_V};
            wildcard bins vse16_v = {VSE16_V};
            wildcard bins vse32_v = {VSE32_V};
            wildcard bins vse64_v = {VSE64_V};
            wildcard bins vle8_v  = {VLE8_V};
            wildcard bins vle16_v = {VLE16_V};
            wildcard bins vle32_v = {VLE32_V};
            wildcard bins vle64_v = {VLE64_V};
        }
        vperm: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
            bins store = {3'b010}; bins load = {3'b001};
        }
    `endif
    `ifdef ZCMP_SUPPORTED
        cm_pushpop: coverpoint ins.current.insn {
            wildcard bins cm_push = {CM_PUSH};
            wildcard bins cm_pop  = {CM_POP};
        }
    `endif

    `ifdef V_SUPPORTED
        cp_sdtrig_vector_load_store: cross mcontrol6, priv_mode_m, triggernum, addrval_marker, vector_ls, vsew,
                                     select_adr, size_sew, chain_off, match_eq, vperm, priv_m;
        cp_sdtrig_vector_accesses:   cross mcontrol6, priv_mode_m, triggernum, addrval_multi, vector_ls, vsew,
                                     select_adr, size_sew, chain_off, match_eq, vperm, priv_m;
    `endif
    `ifdef ZCMP_SUPPORTED
        cp_sdtrig_cm_pop_push:       cross mcontrol6, priv_mode_m, triggernum, addrval_multi, cm_pushpop,
                                     select_adr, size_all, chain_off, match_eq, perm_store_load, priv_m;
    `endif
endgroup

covergroup SdtrigSm_cache_operations_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/sdtrig_mcontrol6_common.svh"

    size_any:      coverpoint ins.current.csr[CSR_TDATA1][18:16] { bins size_any = {3'b000}; }
    size_all:      coverpoint ins.current.csr[CSR_TDATA1][18:16] { bins size[] = {[3'b000:3'b110]}; }
    perm_xsl: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins exec = {3'b100}; bins store = {3'b010}; bins load = {3'b001};
    }
    perm_all: coverpoint ins.current.csr[CSR_TDATA1][2:0] { bins all = {3'b111}; }
    addrval_marker: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins marker = {32'hDEADBEEF}; bins zero = {32'h0};
        `endif
        `ifdef UDB_MXLEN_64
            bins marker = {64'hDEADBEEFDEADBEEF}; bins zero = {64'h0};
        `endif
    }

    `ifdef ZICBOM_SUPPORTED
        cbom: coverpoint ins.current.insn {
            wildcard bins cbo_clean = {CBO_CLEAN};
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_inval = {CBO_INVAL};
        }
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cboz: coverpoint ins.current.insn { wildcard bins cbo_zero = {CBO_ZERO}; }
    `endif
    `ifdef ZICBOP_SUPPORTED
        prefetch: coverpoint ins.current.insn {
            wildcard bins prefetch_i = {PREFETCH_I};
            wildcard bins prefetch_r = {PREFETCH_R};
            wildcard bins prefetch_w = {PREFETCH_W};
        }
    `endif

    `ifdef ZICBOM_SUPPORTED
        cp_sdtrig_cache_zicbom: cross mcontrol6, priv_mode_m, triggernum, cbom, addrval_marker,
                                select_adr, size_all, chain_off, match_eq, perm_xsl, priv_m;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_sdtrig_cache_zicboz: cross mcontrol6, priv_mode_m, triggernum, cboz, addrval_marker,
                                select_adr, size_all, chain_off, match_eq, perm_xsl, priv_m;
    `endif
    `ifdef ZICBOP_SUPPORTED
        cp_sdtrig_cache_zicbop: cross mcontrol6, priv_mode_m, triggernum, prefetch,
                                select_adr, size_any, chain_off, match_eq, perm_all, priv_m;
    `endif
endgroup

covergroup SdtrigSm_address_matches_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    triggernum: coverpoint ins.current.csr[CSR_TSELECT] { bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]}; }
    tdata2_write: coverpoint ins.current.insn[31:20] { bins tdata2 = {CSR_TDATA2}; }
    tdata2_msb:   coverpoint ins.current.csr[CSR_TDATA2][XLEN-1] { } // walking high bit / sign extension
    `ifdef UDB_MXLEN_32
        satp_mode: coverpoint ins.current.csr[CSR_SATP][31] {
            bins bare = {1'b0}; bins sv32 = {1'b1};
        }
    `endif
    `ifdef UDB_MXLEN_64
        satp_mode: coverpoint ins.current.csr[CSR_SATP][63:60] {
            bins bare = {4'd0}; bins sv39 = {4'd8}; bins sv48 = {4'd9}; bins sv57 = {4'd10};
        }
    `endif

    cp_sdtrig_tdata2_translate: cross triggernum, satp_mode, tdata2_write, tdata2_msb;
endgroup
// TODO(trigger_types): // `endif

covergroup SdtrigSm_csr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    triggernum: coverpoint ins.current.csr[CSR_TSELECT] { bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]}; }
    type_disabled: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] { bins disabled = {4'd15}; }
    priv_all: coverpoint {ins.current.csr[CSR_TDATA1][6], ins.current.csr[CSR_TDATA1][4],
                          ins.current.csr[CSR_TDATA1][3], ins.current.csr[CSR_TDATA1][24],
                          ins.current.csr[CSR_TDATA1][23]} {
        // all 32 priv-bit combinations; unsupported bits read back 0
        `ifndef S_SUPPORTED
            ignore_bins no_s = {[0:31]} with (item[3] == 1'b1);
        `endif
        `ifndef U_SUPPORTED
            ignore_bins no_u = {[0:31]} with (item[2] == 1'b1);
        `endif
        `ifndef H_SUPPORTED
            ignore_bins no_vs = {[0:31]} with (item[1] == 1'b1);
            ignore_bins no_vu = {[0:31]} with (item[0] == 1'b1);
        `endif
    }
    csr_tdata: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1}; bins tdata2 = {CSR_TDATA2}; bins tdata3 = {CSR_TDATA3};
    }
    csr_tinfo: coverpoint ins.current.insn[31:20] { bins tinfo = {CSR_TINFO}; }
    csr_mcontext: coverpoint ins.current.insn[31:20] { bins mcontext = {CSR_MCONTEXT}; }
    // CSRs only accessible in M/Debug mode
    csr_mmode_only: coverpoint ins.current.insn[31:20] {
        bins tdata1   = {CSR_TDATA1}; bins tdata2 = {CSR_TDATA2}; bins tdata3 = {CSR_TDATA3};
        bins tinfo    = {CSR_TINFO};  bins tcontrol = {CSR_TCONTROL}; bins mcontext = {CSR_MCONTEXT};
        bins scontext = {CSR_SCONTEXT};
        `ifdef H_SUPPORTED
            bins hcontext = {CSR_HCONTEXT};
        `endif
    }
    illegal_trap: coverpoint {ins.current.csr[CSR_MCAUSE][XLEN-1], ins.current.csr[CSR_MCAUSE][5:0]} iff (ins.current.trap) {
        bins illegal = {7'b0_000010}; // illegal instruction on M-only CSR access from S
    }
    no_trap: coverpoint ins.current.trap { bins no_trap = {1'b0}; } // v6: all M-mode-only CSRs accessible from M-mode, no exceptions
    tcontrol_mte:  coverpoint ins.current.csr[CSR_TCONTROL][3] { } // 0/1
    tcontrol_mpte: coverpoint ins.current.csr[CSR_TCONTROL][7] { } // 0/1
    bp_trap: coverpoint {ins.current.csr[CSR_MCAUSE][XLEN-1], ins.current.csr[CSR_MCAUSE][5:0]} iff (ins.current.trap) {
        bins breakpoint = {7'b0_000011};
    }
    mtrap: coverpoint ins.current.trap { bins trap = {1'b1}; }
    mret:  coverpoint ins.current.insn { bins mret = {MRET}; }

    cp_sdtrig_tselect_trigs:         cross priv_mode_m, triggernum, csr_tinfo;
    cp_sdtrig_tdata_write:           cross priv_mode_m, triggernum, type_disabled, csr_tdata;
    cp_sdtrig_csr_access:            cross priv_mode_m, triggernum, csr_mmode_only, no_trap;
    cp_sdtrig_tdata1_mode_hardwired: cross priv_mode_m, triggernum, priv_all;
    cp_sdtrig_tinfo_read_only:       cross priv_mode_m, triggernum, csr_tinfo;
    cp_sdtrig_tcontrol_enable:       cross priv_mode_m, triggernum, tcontrol_mte, bp_trap;
    cp_sdtrig_tcontrol_mtrap:        cross priv_mode_m, triggernum, tcontrol_mte, tcontrol_mpte, mtrap;
    cp_sdtrig_tcontrol_mret:         cross priv_mode_m, triggernum, tcontrol_mte, tcontrol_mpte, mret;
    cp_sdtrig_mcontext_smode:        cross priv_mode_s, csr_mcontext, illegal_trap;
endgroup

// TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_MCONTROL6
covergroup SdtrigSm_mcontrol6_cg with function sample(
        ins_t ins,
        logic [XLEN-1:0] td1 [2]); // snapshot of triggers 0 and 1 for cross-trigger (chain) coverage
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/sdtrig_mcontrol6_common.svh"

    select_data: coverpoint ins.current.csr[CSR_TDATA1][21] {
        bins data = {1'b1};
    }
    size_any: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
        bins size_any = {3'b000};
    }
    size_all: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
        bins size[] = {[3'b000:3'b110]}; // 0-6 (7 reserved)
    }
    chain_pair: coverpoint {td1[0][11], td1[1][11]} {
        bins on_off = {2'b10}; // trig0 chain=1, trig1 chain=0
    }
    select_pair: coverpoint {td1[0][21], td1[1][21]} {
        bins adr_data = {2'b01}; // trig0 address, trig1 data
    }

    match_grp: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins eq  = {4'b0000}; // 0:  equal
        bins ge  = {4'b0010}; // 2:  >= tdata2
        bins lt  = {4'b0011}; // 3:  <  tdata2
        bins neq = {4'b1000}; // 8:  not equal
    }
    match_napot_grp: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins napot     = {4'b0001}; // 1:  napot
        bins not_napot = {4'b1001}; // 9:  not napot
    }
    match_mask_grp: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins mask_low      = {4'b0100}; // 4:  mask low
        bins mask_high     = {4'b0101}; // 5:  mask high
        bins not_mask_low  = {4'b1100}; // 12: not mask low
        bins not_mask_high = {4'b1101}; // 13: not mask high
    }

    perm_exec: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins exec = {3'b100};
    }
    perm_store: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins store = {3'b010};
    }
    perm_load: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins load = {3'b001};
    }
    perm_xsl: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins exec = {3'b100};
        bins store = {3'b010};
        bins load = {3'b001};
    }
    priv_all: coverpoint {ins.current.csr[CSR_TDATA1][6],  // m
                                    ins.current.csr[CSR_TDATA1][4],  // s
                                    ins.current.csr[CSR_TDATA1][3],  // u
                                    ins.current.csr[CSR_TDATA1][24], // vs
                                    ins.current.csr[CSR_TDATA1][23]  // vu
                                   } {
        // all 32 combinations of privilege modes
        `ifndef S_SUPPORTED
            ignore_bins no_s = {[0:31]} with (item[3] == 1'b1);
        `endif
        `ifndef U_SUPPORTED
            ignore_bins no_u = {[0:31]} with (item[2] == 1'b1);
        `endif
        `ifndef H_SUPPORTED
            ignore_bins no_vs = {[0:31]} with (item[1] == 1'b1);
            ignore_bins no_vu = {[0:31]} with (item[0] == 1'b1);
        `endif
    }

    dataval: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins dataval = {32'h12345678};
        `endif
        `ifdef UDB_MXLEN_64
            bins dataval = {64'h123456789ABCDEF0};
        `endif
    }
    addrval_scratch: coverpoint ins.current.csr[CSR_TDATA2] {
        `ifdef UDB_MXLEN_32
            bins addval = {32'hDEADBEEF};
            bins addzero = {32'h0};
        `endif
        `ifdef UDB_MXLEN_64
            bins addval = {64'hDEADBEEFDEADBEEF};
            bins addzero = {64'h0};
        `endif
    }
    tdata2_nop: coverpoint ins.current.csr[CSR_TDATA2] {
        bins nop = {NOP};
    }
    tdata2_nop_sizes: coverpoint ins.current.csr[CSR_TDATA2] {
        bins nop = {NOP};
        `ifdef ZCA_SUPPORTED
            bins c_nop = {C_NOP};
        `endif
    }
    store_data: coverpoint ins.current.rs2_val {
        `ifdef UDB_MXLEN_32
            bins zero       = {32'h00000000};   // far below
            bins below      = {32'hB0BAB0B9};   // tdata2 - 1
            bins equal      = {32'hB0BAB0BA};   // == tdata2
            bins above      = {32'hB0BAB0BB};   // tdata2 + 1
            bins high_diff  = {32'hCCCCB0BA};   // low half match, high differs
            bins low_diff   = {32'hB0BACCCC};   // high half match, low differs
            bins all_ones_ish = {32'h11111111}; // far above
            bins napot_below = {32'hB0BAB0B7};  // below NAPOT range
            bins napot_above = {32'hB0BAB0BC};  // above NAPOT range
        `endif
        `ifdef UDB_MXLEN_64
            bins zero       = {64'h0000000000000000};   // far below
            bins below      = {64'hB0BAB0BAB0BAB0B9};   // tdata2 - 1
            bins equal      = {64'hB0BAB0BAB0BAB0BA};   // == tdata2
            bins above      = {64'hB0BAB0BAB0BAB0BB};   // tdata2 + 1
            bins high_diff  = {64'hCCCCCCCCB0BAB0BA};   // low half match, high differs
            bins low_diff   = {64'hB0BAB0BACCCCCCCC};   // high half match, low differs
            bins all_ones_ish = {64'h1111111111111111}; // far above
            bins napot_below = {64'hB0BAB0BAB0BAB0B7};  // below NAPOT range
            bins napot_above = {64'hB0BAB0BAB0BAB0BC};  // above NAPOT range
        `endif
    }

    nop: coverpoint ins.current.insn {
        bins nop = {NOP};
    }
    nop_sizes: coverpoint ins.current.insn {
        bins nop = {NOP};
        `ifdef ZCA_SUPPORTED
            wildcard bins c_nop = {C_NOP};
        `endif
    }
    load: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    store: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    load_store: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    loadstore_all: coverpoint ins.current.insn {
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        wildcard bins sb  = {SB};
        wildcard bins sh  = {SH};
        wildcard bins sw  = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins lwu = {LWU};
            wildcard bins ld  = {LD};
            wildcard bins sd  = {SD};
        `endif
        `ifdef F_SUPPORTED
            wildcard bins flw = {FLW};
            wildcard bins fsw = {FSW};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
            wildcard bins fsd = {FSD};
        `endif
        `ifdef ZFH_SUPPORTED
            wildcard bins flh = {FLH};
            wildcard bins fsh = {FSH};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins flq = {FLQ};
            wildcard bins fsq = {FSQ};
        `endif
        `ifdef ZCA_SUPPORTED
            wildcard bins c_lw   = {C_LW};
            wildcard bins c_sw   = {C_SW};
            wildcard bins c_lwsp = {C_LWSP};
            wildcard bins c_swsp = {C_SWSP};
            `ifdef UDB_MXLEN_64
                wildcard bins c_ld   = {C_LD};
                wildcard bins c_sd   = {C_SD};
                wildcard bins c_ldsp = {C_LDSP};
                wildcard bins c_sdsp = {C_SDSP};
            `endif
        `endif
        `ifdef ZCB_SUPPORTED
            wildcard bins c_lbu = {C_LBU};
            wildcard bins c_lh  = {C_LH};
            wildcard bins c_lhu = {C_LHU};
            wildcard bins c_sb  = {C_SB};
            wildcard bins c_sh  = {C_SH};
        `endif
        `ifdef ZCF_SUPPORTED // Zcf is RV32-only
            `ifdef UDB_MXLEN_32
                wildcard bins c_flw   = {C_FLW};
                wildcard bins c_flwsp = {C_FLWSP};
                wildcard bins c_fsw   = {C_FSW};
                wildcard bins c_fswsp = {C_FSWSP};
            `endif
        `endif
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fld   = {C_FLD};
            wildcard bins c_fldsp = {C_FLDSP};
            wildcard bins c_fsd   = {C_FSD};
            wildcard bins c_fsdsp = {C_FSDSP};
        `endif
    }


    rel_exec_adr: coverpoint (ins.current.pc_rdata == ins.current.csr[CSR_TDATA2]) {
        bins match   = {1'b1};
        bins nomatch = {1'b0};
    }
    rel_exec_data: coverpoint (ins.current.insn == ins.current.csr[CSR_TDATA2]) {
        bins match   = {1'b1};
        bins nomatch = {1'b0};
    }

    cp_sdtrig_mcontrol6_priv_mode:      cross mcontrol6, priv_mode_m, triggernum, dataval, store,
                                        select_data, size_any, chain_off, match_eq, perm_store, priv_all;

    cp_sdtrig_mcontrol6_execute_adr:    cross mcontrol6, priv_mode_m, triggernum, nop, rel_exec_adr,
                                        select_adr, size_any, chain_off, match_eq, perm_xsl, priv_m;

    cp_sdtrig_mcontrol6_load_store_adr: cross mcontrol6, priv_mode_m, triggernum, addrval_scratch, load_store,
                                        select_adr, size_any, chain_off, match_eq, perm_xsl, priv_m;

    cp_sdtrig_mcontrol6_execute_data:   cross mcontrol6, priv_mode_m, triggernum, tdata2_nop, nop, rel_exec_data,
                                        select_data, size_any, chain_off, match_eq, perm_xsl, priv_m;

    cp_sdtrig_mcontrol6_load_store_data: cross mcontrol6, priv_mode_m, triggernum, addrval_scratch, load_store,
                                        select_data, size_any, chain_off, match_eq, perm_xsl, priv_m;

    cp_sdtrig_mcontrol6_execute_size:   cross mcontrol6, priv_mode_m, triggernum, tdata2_nop_sizes, nop_sizes,
                                        select_data, size_all, chain_off, match_eq, perm_exec, priv_m;

    cp_sdtrig_mcontrol6_load_store_size: cross mcontrol6, priv_mode_m, triggernum, loadstore_all,
                                        select_data, size_all, chain_off, match_eq, perm_xsl, priv_m;

    cp_sdtrig_mcontrol6_match:          cross mcontrol6, priv_mode_m, triggernum, dataval, store, store_data,
                                        select_data, size_any, chain_off, match_grp, perm_store, priv_m;

    cp_sdtrig_mcontrol6_match_napot:    cross mcontrol6, priv_mode_m, triggernum, dataval, store, store_data,
                                        select_data, size_any, chain_off, match_napot_grp, perm_store, priv_m;

    cp_sdtrig_mcontrol6_match_mask:     cross mcontrol6, priv_mode_m, triggernum, dataval, store, store_data,
                                        select_data, size_any, chain_off, match_mask_grp, perm_store, priv_m;

    cp_sdtrig_mcontrol6_chain_adr:      cross mcontrol6, priv_mode_m, dataval, store,
                                        chain_pair, select_pair, size_any, match_eq, perm_store, priv_m;

endgroup
// TODO(trigger_types): // `endif

// TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_ICOUNT
covergroup SdtrigSm_icount_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    icount_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins icount = {4'b0011};
    }
    dmode_0: coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] {
        bins zero = {1'b0};
    }
    count_val: coverpoint ins.current.csr[CSR_TDATA1][23:10] {
        bins zero = {14'd0};
        bins one  = {14'd1};
        bins many = {[14'd2:14'h3FFF]};
    }
    pending: coverpoint ins.current.csr[CSR_TDATA1][8] {
    }
    nop: coverpoint ins.current.insn {
        bins nop = {NOP};
    }
    icount_trap: coverpoint ins.current.trap {
        bins trap = {1'b1};
    }
    action_breakpoint: coverpoint ins.current.csr[CSR_TDATA1][5:0] {
        bins breakpoint = {6'b000000}; // action 0
    }
    priv_m: coverpoint {ins.current.csr[CSR_TDATA1][26], // vs
                        ins.current.csr[CSR_TDATA1][25], // vu
                        ins.current.csr[CSR_TDATA1][9],  // m
                        ins.current.csr[CSR_TDATA1][7],  // s
                        ins.current.csr[CSR_TDATA1][6]   // u
                       } {
        bins m = {5'b00100}; // machine mode only
    }
    icount_priv_all: coverpoint {ins.current.csr[CSR_TDATA1][26], // vs
                                 ins.current.csr[CSR_TDATA1][25], // vu
                                 ins.current.csr[CSR_TDATA1][9],  // m
                                 ins.current.csr[CSR_TDATA1][7],  // s
                                 ins.current.csr[CSR_TDATA1][6]   // u
                                } {
        // all 32 combinations of privilege modes
        `ifndef S_SUPPORTED
            ignore_bins no_s = {[0:31]} with (item[1] == 1'b1);
        `endif
        `ifndef U_SUPPORTED
            ignore_bins no_u = {[0:31]} with (item[0] == 1'b1);
        `endif
        `ifndef H_SUPPORTED
            ignore_bins no_vs = {[0:31]} with (item[4] == 1'b1);
            ignore_bins no_vu = {[0:31]} with (item[3] == 1'b1);
        `endif
    }


    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    icount: cross icount_type, dmode_0, action_breakpoint;

    cp_sdtrig_icount_hardwired: cross priv_mode_m, triggernum, icount, icount_priv_all, nop;
    cp_sdtrig_icount_instr:     cross priv_mode_m, triggernum, icount, count_val, priv_m, nop;
    cp_sdtrig_icount_trap:      cross priv_mode_m, triggernum, icount, count_val, priv_m, icount_trap;
    cp_sdtrig_icount_eq0:       cross priv_mode_m, triggernum, icount, count_val, pending, nop;
endgroup
// TODO(trigger_types): // `endif

// TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_ITRIGGER
covergroup SdtrigSm_itrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    interrupt_cause: coverpoint {ins.current.csr[CSR_MCAUSE][XLEN-1],
                                ins.current.csr[CSR_MCAUSE][5:0]} {
        bins ssi   = {7'b1_000001}; //  1  supervisor software
        bins msi   = {7'b1_000011}; //  3  machine software
        bins sti   = {7'b1_000101}; //  5  supervisor timer
        bins mti   = {7'b1_000111}; //  7  machine timer
        bins sei   = {7'b1_001001}; //  9  supervisor external
        bins mei   = {7'b1_001011}; // 11  machine external
        bins lcofi = {7'b1_001101}; // 13  counter-overflow (Sscofpmf)
    }

    itrigger_priv_all: coverpoint {ins.current.csr[CSR_TDATA1][9],  // m
                        ins.current.csr[CSR_TDATA1][7],  // s
                        ins.current.csr[CSR_TDATA1][6],  // u
                        ins.current.csr[CSR_TDATA1][12], // vs
                        ins.current.csr[CSR_TDATA1][11]  // vu
                       } {
        // all 32 combinations of privilege modes
        `ifndef S_SUPPORTED
            ignore_bins no_s = {[0:31]} with (item[3] == 1'b1);
        `endif
        `ifndef U_SUPPORTED
            ignore_bins no_u = {[0:31]} with (item[2] == 1'b1);
        `endif
        `ifndef H_SUPPORTED
            ignore_bins no_vs = {[0:31]} with (item[1] == 1'b1);
            ignore_bins no_vu = {[0:31]} with (item[0] == 1'b1);
        `endif
    }

    itrigger_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins itrigger = {4'b0100}; // type 4
    }
    dmode_0: coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] {
        bins zero = {1'b0};
    }
    action_bp: coverpoint ins.current.csr[CSR_TDATA1][5:0] {
        bins breakpoint = {6'b000000}; // action 0
    }
    hit: coverpoint ins.current.csr[CSR_TDATA1][XLEN-6] iff (ins.current.trap) {
        bins nofire = {1'b0};
        bins fire   = {1'b1};
    }
    // norm:Sdtrig_itrigger_nmi
    nmi: coverpoint ins.current.csr[CSR_TDATA1][10] {
        bins off = {1'b0};
        bins on  = {1'b1};
    }

    // one-hot mask of mcause Interrupt Codes; bit N => trap on code N
    tdata2_intcode: coverpoint ins.current.csr[CSR_TDATA2] {
        bins ssi = {1 << 1};   //  1  supervisor software
        `ifdef H_SUPPORTED
            bins vssi = {1 << 2}; //  2  VS software
        `endif
        bins msi = {1 << 3};   //  3  machine software
        bins sti = {1 << 5};   //  5  supervisor timer
        `ifdef H_SUPPORTED
            bins vsti = {1 << 6}; //  6  VS timer
        `endif
        bins mti = {1 << 7};   //  7  machine timer
        bins sei = {1 << 9};   //  9  supervisor external
        `ifdef H_SUPPORTED
            bins vsei = {1 << 10}; // 10  VS external
        `endif
        bins mei = {1 << 11};  // 11  machine external
        `ifdef H_SUPPORTED
            bins sgei = {1 << 12}; // 12  supervisor guest external
        `endif
        bins lcofi = {1 << 13}; // 13  counter-overflow (Sscofpmf)
    }

    // norm:Sdtrig_itrigger_action0
    tval_zero: coverpoint (ins.current.csr[CSR_MTVAL] == '0) iff (ins.current.trap) {
        bins zero    = {1'b1};
        bins nonzero = {1'b0};
    }

    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    itrigger: cross itrigger_type, dmode_0, action_bp;

    cp_sdtrig_itrigger: cross itrigger, triggernum, tdata2_intcode, itrigger_priv_all, hit, tval_zero;
    cp_sdtrig_itrigger_nmi: cross itrigger, triggernum, tdata2_intcode, itrigger_priv_all, nmi;

endgroup
// TODO(trigger_types): // `endif

// TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_ETRIGGER
covergroup SdtrigSm_etrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    exception_cause: coverpoint {ins.current.csr[CSR_MCAUSE][XLEN-1],
                                ins.current.csr[CSR_MCAUSE][5:0]} {
        bins iaf  = {7'b0_000000}; //  0  instruction address misaligned
        bins iacc = {7'b0_000001}; //  1  instruction access fault
        bins ill  = {7'b0_000010}; //  2  illegal instruction
        bins bp   = {7'b0_000011}; //  3  breakpoint
        bins lam  = {7'b0_000100}; //  4  load address misaligned
        bins lacc = {7'b0_000101}; //  5  load access fault
        bins sam  = {7'b0_000110}; //  6  store/AMO address misaligned
        bins sacc = {7'b0_000111}; //  7  store/AMO access fault
        bins ecu  = {7'b0_001000}; //  8  ecall from U
        bins ecs  = {7'b0_001001}; //  9  ecall from S
        bins ecm  = {7'b0_001011}; // 11  ecall from M
        bins ipf  = {7'b0_001100}; // 12  instruction page fault
        bins lpf  = {7'b0_001101}; // 13  load page fault
        bins spf  = {7'b0_001111}; // 15  store/AMO page fault
    }

    etrigger_priv_all: coverpoint {ins.current.csr[CSR_TDATA1][9],  // m
                        ins.current.csr[CSR_TDATA1][7],  // s
                        ins.current.csr[CSR_TDATA1][6],  // u
                        ins.current.csr[CSR_TDATA1][12], // vs
                        ins.current.csr[CSR_TDATA1][11]  // vu
                       } {
        // all 32 combinations of privilege modes
        `ifndef S_SUPPORTED
            ignore_bins no_s = {[0:31]} with (item[3] == 1'b1);
        `endif
        `ifndef U_SUPPORTED
            ignore_bins no_u = {[0:31]} with (item[2] == 1'b1);
        `endif
        `ifndef H_SUPPORTED
            ignore_bins no_vs = {[0:31]} with (item[1] == 1'b1);
            ignore_bins no_vu = {[0:31]} with (item[0] == 1'b1);
        `endif
    }

    etrigger_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins etrigger = {4'b0101}; // type 5
    }
    dmode_0: coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] {
        bins zero = {1'b0};
    }
    action_bp: coverpoint ins.current.csr[CSR_TDATA1][5:0] {
        bins breakpoint = {6'b000000}; // action 0
    }
    hit: coverpoint ins.current.csr[CSR_TDATA1][XLEN-6] iff (ins.current.trap) {
        bins nofire = {1'b0};
        bins fire   = {1'b1};
    }

    // one-hot mask of mcause Exception Codes; bit N => trap on code N (norm:Sdtrig_etrigger_config)
    tdata2_excode: coverpoint ins.current.csr[CSR_TDATA2] {
        bins iam  = {1 << 0};  //  0  instruction address misaligned
        bins iacc = {1 << 1};  //  1  instruction access fault
        bins ill  = {1 << 2};  //  2  illegal instruction
        bins bp   = {1 << 3};  //  3  breakpoint
        bins lam  = {1 << 4};  //  4  load address misaligned
        bins lacc = {1 << 5};  //  5  load access fault
        bins sam  = {1 << 6};  //  6  store/AMO address misaligned
        bins sacc = {1 << 7};  //  7  store/AMO access fault
        `ifdef U_SUPPORTED
            bins ecu = {1 << 8};   //  8  ecall from U
        `endif
        `ifdef S_SUPPORTED
            bins ecs = {1 << 9};   //  9  ecall from S
        `endif
        `ifdef H_SUPPORTED
            bins ecvs = {1 << 10}; // 10  ecall from VS
        `endif
        bins ecm  = {1 << 11}; // 11  ecall from M
        bins ipf  = {1 << 12}; // 12  instruction page fault
        bins lpf  = {1 << 13}; // 13  load page fault
        bins spf  = {1 << 15}; // 15  store/AMO page fault
        `ifdef SMDBLTRP_SUPPORTED
            bins dbltrp = {1 << 16}; // 16  double trap
        `endif
        `ifdef SOFTWARE_CHECK_SUPPORTED
            bins swchk = {1 << 18}; // 18  software check
        `endif
        `ifdef H_SUPPORTED
            bins igpf = {1 << 20}; // 20  instruction guest-page fault
            bins lgpf = {1 << 21}; // 21  load guest-page fault
            bins virt = {1 << 22}; // 22  virtual instruction
            bins sgpf = {1 << 23}; // 23  store/AMO guest-page fault
        `endif
    }

    // norm:Sdtrig_etrigger_action0
    tval_zero: coverpoint (ins.current.csr[CSR_MTVAL] == '0) iff (ins.current.trap) {
        bins zero    = {1'b1};
        bins nonzero = {1'b0};
    }

    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    etrigger: cross etrigger_type, dmode_0, action_bp;

    cp_sdtrig_etrigger: cross etrigger, triggernum, tdata2_excode, etrigger_priv_all, tval_zero;

endgroup
// TODO(trigger_types): // `endif

// TODO(trigger_types): NOT gated by mcontrol6 -- textra (tdata3) applies to types 2,3,4,5,6.
// When real params exist, gate on "any match-type trigger present", not UDB_TRIGGER_TYPES_MCONTROL6.
covergroup SdtrigSm_textra_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    trig_type4: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins icount    = {4'b0011};
        bins itrigger  = {4'b0100};
        bins etrigger  = {4'b0101};
        bins mcontrol6 = {4'b0110};
    }
    dmode_0:    coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] { bins zero = {1'b0}; }
    action_bp:  coverpoint ins.current.csr[CSR_TDATA1][15:12]  { bins breakpoint = {4'b0000}; }
    triggernum: coverpoint ins.current.csr[CSR_TSELECT] { bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]}; }

    `ifdef UDB_MXLEN_32
        // sselect[1:0] svalue[17:2] sbytemask[19:18] mhselect[25:23] mhvalue[31:26]
        mhselect_4: coverpoint ins.current.csr[CSR_TDATA3][25:23] { bins four = {3'b100}; }
        mhselect_double: coverpoint ins.current.csr[CSR_TDATA3][25:23] { bins ignore = {3'b000}; bins mcontext = {3'b100}; }
        sselect_double:  coverpoint ins.current.csr[CSR_TDATA3][1:0]   { bins ignore = {2'b00};   bins scontext = {2'b01}; }
        mhvalue:    coverpoint ins.current.csr[CSR_TDATA3][31:26] {
            bins match = {6'b010101}; bins zero = {6'b000000}; bins all_ones = {6'b111111};
        }
        rel_mhvalue: coverpoint (ins.current.csr[CSR_TDATA3][31:26] == ins.current.csr[CSR_MCONTEXT][5:0]) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        sselect_scontext: coverpoint ins.current.csr[CSR_TDATA3][1:0] { bins scontext = {2'b01}; }
        sselect_asid:     coverpoint ins.current.csr[CSR_TDATA3][1:0] { bins asid     = {2'b10}; }
        svalue: coverpoint ins.current.csr[CSR_TDATA3][17:2] {
            bins zero = {16'h0000}; bins b0034 = {16'h0034}; bins b1200 = {16'h1200}; bins b1234 = {16'h1234};
        }
        sbytemask: coverpoint ins.current.csr[CSR_TDATA3][19:18] { } // all 4 combinations
        rel_scontext: coverpoint (
                (ins.current.csr[CSR_TDATA3][19] | (ins.current.csr[CSR_TDATA3][17:10] == ins.current.csr[CSR_SCONTEXT][15:8])) &
                (ins.current.csr[CSR_TDATA3][18] | (ins.current.csr[CSR_TDATA3][9:2]   == ins.current.csr[CSR_SCONTEXT][7:0]))) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        svalue_asid: coverpoint ins.current.csr[CSR_TDATA3][10:2] { } // svalue low ASIDMAX(9) bits
        rel_asid: coverpoint (ins.current.csr[CSR_SATP][30:22] == ins.current.csr[CSR_TDATA3][10:2]) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        // svalue + sselect read 0 when S-mode not supported
        sfield_hw: coverpoint {ins.current.csr[CSR_TDATA3][17:2], ins.current.csr[CSR_TDATA3][1:0]} {
            bins zero = {18'h0};
        }
    `endif
    `ifdef UDB_MXLEN_64
        // sselect[1:0] svalue[33:2] sbytemask[39:36] mhselect[50:48] mhvalue[63:51]
        mhselect_4: coverpoint ins.current.csr[CSR_TDATA3][50:48] { bins four = {3'b100}; }
        mhselect_double: coverpoint ins.current.csr[CSR_TDATA3][50:48] { bins ignore = {3'b000}; bins mcontext = {3'b100}; }
        sselect_double:  coverpoint ins.current.csr[CSR_TDATA3][1:0]   { bins ignore = {2'b00};   bins scontext = {2'b01}; }
        mhvalue:    coverpoint ins.current.csr[CSR_TDATA3][63:51] {
            bins match = {13'h1AAA}; bins zero = {13'h0000}; bins half = {13'h0AAA};
        }
        rel_mhvalue: coverpoint (ins.current.csr[CSR_TDATA3][63:51] == ins.current.csr[CSR_MCONTEXT][12:0]) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        sselect_scontext: coverpoint ins.current.csr[CSR_TDATA3][1:0] { bins scontext = {2'b01}; }
        sselect_asid:     coverpoint ins.current.csr[CSR_TDATA3][1:0] { bins asid     = {2'b10}; }
        svalue: coverpoint ins.current.csr[CSR_TDATA3][33:2] {
            bins zero        = {32'h00000000}; bins b12345600 = {32'h12345600}; bins b12340078 = {32'h12340078};
            bins b12005678   = {32'h12005678}; bins b00345678 = {32'h00345678}; bins b12345678 = {32'h12345678};
        }
        sbytemask: coverpoint ins.current.csr[CSR_TDATA3][39:36] { } // all 16 combinations
        rel_scontext: coverpoint (
                (ins.current.csr[CSR_TDATA3][39] | (ins.current.csr[CSR_TDATA3][33:26] == ins.current.csr[CSR_SCONTEXT][31:24])) &
                (ins.current.csr[CSR_TDATA3][38] | (ins.current.csr[CSR_TDATA3][25:18] == ins.current.csr[CSR_SCONTEXT][23:16])) &
                (ins.current.csr[CSR_TDATA3][37] | (ins.current.csr[CSR_TDATA3][17:10] == ins.current.csr[CSR_SCONTEXT][15:8]))  &
                (ins.current.csr[CSR_TDATA3][36] | (ins.current.csr[CSR_TDATA3][9:2]   == ins.current.csr[CSR_SCONTEXT][7:0]))) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        svalue_asid: coverpoint ins.current.csr[CSR_TDATA3][17:2] {
            bins below = {16'h9AAA}; bins equal = {16'hAAAA}; bins above = {16'hBAAA};
        }
        rel_asid: coverpoint (ins.current.csr[CSR_SATP][59:44] == ins.current.csr[CSR_TDATA3][17:2]) {
            bins match = {1'b1}; bins nomatch = {1'b0};
        }
        // svalue + sselect read 0 when S-mode not supported
        sfield_hw: coverpoint {ins.current.csr[CSR_TDATA3][33:2], ins.current.csr[CSR_TDATA3][1:0]} {
            bins zero = {34'h0};
        }
    `endif

    cp_sdtrig_textra_mcontext:        cross priv_mode_m, trig_type4, dmode_0, action_bp, triggernum, mhselect_4, mhvalue, rel_mhvalue;
    cp_sdtrig_textra_scontext:        cross priv_mode_m, trig_type4, dmode_0, action_bp, triggernum, sselect_scontext, svalue, sbytemask, rel_scontext;
    cp_sdtrig_textra_asid:            cross priv_mode_m, trig_type4, dmode_0, action_bp, triggernum, sselect_asid, svalue_asid, rel_asid;
    cp_sdtrig_textra_mcontext_smode:  cross priv_mode_s, trig_type4, dmode_0, action_bp, triggernum, mhselect_4, mhvalue, rel_mhvalue;
    cp_sdtrig_textra_scontext_smode:  cross priv_mode_s, trig_type4, dmode_0, action_bp, triggernum, sselect_scontext, svalue, sbytemask, rel_scontext;
    cp_sdtrig_smode_fields_hardwired: cross priv_mode_m, triggernum, sfield_hw;
    // both context filters enabled together must combine with AND, not OR (norm:Sdtrig_textra32_mhselect_mcontext, norm:Sdtrig_textra32_sselect_scontext)
    cp_sdtrig_textra_double_context:  cross priv_mode_m, trig_type4, dmode_0, action_bp, triggernum,
                                      mhselect_double, sselect_double, rel_mhvalue, rel_scontext;

endgroup


function void sdtrigsm_sample(int hart, int issue, ins_t ins);
    // snapshot triggers 0 and 1 for the mcontrol6 chain coverpoints (2 wide: safe on 1-trigger configs)
    static logic [XLEN-1:0] td1 [2];
    int unsigned tsel;
    tsel = ins.current.csr[CSR_TSELECT];
    if (tsel < 2)
        td1[tsel] = ins.current.csr[CSR_TDATA1];
    SdtrigSm_sdtrig_cg.sample(ins);
    SdtrigSm_native_triggers_cg.sample(ins);
    // TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_MCONTROL6
    SdtrigSm_a_cg.sample(ins);
    SdtrigSm_combined_accesses_cg.sample(ins);
    SdtrigSm_cache_operations_cg.sample(ins);
    SdtrigSm_address_matches_cg.sample(ins);
    // TODO(trigger_types): // `endif
    SdtrigSm_csr_cg.sample(ins);
    // TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_MCONTROL6
    SdtrigSm_mcontrol6_cg.sample(ins, td1);
    // TODO(trigger_types): // `endif
    // TODO(trigger_types): wrap each in // `ifdef UDB_TRIGGER_TYPES_<TYPE> / // `endif
    SdtrigSm_icount_cg.sample(ins);
    SdtrigSm_itrigger_cg.sample(ins);
    SdtrigSm_etrigger_cg.sample(ins);
    SdtrigSm_textra_cg.sample(ins);
endfunction
