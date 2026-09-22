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

`define COVER_INTERRUPTSSM

covergroup InterruptsSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    // Uses ins.prev instead of ins.current because RVVI updates CSRs after instruction retirement,
    // so ins.current shows post-trap state while ins.prev shows pre-trap state.
    // mip is the exception: the instruction that raises an interrupt records the new pending bit and
    // the trap's CSR updates together, so mip is read from ins.current to line up with ins.prev mstatus.
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

    // Privilege modes this config implements.
    priv_mode_interrupts: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
        bins M_mode = {3'b011};
        `ifdef S_SUPPORTED
            bins HS_mode = {3'b001};
        `endif
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b101};
            bins VU_mode = {3'b100};
        `endif
        `ifdef U_SUPPORTED
            bins U_mode = {3'b000};
        `endif
    }

    // mideleg written all 0s or all 1s in every delegable field.
    // mideleg does not exist without S, so it becomes a trivial always-hit bin that leaves the
    // crosses below intact.
    `ifdef S_SUPPORTED
        mideleg_both: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
            // Sail does not let M-level interrupts be delegated (mideleg MEI, MTI, and MSI stay 0),
            // so bits 11, 7, and 3 are don't care in ones.
            `ifdef SSCOFPMF_SUPPORTED
                wildcard bins ones  = {16'b??1???1???1???1?}; // LCOFI, SEI, STI, SSI delegated
                wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
            `else
                wildcard bins ones  = {16'b??????1???1???1?}; // SEI, STI, SSI delegated
                wildcard bins zeros = {16'b????0?0?0?0?0?0?};
            `endif
        }
    `else
        mideleg_both: coverpoint 1'b1 {
            bins no_mideleg = {1'b1};
        }
    `endif

    // mideleg written all 0s. Bits 12, 10, 6, and 2 are don't care because H hardwires them to 1.
    // mideleg does not exist without S, so it becomes a trivial always-hit bin that leaves the
    // crosses below intact.
    `ifdef S_SUPPORTED
        mideleg_zeros: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
            wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
        }
    `else
        mideleg_zeros: coverpoint 1'b1 {
            bins no_mideleg = {1'b1};
        }
    `endif

    // Interrupt bits the mideleg pair coverpoints use: SEI, STI, SSI, and LCOFI with Sscofpmf.
    // H hardwires mideleg bits 12, 10, 6, and 2 to 1, and Sail does not let M-level interrupts
    // (MEI, MTI, MSI) be delegated, so both are left out.
    `ifdef SSCOFPMF_SUPPORTED
        `define SM_NOH_MASK 16'h2222
    `else
        `define SM_NOH_MASK 16'h0222
    `endif
    `define SM_MIDELEG_NOH (ins.current.csr[CSR_MIDELEG][15:0] & `SM_NOH_MASK)
    `define SM_MIP_NOH (ins.current.csr[CSR_MIP][15:0] & `SM_NOH_MASK)

    // Interrupt bits this config supports: MEI, MTI, MSI, plus the S, Sscofpmf, and H interrupts
    `ifdef S_SUPPORTED
        `ifdef H_SUPPORTED
            `define SM_INT_MASK (16'h0888 | `SM_NOH_MASK | 16'h0444)
        `else
            `define SM_INT_MASK (16'h0888 | `SM_NOH_MASK)
        `endif
    `else
        `define SM_INT_MASK 16'h0888
    `endif

    // mideleg delegates exactly one interrupt of the pending mip pair and nothing else.
    // x & -x keeps the lowest set bit; x & (x-1) clears it, leaving the higher bit of the pair.
    `ifdef S_SUPPORTED
        mideleg_one_of_mip_pair: coverpoint
            ((`SM_MIDELEG_NOH == (`SM_MIP_NOH & -`SM_MIP_NOH))          ? 2'd1 :
             (`SM_MIDELEG_NOH == (`SM_MIP_NOH & (`SM_MIP_NOH - 16'd1))) ? 2'd2 : 2'd0) {
            bins lower_delegated  = {2'd1};
            bins higher_delegated = {2'd2};
        }
    `endif

    // mie written all 1s: reduction AND over every enable bit the config supports
    mie_ones: coverpoint (&{ins.current.csr[CSR_MIE][11],  // MEIE
                            ins.current.csr[CSR_MIE][7],   // MTIE
                            ins.current.csr[CSR_MIE][3]    // MSIE
                            `ifdef S_SUPPORTED
                                , ins.current.csr[CSR_MIE][9]  // SEIE
                                , ins.current.csr[CSR_MIE][5]  // STIE
                                , ins.current.csr[CSR_MIE][1]  // SSIE
                            `endif
                            `ifdef SSCOFPMF_SUPPORTED
                                , ins.current.csr[CSR_MIE][13] // LCOFIE
                            `endif
                            `ifdef H_SUPPORTED
                                , ins.current.csr[CSR_MIE][10] // VSEIE
                                , ins.current.csr[CSR_MIE][6]  // VSTIE
                                , ins.current.csr[CSR_MIE][2]  // VSSIE
                            `endif
                            }) {
        bins ones = {1'b1};
    }


    mie_mtie: coverpoint ins.current.csr[CSR_MIE][7] {
         // autofill 0/1
    }

    mie_mtie_one: coverpoint ins.current.csr[CSR_MIE][7] {
         bins one = {1'b1};
    }

    // Exactly one interrupt enabled. Each bin requires mie[15:0] to contain exactly one supported
    // interrupt-enable bit and no other set bits.
    walking_mie_one: coverpoint ins.current.csr[CSR_MIE][15:0] {
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
    walking_mie_zero: coverpoint ((~ins.current.csr[CSR_MIE][15:0]) & `SM_INT_MASK) {
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

    // The single enabled interrupt in walking_mie_one is pending
    mip_matches_mie_one: coverpoint ((ins.current.csr[CSR_MIP][15:0] & ins.current.csr[CSR_MIE][15:0]) != 16'h0) {
        bins pending = {1'b1};
    }

    // The single disabled interrupt in walking_mie_zero is pending
    mip_matches_mie_zero: coverpoint ((ins.current.csr[CSR_MIP][15:0] & ~ins.current.csr[CSR_MIE][15:0] & `SM_INT_MASK) != 16'h0) {
        bins pending = {1'b1};
    }

    // Exactly two interrupts enabled: mie masked to the bits this config supports has exactly two
    // bits set. One bin per pair of supported interrupt bits: 3 for M only, 15 for M+S,
    // 21 for M+S+Sscofpmf, 36 for M+S+H, and 45 for M+S+H+Sscofpmf.
    mie_pairs: coverpoint (ins.current.csr[CSR_MIE][15:0] & `SM_INT_MASK) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`SM_INT_MASK) == 0);
    }

    // One interrupt pending at a time. Bits 15:14, 12, 8, 4, and 0 are don't care because they are
    // either tied to zero or driven by the platform (SGEIP) rather than by the test.
    mip_walking: coverpoint ins.current.csr[CSR_MIP][15:0] {
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
    // bits set. One bin per pair of supported interrupt bits: 3 for M only, 15 for M+S,
    // 21 for M+S+Sscofpmf, 36 for M+S+H, and 45 for M+S+H+Sscofpmf.
    mip_pairs: coverpoint (ins.current.csr[CSR_MIP][15:0] & `SM_INT_MASK) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`SM_INT_MASK) == 0);
    }

    // Exactly two S-level interrupts pending (no M-level or H interrupts)
    `ifdef S_SUPPORTED
        mip_pairs_noh: coverpoint `SM_MIP_NOH {
            bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`SM_NOH_MASK) == 0);
        }
    `endif

    // Every interrupt pending at once: reduction AND over every pending bit the config supports
    mip_all_ones: coverpoint (&{ins.current.csr[CSR_MIP][11],  // MEIP
                            ins.current.csr[CSR_MIP][7],   // MTIP
                            ins.current.csr[CSR_MIP][3]    // MSIP
                            `ifdef S_SUPPORTED
                                , ins.current.csr[CSR_MIP][9]  // SEIP
                                , ins.current.csr[CSR_MIP][5]  // STIP
                                , ins.current.csr[CSR_MIP][1]  // SSIP
                            `endif
                            `ifdef SSCOFPMF_SUPPORTED
                                , ins.current.csr[CSR_MIP][13] // LCOFIP
                            `endif
                            `ifdef H_SUPPORTED
                                , ins.current.csr[CSR_MIP][10] // VSEIP
                                , ins.current.csr[CSR_MIP][6]  // VSTIP
                                , ins.current.csr[CSR_MIP][2]  // VSSIP
                            `endif
                            }) {
        bins ones = {1'b1};
    }

    mtvec_both: coverpoint ins.current.csr[CSR_MTVEC][1:0] {
        bins direct = {2'b00};
        bins vector = {2'b01};
    }

    csrrs: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csrrc: coverpoint ins.current.insn {
        wildcard bins csrrc = {CSRRC};
    }

    // Building blocks for the software writes to mip.SSIP, mip.SEIP, and sip.SSIP
    `ifdef S_SUPPORTED
        csr_mip: coverpoint ins.current.insn[31:20] {
            bins mip = {CSR_MIP};
        }
        csr_sip: coverpoint ins.current.insn[31:20] {
            bins sip = {CSR_SIP};
        }
        // SSIP fits in the 5-bit immediate, so csrrsi writes the value in insn[19:15] instead of rs1
        csrrs_csrrsi: coverpoint ins.current.insn {
            wildcard bins csrrs_csrrsi = {CSRRS, CSRRSI};
        }
        rs1_ssip: coverpoint (ins.current.insn[14] ? XLEN'(ins.current.insn[19:15]) : ins.current.rs1_val) {
            bins ssip = {'h2};
        }
        rs1_seip: coverpoint ins.current.rs1_val {
            bins seip = {'h200};
        }
        // sip.SSIP is read-only zero unless SSI is delegated
        mideleg_ssi_one: coverpoint ins.current.csr[CSR_MIDELEG][1] {
            bins one = {1'b1};
        }
    `endif

    // Building blocks for the Sstc crosses, which check writes to mip.STIP
    `ifdef SSTC_SUPPORTED
        // STCE set, so stimecmp drives STIP and writes to mip.STIP are ignored
        // STCE is menvcfg bit 63, which lands in the high half of the CSR when MXLEN is 32
        `ifdef UDB_MXLEN_64
            menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFG][63] {
                bins one = {1};
            }
            menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFG][63] {
                // autofill 0/1
            }
        `else
            menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
                bins one = {1};
            }
            menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
                // autofill 0/1
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

    // Interrupts raised through T-SBI fire right after the mret back to S/U, so they are recorded on
    // the mret. Before the mret, MPP holds the mode it returns to and MPIE the MIE it restores.
    mret_insn: coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    `ifdef U_SUPPORTED
        mstatus_mpp: coverpoint ins.prev.csr[CSR_MSTATUS][12:11] {
            `ifdef S_SUPPORTED
                bins S_mode = {2'b01};
            `endif
            bins U_mode = {2'b00};
        }
    `endif
    mstatus_mpie: coverpoint ins.prev.csr[CSR_MSTATUS][7] {
        // autofill 0/1
    }

    // main coverpoints

    cp_trigger:                 cross priv_mode_interrupts, mip_walking, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both {
        // MSI and MTI are the only interrupts with no pending bit reachable below M: they cannot be
        // delegated, so once pending they are enabled regardless of mstatus.MIE and are taken on the
        // mret out of the T-SBI handler that set them, before any S/U instruction retires.
        // cp_trigger_tsbi records them there. Everything else is reachable in S/U: sip.SSIP and
        // sip.LCOFIP are read-write, stimecmp is S-accessible when menvcfg.STCE is 1, and MEI/SEI
        // come from the interrupt controller.
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000} &&
                           binsof(mip_walking) intersect {16'h0008, 16'h0080};
        // The same argument applies wherever the mode cannot reach the pending bit either.
        // sip.LCOFIP only aliases mip.LCOFIP when mideleg.LCOFI is set, and U-mode has no sip at
        // all, so an undelegated LCOFI cannot be raised from S or U.
        // mideleg_both, mstatus_sie.one and mip_walking.stip/.lcofip all need S, and the bins below
        // only describe delegation, so the whole group is gated on S_SUPPORTED.
        `ifdef S_SUPPORTED
            `ifdef SSCOFPMF_SUPPORTED
                // In U-mode the pending bit is out of reach whatever mideleg says, because U has no sip
            // at all, so the T-SBI call that sets it takes the interrupt on its own mret.
            ignore_bins lcofi_u_has_no_sip = binsof(priv_mode_interrupts) intersect {3'b000} &&
                                             binsof(mip_walking.lcofip);
            ignore_bins lcofi_needs_mideleg = binsof(priv_mode_interrupts) intersect {3'b001} &&
                                                  binsof(mip_walking.lcofip) && binsof(mideleg_both.zeros);
                // With sstatus.SIE set, a delegated LCOFI is taken on the csrrs that made it pending,
                // so no later S-mode instruction retires with it still showing in mip.
                ignore_bins lcofi_taken_at_once_in_s = binsof(priv_mode_interrupts) intersect {3'b001} &&
                                                       binsof(mip_walking.lcofip) && binsof(mstatus_sie.one);
            `endif
            // U-mode reaches neither sip.STIP (read-only) nor stimecmp, so an undelegated STI can
            // only be raised for it from M and is taken on the mret.
            // Same for STI: sip.STIP is read-only and U cannot reach stimecmp, so every U-mode STI
            // is raised from M and taken on the mret, whatever mideleg says.
            ignore_bins u_cannot_raise_sti = binsof(priv_mode_interrupts) intersect {3'b000} &&
                                             binsof(mip_walking.stip);
        `endif
    }
    `ifdef U_SUPPORTED
        cp_trigger_tsbi:        cross priv_mode_m, mret_insn, mstatus_mpp, mip_walking, mstatus_mpie, mstatus_sie, mideleg_both, mie_ones, mtvec_both {
            // MEI is the only interrupt with no mip write path: it is raised by a store to the
            // interrupt controller from whatever mode the test runs in, so it never sits pending
            // across an mret. SEI and SSI do reach mip through T-SBI (MIP_SEIP, MIP_SSIP) and are
            // recorded here.
            ignore_bins mei_has_no_mip_write = binsof(mip_walking) intersect {16'h0800};
            `ifdef SSCOFPMF_SUPPORTED
                `ifdef S_SUPPORTED
                    // S-mode raises LCOFI by writing sip.LCOFIP itself, so on the way back to S it is
                    // never still pending here. U-mode has no sip access and keeps the T-SBI path.
                    ignore_bins lcofi_is_direct_from_s =
                        binsof(mstatus_mpp.S_mode) && binsof(mip_walking.lcofip);
                `endif
            `endif
        }
    `endif

    // These are all S-level interrupts, hence the S_SUPPORTED gate. mip is an M CSR, so the mip
    // flavours are written from M directly and from S/U through T-SBI. sip is not: sip.SSIP is
    // read-write, so cp_trigger_reg_sip_ssip is an ordinary S-mode csrrs with no T-SBI involved,
    // which is why it drops the mstatus.MIE dimension and requires mideleg.SSI.
    `ifdef S_SUPPORTED
        cp_trigger_reg_mip_ssip: cross csrrs_csrrsi, csr_mip, rs1_ssip, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both;
        cp_trigger_reg_mip_seip: cross csrrs, csr_mip, rs1_seip, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both;
        cp_trigger_reg_sip_ssip: cross csrrs_csrrsi, csr_sip, rs1_ssip, mstatus_sie, mideleg_ssi_one, mie_ones, mtvec_both;
    `endif
    `ifdef SSTC_SUPPORTED
        cp_trigger_sti_sstc:    cross priv_mode_interrupts, menvcfg_stce, mstatus_mie, mstatus_sie, mie_ones, mideleg_both, mtvec_both, stimecmp_max_min {
            // menvcfg.STCE = 1 is what makes stimecmp S-accessible, so S-mode arms its own timer and
            // the STI is taken in S-mode, here. Only U-mode still goes through T-SBI, where an
            // undelegated STI from stimecmp = 0 fires on the mret and cp_trigger_sti_sstc_tsbi
            // records it.
            // U-mode cannot reach stimecmp whatever menvcfg.STCE says, so the armed-timer case is
            // always raised from M through T-SBI and taken on the mret, for either mideleg value.
            ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b000} && binsof(menvcfg_stce) intersect {1} &&
                               binsof(stimecmp_max_min.min);
        }
        `ifdef U_SUPPORTED
            cp_trigger_sti_sstc_tsbi: cross priv_mode_m, mret_insn, mstatus_mpp, menvcfg_stce, mstatus_mpie, mstatus_sie, mie_ones, mideleg_both, mtvec_both, stimecmp_max_min {
                // Complement of the cp_trigger_sti_sstc ignore above, so the two still partition the
                // space: only the U-mode STCE = 1 case arrives through T-SBI and is recorded here.
                ignore_bins direct = binsof(menvcfg_stce) intersect {0} || binsof(mideleg_both.ones) || binsof(stimecmp_max_min.max)
                                     `ifdef S_SUPPORTED
                                         || binsof(mstatus_mpp.S_mode)
                                     `endif
                                     ;
            }
        `endif
    `endif
        // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, walking_mie_one, mip_matches_mie_one {
        // MSI, MTI, STI, and LCOFI are raised through T-SBI in S/U and covered by cp_enable_one_tsbi
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000} &&
                           binsof(walking_mie_one) intersect {16'h0008, 16'h0080, 16'h0020, 16'h2000};
    }
    `ifdef U_SUPPORTED
        cp_enable_one_tsbi:     cross priv_mode_m, mret_insn, mstatus_mpp, mideleg_zeros, walking_mie_one, mip_matches_mie_one {
            // MEI, SEI, and SSI are raised directly in S/U and covered by cp_enable_one
            ignore_bins direct = binsof(walking_mie_one) intersect {16'h0800, 16'h0200, 16'h0002};
            `ifdef SSCOFPMF_SUPPORTED
                `ifdef S_SUPPORTED
                    // As in cp_trigger_tsbi: S-mode raises LCOFI through sip.LCOFIP itself, so it is
                    // never still pending on the mret back to S.
                    ignore_bins lcofi_is_direct_from_s =
                        binsof(mstatus_mpp.S_mode) && binsof(walking_mie_one.lcofie);
                `endif
            `endif
        }
    `endif
    cp_enable_zero:             cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, walking_mie_zero, mip_matches_mie_zero;
    // In S/U, mie and mideleg are written through T-SBI, so the priority interrupts fire right after
    // the mret and are covered by the _tsbi crosses
    cp_priority_mip:            cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, mie_ones, mip_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000};
    }
    cp_priority_mie:            cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, mip_all_ones, mie_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000};
    }
    `ifdef U_SUPPORTED
        cp_priority_mip_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpp, mideleg_zeros, mie_ones, mip_pairs;
        cp_priority_mie_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpp, mideleg_zeros, mip_all_ones, mie_pairs;
    `endif
    `ifdef S_SUPPORTED
        cp_priority_mideleg:        cross priv_mode_interrupts, mstatus_mie_one, mie_ones, mip_pairs_noh, mideleg_one_of_mip_pair {
            ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000};
        }
        cp_priority_mideleg_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpp, mie_ones, mip_pairs_noh, mideleg_one_of_mip_pair;
    `endif
    cp_wfi_m:                   cross priv_mode_m, mstatus_mie, mstatus_tw, wfi, mideleg_zeros;

    // H modes not included as wfi behavior is additionally affected by hstatus.VTW - TODO: test in InterruptsH
    // WFI with TW = 0 is exercised in the most privileged mode below M that this config implements.
    // The mode is selected with a macro rather than an `ifdef inside the cross argument list: on a hart
    // with neither S nor U (cv32e20 implements Sm and no lower mode) the inline form leaves a cross with
    // no privilege axis at all, which still elaborates and fills from M-mode WFIs -- a silent duplicate
    // of cp_wfi_m reporting coverage for a mode the hart does not have. Dropping the coverpoint is right.
    `ifdef S_SUPPORTED
        `define SM_WFI_PRIV priv_mode_s
    `elsif U_SUPPORTED
        `define SM_WFI_PRIV priv_mode_u
    `endif
    `ifdef SM_WFI_PRIV
        cp_wfi:                 cross `SM_WFI_PRIV, mstatus_mie, mie_mtie_one, mstatus_tw_zero, wfi, mideleg_zeros;
    `endif

    // mstatus.TW = 1 traps WFI in every mode below M, so the timeout applies whenever any lower mode
    // exists, not only when S does. S-mode implies U-mode, so S_SUPPORTED means both bins of
    // priv_mode_s_u are reachable and U without S needs priv_mode_u alone. cp_wfi_timeout_tw_zero stays
    // under S_SUPPORTED: U-mode WFI only times out with TW = 0 when S is implemented.
    `ifdef S_SUPPORTED
        cp_wfi_timeout:                     cross priv_mode_s_u, mstatus_mie, mie_mtie, mstatus_tw_one, wfi;
        cp_wfi_timeout_tw_zero:             cross priv_mode_u, mstatus_mie, mie_mtie, mstatus_tw_zero, wfi;
    `elsif U_SUPPORTED
        cp_wfi_timeout:                     cross priv_mode_u, mstatus_mie, mie_mtie, mstatus_tw_one, wfi;
    `endif

    `ifdef SSTC_SUPPORTED // need to modify this one to check more stuff
        cp_write_stip_sstc_csrrs: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrs, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
        cp_write_stip_sstc_csrrc: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrc, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
    `endif


endgroup

`undef SM_INT_MASK
`undef SM_NOH_MASK
`undef SM_MIDELEG_NOH
`undef SM_MIP_NOH
`ifdef SM_WFI_PRIV
    `undef SM_WFI_PRIV
`endif

function void interruptssm_sample(int hart, int issue, ins_t ins);
    InterruptsSm_cg.sample(ins);
endfunction
