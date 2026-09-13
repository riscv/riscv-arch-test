///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu September 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSSM2

covergroup InterruptsSm2_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    // Uses ins.prev instead of ins.current because RVVI updates CSRs after instruction retirement,
    // so ins.current shows post-trap state while ins.prev shows pre-trap state.
    mstatus_mie: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        // autofill 0/1
    }
    mstatus_mie_one: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins one = {1};
    }
    mstatus_sie: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins zero = {0};
        `ifdef S_SUPPORTED
            bins one = {1}; // SIE is read-only zero without S
        `endif
    }
    mstatus_tw: coverpoint ins.prev.csr[CSR_MSTATUS][21] {
        // autofill 0/1
    }
    mstatus_tw_zero: coverpoint ins.prev.csr[CSR_MSTATUS][21] {
        bins zero = {0}; // WFI is permitted outside M mode
    }
    mstatus_tw_one: coverpoint ins.prev.csr[CSR_MSTATUS][21] {
        bins one = {1}; // WFI outside M mode traps after the implementation-defined timeout
    }

    // mideleg written all 0s or all 1s in every delegable field
    mideleg_both: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        `ifdef S_SUPPORTED
            `ifdef SSCOFPMF_SUPPORTED
                wildcard bins ones  = {16'b??1?1?1?1?1?1?1?}; // LCOFI, MEI, SEI, MTI, STI, MSI, SSI delegated
                wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
            `else
                wildcard bins ones  = {16'b????1?1?1?1?1?1?}; // MEI, SEI, MTI, STI, MSI, SSI delegated
                wildcard bins zeros = {16'b????0?0?0?0?0?0?};
            `endif
        `else
            bins zeros = {16'h0000}; // mideleg is read-only zero without S
        `endif
    }

    // mideleg written all 0s. Bits 12, 10, 6, and 2 are don't care because H hardwires them to 1.
    mideleg_zeros: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        `ifdef SSCOFPMF_SUPPORTED
            wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
        `else
            wildcard bins zeros = {16'b????0?0?0?0?0?0?};
        `endif
    }

    // Exactly one interrupt delegated: mideleg masked to the bits software can write is one-hot.
    // H hardwires bits 12, 10, 6, and 2 to 1, so they are left out of the mask to keep it one-hot.
    // Reads ins.prev to match mip_pairs and mie_pairs, which it is crossed with.
    `ifdef S_SUPPORTED
        mideleg_walking_one: coverpoint (ins.prev.csr[CSR_MIDELEG][15:0] & (16'h0AAA // MEI, SEI, MTI, STI, MSI, SSI
                                         `ifdef SSCOFPMF_SUPPORTED
                                             | 16'h2000 // LCOFI
                                         `endif
                                         )) {
            bins mei = {16'h0800};
            bins sei = {16'h0200};
            bins mti = {16'h0080};
            bins sti = {16'h0020};
            bins msi = {16'h0008};
            bins ssi = {16'h0002};
            `ifdef SSCOFPMF_SUPPORTED
                bins lcofi = {16'h2000};
            `endif
        }
    `endif

    // mie written all 1s: reduction AND over every enable bit the config supports
    mie_ones: coverpoint (&{ins.prev.csr[CSR_MIE][11],  // MEIE
                            ins.prev.csr[CSR_MIE][7],   // MTIE
                            ins.prev.csr[CSR_MIE][3]    // MSIE
                            `ifdef S_SUPPORTED
                                , ins.prev.csr[CSR_MIE][9]  // SEIE
                                , ins.prev.csr[CSR_MIE][5]  // STIE
                                , ins.prev.csr[CSR_MIE][1]  // SSIE
                            `endif
                            `ifdef SSCOFPMF_SUPPORTED
                                , ins.prev.csr[CSR_MIE][13] // LCOFIE
                            `endif
                            `ifdef H_SUPPORTED
                                , ins.prev.csr[CSR_MIE][10] // VSEIE
                                , ins.prev.csr[CSR_MIE][6]  // VSTIE
                                , ins.prev.csr[CSR_MIE][2]  // VSSIE
                            `endif
                            }) {
        bins ones = {1'b1};
    }


    mie_mtie: coverpoint ins.prev.csr[CSR_MIE][7] {
         // autofill 0/1
    }

    // Exactly one interrupt enabled: mie masked to the bits this config supports is one-hot.
    // Masking keeps the bin values the same on every config, so no bin is left unreachable.
    walking_mie_one: coverpoint (ins.current.csr[CSR_MIE][15:0] & (16'h0888 // MEIE, MTIE, MSIE
                                 `ifdef S_SUPPORTED
                                     | 16'h0222 // SEIE, STIE, SSIE
                                 `endif
                                 `ifdef SSCOFPMF_SUPPORTED
                                     | 16'h2000 // LCOFIE
                                 `endif
                                 `ifdef H_SUPPORTED
                                     | 16'h0444 // VSEIE, VSTIE, VSSIE
                                 `endif
                                 )) {
        bins meie = {16'h0800};
        bins mtie = {16'h0080};
        bins msie = {16'h0008};
        `ifdef S_SUPPORTED
            bins seie = {16'h0200};
            bins stie = {16'h0020};
            bins ssie = {16'h0002};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofie = {16'h2000};
        `endif
        `ifdef H_SUPPORTED
            bins vseie = {16'h0400};
            bins vstie = {16'h0040};
            bins vssie = {16'h0004};
        `endif
    }

    // Every interrupt enabled except one: the complement of mie, masked to the bits this config
    // supports, is one-hot. The bin names the single interrupt left disabled.
    walking_mie_zero: coverpoint ((~ins.current.csr[CSR_MIE][15:0]) & (16'h0888 // MEIE, MTIE, MSIE
                                  `ifdef S_SUPPORTED
                                      | 16'h0222 // SEIE, STIE, SSIE
                                  `endif
                                  `ifdef SSCOFPMF_SUPPORTED
                                      | 16'h2000 // LCOFIE
                                  `endif
                                  `ifdef H_SUPPORTED
                                      | 16'h0444 // VSEIE, VSTIE, VSSIE
                                  `endif
                                  )) {
        bins meie = {16'h0800};
        bins mtie = {16'h0080};
        bins msie = {16'h0008};
        `ifdef S_SUPPORTED
            bins seie = {16'h0200};
            bins stie = {16'h0020};
            bins ssie = {16'h0002};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofie = {16'h2000};
        `endif
        `ifdef H_SUPPORTED
            bins vseie = {16'h0400};
            bins vstie = {16'h0040};
            bins vssie = {16'h0004};
        `endif
    }

    // Exactly two interrupts enabled: mie masked to the bits this config supports has exactly two
    // bits set. One bin per pair, so the count follows the config: 45 with S, H, and Sscofpmf,
    // 21 without H, 15 without Sscofpmf, 3 for M only.
    mie_pairs: coverpoint (ins.prev.csr[CSR_MIE][15:0] & (16'h0888 // MEIE, MTIE, MSIE
                           `ifdef S_SUPPORTED
                               | 16'h0222 // SEIE, STIE, SSIE
                           `endif
                           `ifdef SSCOFPMF_SUPPORTED
                               | 16'h2000 // LCOFIE
                           `endif
                           `ifdef H_SUPPORTED
                               | 16'h0444 // VSEIE, VSTIE, VSSIE
                           `endif
                           )) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~(16'h0888
                                     `ifdef S_SUPPORTED
                                         | 16'h0222
                                     `endif
                                     `ifdef SSCOFPMF_SUPPORTED
                                         | 16'h2000
                                     `endif
                                     `ifdef H_SUPPORTED
                                         | 16'h0444
                                     `endif
                                     )) == 0);
    }

    // One interrupt pending at a time. Bits 15:14, 12, 8, 4, and 0 are don't care because they are
    // either tied to zero or driven by the platform (SGEIP) rather than by the test.
    mip_walking: coverpoint ins.prev.csr[CSR_MIP][15:0] {
        wildcard bins meip = {16'b??0?100?000?000?};
        wildcard bins mtip = {16'b??0?000?100?000?};
        wildcard bins msip = {16'b??0?000?000?100?};
        `ifdef S_SUPPORTED
            wildcard bins seip = {16'b??0?001?000?000?};
            wildcard bins stip = {16'b??0?000?001?000?};
            wildcard bins ssip = {16'b??0?000?000?001?};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            wildcard bins lcofip = {16'b??1?000?000?000?};
        `endif
        `ifdef H_SUPPORTED
            wildcard bins vseip = {16'b??0?010?000?000?};
            wildcard bins vstip = {16'b??0?000?010?000?};
            wildcard bins vssip = {16'b??0?000?000?010?};
        `endif
    }

    // Two interrupts pending at once: mip masked to the bits this config supports has exactly two
    // bits set. One bin per pair, so the count follows the config: 45 with S, H, and Sscofpmf,
    // 21 without H, 15 without Sscofpmf, 3 for M only.
    mip_pairs: coverpoint (ins.prev.csr[CSR_MIP][15:0] & (16'h0888 // MEIP, MTIP, MSIP
                           `ifdef S_SUPPORTED
                               | 16'h0222 // SEIP, STIP, SSIP
                           `endif
                           `ifdef SSCOFPMF_SUPPORTED
                               | 16'h2000 // LCOFIP
                           `endif
                           `ifdef H_SUPPORTED
                               | 16'h0444 // VSEIP, VSTIP, VSSIP
                           `endif
                           )) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~(16'h0888
                                     `ifdef S_SUPPORTED
                                         | 16'h0222
                                     `endif
                                     `ifdef SSCOFPMF_SUPPORTED
                                         | 16'h2000
                                     `endif
                                     `ifdef H_SUPPORTED
                                         | 16'h0444
                                     `endif
                                     )) == 0);
    }

    // Every interrupt pending at once: reduction AND over every pending bit the config supports
    mip_all_ones: coverpoint (&{ins.prev.csr[CSR_MIP][11],  // MEIP
                            ins.prev.csr[CSR_MIP][7],   // MTIP
                            ins.prev.csr[CSR_MIP][3]    // MSIP
                            `ifdef S_SUPPORTED
                                , ins.prev.csr[CSR_MIP][9]  // SEIP
                                , ins.prev.csr[CSR_MIP][5]  // STIP
                                , ins.prev.csr[CSR_MIP][1]  // SSIP
                            `endif
                            `ifdef SSCOFPMF_SUPPORTED
                                , ins.prev.csr[CSR_MIP][13] // LCOFIP
                            `endif
                            `ifdef H_SUPPORTED
                                , ins.prev.csr[CSR_MIP][10] // VSEIP
                                , ins.prev.csr[CSR_MIP][6]  // VSTIP
                                , ins.prev.csr[CSR_MIP][2]  // VSSIP
                            `endif
                            }) {
        bins ones = {1'b1};
    }

    mtvec_both: coverpoint ins.current.csr[CSR_MTVEC][1:0] {
        bins direct = {2'b00};
        bins vector = {2'b01};
    }

    // STCE is menvcfg bit 63, which lands in the high half of the CSR when MXLEN is 32
    `ifdef SSTC_SUPPORTED
        `ifdef UDB_MXLEN_64
            menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFG][63] {
                // autofill 0/1
            }
        `else
            menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
                // autofill 0/1
            }
        `endif
    `endif

    csrrs: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csrrc: coverpoint ins.current.insn {
        wildcard bins csrrc = {CSRRC};
    }

    // Building blocks for the Sstc crosses, which check writes to mip.STIP
    `ifdef SSTC_SUPPORTED
        // STCE set, so stimecmp drives STIP and writes to mip.STIP are ignored
        `ifdef UDB_MXLEN_64
            menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFG][63] {
                bins one = {1};
            }
        `else
            menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
                bins one = {1};
            }
        `endif

        // stimecmp written to its minimum or maximum. csr elements are XLEN wide, so on RV32 the
        // 64 bit value is the high and low halves concatenated.
        `ifdef UDB_MXLEN_64
            stimecmp_max_min: coverpoint ins.current.csr[CSR_STIMECMP] {
                bins min = {'0};
                bins max = {'1};
            }
        `else
            stimecmp_max_min: coverpoint {ins.current.csr[CSR_STIMECMPH], ins.current.csr[CSR_STIMECMP]} {
                bins min = {'0};
                bins max = {'1};
            }
        `endif
        write_mip: coverpoint ins.current.insn[31:20] {
            bins write_STIP = {CSR_MIP};
        }
        rs1_STIP: coverpoint ins.current.rs1_val {
            bins stip = {'h20};
        }

    `endif
    mie_zeros: coverpoint ins.current.csr[CSR_MIE][15:0] {
        wildcard bins zeros = {16'b????0?0?0?0?0?0?};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }

    // main coverpoints

    cp_trigger:                 cross priv_mode_m_hs_vs_u_vu, mip_walking, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both;

// TODO: need to figure out how to check writing to mip and sip (Is writing to these with TSBI able to hit the coverpoint?)
    cp_trigger_reg_mip_seip:    cross priv_mode_m_hs_vs_u_vu, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both; // check writing instr to the specific place
    `ifdef SSTC_SUPPORTED
        cp_trigger_sti_sstc:    cross priv_mode_m_hs_vs_u_vu, menvcfg_stce, mstatus_mie, mstatus_sie, mie_ones, mideleg_both, mtvec_both;
    `endif
        // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_m_hs_vs_u_vu, mideleg_zeros, mstatus_mie_one, walking_mie_one;
    cp_enable_zero:             cross priv_mode_m_hs_vs_u_vu, mideleg_zeros, mstatus_mie_one, walking_mie_zero;
    cp_priority_mip:            cross priv_mode_m_hs_vs_u_vu, mideleg_zeros, mstatus_mie_one, mie_ones, mip_pairs;
    cp_priority_mie:            cross priv_mode_m_hs_vs_u_vu, mideleg_zeros, mstatus_mie_one, mip_all_ones, mie_pairs;
    `ifdef S_SUPPORTED
        cp_priority_mideleg:        cross priv_mode_m_hs_vs_u_vu, mstatus_mie_one, mip_pairs;
    `endif
    cp_wfi_m:                   cross priv_mode_m, mstatus_mie, mstatus_tw, wfi;
    cp_wfi:                     cross priv_mode_hs_vs_u_vu, mstatus_mie, mstatus_tw_zero, wfi;
    cp_wfi_timeout:             cross priv_mode_hs_vs_u_vu, mstatus_mie, mie_mtie, mstatus_tw_one, wfi;

    `ifdef SSTC_SUPPORTED // need to modify this one to check more stuff
        cp_write_stip_sstc_csrrs: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrs, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
        cp_write_stip_sstc_csrrc: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrc, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
    `endif


endgroup

function void interruptssm2_sample(int hart, int issue, ins_t ins);
    InterruptsSm2_cg.sample(ins);
endfunction
