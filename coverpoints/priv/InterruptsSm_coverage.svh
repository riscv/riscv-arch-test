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

// Classify mideleg for mideleg_both: 1 when every implemented S-level interrupt is delegated, 0 when
// no S- or M-level interrupt is, and 2 otherwise. H hardwires the VS bits to 1, so they are not checked.
function automatic logic [1:0] interruptssm_mideleg_class(logic [15:0] mideleg);
    if ((mideleg & `INTR_S_LEVEL) == `INTR_S_LEVEL) return 2'd1;
    if ((mideleg & (`INTR_S_LEVEL | 16'h0888)) == 16'h0) return 2'd0;
    return 2'd2;
endfunction

covergroup InterruptsSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    // Uses ins.prev instead of ins.current because RVVI updates CSRs after instruction retirement,
    // so ins.current shows post-trap state while ins.prev shows pre-trap state.
    // mip is the exception: the instruction that raises an interrupt records the new pending bit and
    // the trap's CSR updates together, so mip is read from ins.current to line up with ins.prev mstatus.
    mstatus_mie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
        // autofill 0/1
    }
    mstatus_mie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
        bins one = {1};
    }
    mstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
        bins zero = {0};
        `ifdef S_SUPPORTED
            bins one = {1}; // SIE is read-only zero without S
        `endif
    }
    mstatus_tw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
        bins zero = {0};
        `ifdef U_SUPPORTED
            bins one = {1}; // TW is read-only zero without a mode below M
        `endif
    }
    mstatus_tw_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
        bins zero = {0}; // WFI is permitted outside M mode
    }
    `ifdef U_SUPPORTED
        mstatus_tw_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
            bins one = {1}; // WFI outside M mode traps after the implementation-defined timeout
        }
    `endif
    `ifdef H_SUPPORTED
        // hstatus.VTW: with mstatus.TW = 0, VS-mode WFI raises virtual instruction after a bounded time when set
        hstatus_vtw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")[0] {
            // autofill 0/1
        }
        hstatus_vtw_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")[0] {
            bins zero = {0};
        }
        hstatus_vtw_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")[0] {
            bins one = {1};
        }
    `endif

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
        // Sail does not let M-level interrupts be delegated (mideleg MEI, MTI, and MSI stay 0),
        // so bits 11, 7, and 3 are don't care in ones.
        mideleg_both: coverpoint interruptssm_mideleg_class(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0]) {
            bins ones  = {2'd1}; // every implemented S-level interrupt (LCOFI, SEI, STI, SSI) delegated
            bins zeros = {2'd0};
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
        mideleg_zeros: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0] {
            wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
        }
    `else
        mideleg_zeros: coverpoint 1'b1 {
            bins no_mideleg = {1'b1};
        }
    `endif

    // mideleg delegates exactly one interrupt of the pending mip pair and nothing else.
    // x & -x keeps the lowest set bit; x & (x-1) clears it, leaving the higher bit of the pair.
    `ifdef S_SUPPORTED
        mideleg_one_of_mip_pair: coverpoint
            (((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0] & `INTR_S_LEVEL) ==
              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL) & -(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL))) ? 2'd1 :
             ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0] & `INTR_S_LEVEL) ==
              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL) & ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL) - 16'd1))) ? 2'd2 : 2'd0) {
            bins lower_delegated  = {2'd1};
            bins higher_delegated = {2'd2};
        }
    `endif

    // mie written all 1s: every enable bit the config supports is set
    mie_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_ALL) == `INTR_ALL) {
        bins ones = {1'b1};
    }

    mie_mtie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mtie")[0] {
        bins zero = {1'b0};
        `ifdef UDB_MTI_INTR_IMPL
            bins one = {1'b1}; // MTIE is read-only zero without MTI
        `endif
    }

    `ifdef UDB_MTI_INTR_IMPL
        mie_mtie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mtie")[0] {
            bins one = {1'b1};
        }
    `endif

    // Exactly one interrupt enabled. Each bin requires mie[15:0] to contain exactly one supported
    // interrupt-enable bit and no other set bits.
    walking_mie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] {
        `ifdef UDB_MEI_INTR_IMPL
            bins meie = {16'h0800};
        `endif
        `ifdef UDB_MTI_INTR_IMPL
            bins mtie = {16'h0080};
        `endif
        `ifdef UDB_MSI_INTR_IMPL
            bins msie = {16'h0008};
        `endif
        `ifdef S_SUPPORTED
            `ifdef UDB_SEI_INTR_IMPL
                bins seie = {16'h0200};
            `endif
            `ifdef UDB_STI_INTR_IMPL
                bins stie = {16'h0020};
            `endif
            `ifdef UDB_SSI_INTR_IMPL
                bins ssie = {16'h0002};
            `endif
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
    walking_mie_zero: coverpoint ((~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0]) & `INTR_ALL) {
        `ifdef UDB_MEI_INTR_IMPL
            bins meie = {16'h0800};
        `endif
        `ifdef UDB_MTI_INTR_IMPL
            bins mtie = {16'h0080};
        `endif
        `ifdef UDB_MSI_INTR_IMPL
            bins msie = {16'h0008};
        `endif
        `ifdef S_SUPPORTED
            `ifdef UDB_SEI_INTR_IMPL
                bins seie = {16'h0200};
            `endif
            `ifdef UDB_STI_INTR_IMPL
                bins stie = {16'h0020};
            `endif
            `ifdef UDB_SSI_INTR_IMPL
                bins ssie = {16'h0002};
            `endif
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
    mip_matches_mie_one: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0]) != 16'h0) {
        bins pending = {1'b1};
    }

    // The single disabled interrupt in walking_mie_zero is pending
    mip_matches_mie_zero: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & ~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_ALL) != 16'h0) {
        bins pending = {1'b1};
    }

    // Exactly two interrupts enabled: mie masked to the bits this config supports has exactly two
    // bits set. One bin per pair of supported interrupt bits: 3 for M only, 15 for M+S,
    // 21 for M+S+Sscofpmf, 36 for M+S+H, and 45 for M+S+H+Sscofpmf.
    mie_pairs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_ALL) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_ALL) == 0);
    }

    // One interrupt pending at a time. Bits 15:14, 12, 8, 4, and 0 are don't care because they are
    // either tied to zero or driven by the platform (SGEIP) rather than by the test.
    mip_walking: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] {
        `ifdef UDB_MEI_INTR_IMPL
            wildcard bins meip = {16'b??0?100?000?000?};
        `endif
        `ifdef UDB_MTI_INTR_IMPL
            wildcard bins mtip = {16'b??0?000?100?000?};
        `endif
        `ifdef UDB_MSI_INTR_IMPL
            wildcard bins msip = {16'b??0?000?000?100?};
        `endif
        `ifdef S_SUPPORTED
            `ifdef UDB_SEI_INTR_IMPL
                wildcard bins seip = {16'b??0?001?000?000?};
            `endif
            `ifdef UDB_STI_INTR_IMPL
                wildcard bins stip = {16'b??0?000?001?000?};
            `endif
            `ifdef UDB_SSI_INTR_IMPL
                wildcard bins ssip = {16'b??0?000?000?001?};
            `endif
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
    mip_pairs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_ALL) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_ALL) == 0);
    }

    // Exactly two S-level interrupts pending (no M-level or H interrupts)
    `ifdef S_SUPPORTED
        mip_pairs_noh: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL) {
            bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_S_LEVEL) == 0);
        }
    `endif

    // Every interrupt pending at once: every pending bit the config supports is set
    mip_all_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_ALL) == `INTR_ALL) {
        bins ones = {1'b1};
    }

    mtvec_both: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtvec", "mode")[1:0] {
        `ifdef UDB_MTVEC_MODES_0
            bins direct = {2'b00};
        `endif
        `ifdef UDB_MTVEC_MODES_1
            bins vector = {2'b01};
        `endif
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
        `ifdef UDB_SSI_INTR_IMPL
            mideleg_ssi_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "ssip")[0] {
                bins one = {1'b1};
            }
        `endif
    `endif

    // Building blocks for the Sstc crosses, which check writes to mip.STIP
    `ifdef SSTC_SUPPORTED
        // STCE set, so stimecmp drives STIP and writes to mip.STIP are ignored
        // STCE is menvcfg bit 63, which lands in the high half of the CSR when MXLEN is 32
        `ifdef UDB_MXLEN_64
            menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "stce")[0] {
                bins one = {1};
            }
            menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "stce")[0] {
                // autofill 0/1
            }
        `else
            menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfgh", "stce")[0] {
                bins one = {1};
            }
            menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfgh", "stce")[0] {
                // autofill 0/1
            }
        `endif

        // stimecmp written to its minimum or maximum. csr elements are XLEN wide, so on RV32 the
        // 64 bit value is the high and low halves concatenated.
        `ifdef UDB_MXLEN_64
            stimecmp_max_min: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "stimecmp") {
                bins min = {'0};
                bins max = {'1};
            }
        `else
            stimecmp_max_min: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmph", "stimecmph"), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "stimecmp")} {
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
    mie_zeros: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] {
        wildcard bins zeros = {16'b????0?0?0?0?0?0?};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }

    // Interrupts raised through T-SBI fire right after the mret back to S/U/VS/VU, so they are recorded
    // on the mret. Before the mret, MPP (and with H, MPV) holds the mode it returns to and MPIE the MIE
    // it restores.
    mret_insn: coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    `ifdef U_SUPPORTED
        // MPV is mstatus bit 39, which lands in mstatush when MXLEN is 32.  It reads 0 without H.
        `ifdef UDB_MXLEN_64
            `define SM_MPV get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0]
        `else
            `define SM_MPV get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0]
        `endif
        mstatus_mpv_mpp: coverpoint {`SM_MPV, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
            `ifdef S_SUPPORTED
                bins S_mode = {3'b001};
            `endif
            bins U_mode = {3'b000};
            `ifdef H_SUPPORTED
                bins VS_mode = {3'b101};
                bins VU_mode = {3'b100};
            `endif
        }
    `endif
    mstatus_mpie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie")[0] {
        // autofill 0/1
    }

    // main coverpoints

    cp_trigger:                 cross priv_mode_interrupts, mip_walking, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both {
        // MSI and MTI are the only interrupts with no pending bit reachable below M: they cannot be
        // delegated, so once pending they are enabled regardless of mstatus.MIE and are taken on the
        // mret out of the T-SBI handler that set them, before any S/U instruction retires.
        // cp_trigger_tsbi records them there. Everything else is reachable in S/U: sip.SSIP and
        // sip.LCOFIP are read-write, stimecmp is S-accessible when menvcfg.STCE is 1, and MEI/SEI
        // come from the interrupt controller. VS and VU are like U (3'b101, 3'b100).
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100} &&
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
                // VS and VU are the same: in VS, sip is vsip.
                ignore_bins lcofi_u_has_no_sip = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                                 binsof(mip_walking.lcofip);
                ignore_bins lcofi_needs_mideleg = binsof(priv_mode_interrupts) intersect {3'b001} &&
                                                  binsof(mip_walking.lcofip) && binsof(mideleg_both.zeros);
            `endif
            // Same for STI: sip.STIP is read-only and U cannot reach stimecmp, so every U-mode STI
            // is raised from M and taken on the mret, whatever mideleg says. VS and VU likewise.
            `ifdef UDB_STI_INTR_IMPL
                ignore_bins u_cannot_raise_sti = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                                 binsof(mip_walking.stip);
            `endif
        `endif
        `ifdef H_SUPPORTED
            // The VS-level interrupts are raised through hvip, which only M and HS can write. Below HS
            // the T-SBI call that writes it returns with the interrupt enabled, so it is taken on the mret.
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       (binsof(mip_walking.vseip) || binsof(mip_walking.vstip) || binsof(mip_walking.vssip));
        `endif
    }
    `ifdef U_SUPPORTED
        cp_trigger_tsbi:        cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mip_walking, mstatus_mpie, mstatus_sie, mideleg_both, mie_ones, mtvec_both {
            `ifdef H_SUPPORTED
                // HS writes hvip itself, so its VS-level interrupts never sit pending across an mret
                ignore_bins hs_writes_hvip = binsof(mstatus_mpv_mpp.S_mode) &&
                                             (binsof(mip_walking.vseip) || binsof(mip_walking.vstip) || binsof(mip_walking.vssip));
            `endif
            // MEI is the only interrupt with no mip write path: it is raised by a store to the
            // interrupt controller from whatever mode the test runs in, so it never sits pending
            // across an mret. Every other interrupt can be written to mip through T-SBI for either
            // mideleg value (MIP_SEIP, MIP_SSIP, LCOFI, and the SSI fallback when the DUT defines no
            // RVMODEL_SET_SSW_INT). cp_trigger also records SSI and LCOFI when S writes sip itself
            // or the DUT raises SSI through its interrupt controller.
            ignore_bins mei_has_no_mip_write = binsof(mip_walking) intersect {16'h0800};
        }
    `endif

    // These are all S-level interrupts, hence the S_SUPPORTED gate. mip is an M CSR, so the mip
    // flavours are written from M directly and from S/U through T-SBI. sip is not: sip.SSIP is
    // read-write, so cp_trigger_reg_sip_ssip is an ordinary S-mode csrrs with no T-SBI involved,
    // which is why it drops the mstatus.MIE dimension and requires mideleg.SSI.
    `ifdef S_SUPPORTED
        `ifdef UDB_SSI_INTR_IMPL
            cp_trigger_reg_mip_ssip: cross csrrs_csrrsi, csr_mip, rs1_ssip, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both;
            cp_trigger_reg_sip_ssip: cross csrrs_csrrsi, csr_sip, rs1_ssip, mstatus_sie, mideleg_ssi_one, mie_ones, mtvec_both;
        `endif
        `ifdef UDB_SEI_INTR_IMPL
            cp_trigger_reg_mip_seip: cross csrrs, csr_mip, rs1_seip, mstatus_mie, mstatus_sie, mideleg_both, mie_ones, mtvec_both;
        `endif
    `endif
    `ifdef SSTC_SUPPORTED
        cp_trigger_sti_sstc:    cross priv_mode_interrupts, menvcfg_stce, mstatus_mie, mstatus_sie, mie_ones, mideleg_both, mtvec_both, stimecmp_max_min {
            // U-mode cannot write stimecmp, so its STCE = 1 STI fires on the T-SBI mret and only
            // cp_trigger_sti_sstc_tsbi records it.
            ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(menvcfg_stce) intersect {1} &&
                               binsof(stimecmp_max_min.min);
        }
        `ifdef U_SUPPORTED
            // Overlaps cp_trigger_sti_sstc except for U-mode with STCE = 1 and stimecmp = 0.
            cp_trigger_sti_sstc_tsbi: cross priv_mode_m, mret_insn, mstatus_mpv_mpp, menvcfg_stce, mstatus_mpie, mstatus_sie, mie_ones, mideleg_both, mtvec_both, stimecmp_max_min {
                `ifdef S_SUPPORTED
                    // With STCE = 1, S-mode arms stimecmp itself, so no T-SBI mret returns to S
                    // with the timer armed.
                    ignore_bins s_writes_stimecmp = binsof(mstatus_mpv_mpp.S_mode) && binsof(menvcfg_stce) intersect {1} &&
                                                    binsof(stimecmp_max_min.min);
                `endif
            }
        `endif
    `endif
        // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, walking_mie_one, mip_matches_mie_one {
        // MSI, MTI, STI, and LCOFI are raised through T-SBI in S/U/VS/VU and covered by cp_enable_one_tsbi
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100} &&
                           binsof(walking_mie_one) intersect {16'h0008, 16'h0080, 16'h0020, 16'h2000};
        `ifdef H_SUPPORTED
            // so are the VS-level interrupts below HS (hvip)
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       binsof(walking_mie_one) intersect {16'h0400, 16'h0040, 16'h0004};
        `endif
    }
    `ifdef U_SUPPORTED
        cp_enable_one_tsbi:     cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mideleg_zeros, walking_mie_one, mip_matches_mie_one {
            // As in cp_trigger_tsbi, MEI has no mip write path, so it never sits pending across an mret.
            ignore_bins mei_has_no_mip_write = binsof(walking_mie_one) intersect {16'h0800};
        }
    `endif
    // No _tsbi twin: cp_enable_zero checks that the disabled interrupt does not fire, so the S/U
    // instruction retires with it pending and is observed directly.
    cp_enable_zero:             cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, walking_mie_zero, mip_matches_mie_zero;
    // In S/U/VS/VU, mie and mideleg are written through T-SBI, so the priority interrupts fire right after
    // the mret and are covered by the _tsbi crosses
    cp_priority_mip:            cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, mie_ones, mip_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100};
    }
    cp_priority_mie:            cross priv_mode_interrupts, mideleg_zeros, mstatus_mie_one, mip_all_ones, mie_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100};
    }
    `ifdef U_SUPPORTED
        cp_priority_mip_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mideleg_zeros, mie_ones, mip_pairs;
        cp_priority_mie_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mideleg_zeros, mip_all_ones, mie_pairs;
    `endif
    `ifdef S_SUPPORTED
        cp_priority_mideleg:        cross priv_mode_interrupts, mstatus_mie_one, mie_ones, mip_pairs_noh, mideleg_one_of_mip_pair {
            ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100};
        }
        cp_priority_mideleg_tsbi:   cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mie_ones, mip_pairs_noh, mideleg_one_of_mip_pair;
    `endif
    // cp_wfi_m and cp_wfi wait for the machine timer, so they need MTI
    `ifdef UDB_MTI_INTR_IMPL
        cp_wfi_m:               cross priv_mode_m, mstatus_mie, mstatus_tw, wfi, mideleg_zeros;
    `endif

    // WFI with TW = 0 is exercised in the most privileged mode below M that this config implements.
    // The mode is selected with a macro rather than an `ifdef inside the cross argument list: on a hart
    // with neither S nor U (cv32e20 implements Sm and no lower mode) the inline form leaves a cross with
    // no privilege axis at all, which still elaborates and fills from M-mode WFIs -- a silent duplicate
    // of cp_wfi_m reporting coverage for a mode the hart does not have. Dropping the coverpoint is right.
    // Without S, U-mode WFI only waits when WFI_U_MODE allows it; otherwise it traps at once.
    `ifdef UDB_MTI_INTR_IMPL
        `ifdef S_SUPPORTED
            `define SM_WFI_PRIV priv_mode_s
        `elsif U_SUPPORTED
            `ifdef UDB_WFI_U_MODE
                `define SM_WFI_PRIV priv_mode_u
            `endif
        `endif
    `endif
    `ifdef SM_WFI_PRIV
        cp_wfi:                 cross `SM_WFI_PRIV, mstatus_mie, mie_mtie_one, mstatus_tw_zero, wfi, mideleg_zeros;
    `endif
    // VS-mode WFI waits only with hstatus.VTW = 0; VU-mode WFI never waits.
    `ifdef H_SUPPORTED
        cp_wfi_vs:              cross priv_mode_vs, mstatus_mie, mie_mtie_one, mstatus_tw_zero, hstatus_vtw_zero, wfi, mideleg_zeros;
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
    // In VS-mode, TW = 1 raises illegal instruction whatever VTW is, and TW = 0 with VTW = 1 raises
    // virtual instruction. In VU-mode, TW = 0 raises virtual instruction whatever VTW is.
    `ifdef H_SUPPORTED
        cp_wfi_timeout_vs:                  cross priv_mode_vs, mstatus_mie, mie_mtie, mstatus_tw_one, hstatus_vtw, wfi;
        cp_wfi_timeout_vs_vtw_one:          cross priv_mode_vs, mstatus_mie, mie_mtie, mstatus_tw_zero, hstatus_vtw_one, wfi;
        cp_wfi_timeout_vu:                  cross priv_mode_vu, mstatus_mie, mie_mtie, mstatus_tw, hstatus_vtw, wfi;
        // Every TW and VTW in VS-mode: the WFI waits with TW = VTW = 0 (cp_wfi_vs) and times out otherwise
        cp_wfi_vs_tw_vtw:                   cross priv_mode_vs, mstatus_mie, mstatus_tw, hstatus_vtw, wfi;
    `endif

    `ifdef SSTC_SUPPORTED // need to modify this one to check more stuff
        cp_write_stip_sstc_csrrs: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrs, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
        cp_write_stip_sstc_csrrc: cross priv_mode_m, menvcfg_stce_one, stimecmp_max_min, csrrc, write_mip, rs1_STIP, mideleg_zeros, mie_zeros;
    `endif


endgroup

`ifdef SM_MPV
    `undef SM_MPV
`endif
`ifdef SM_WFI_PRIV
    `undef SM_WFI_PRIV
`endif

// Hypervisor interrupt CSRs read from M-mode and interrupt levels in VS and VU modes, from the hypervisor
// branch's InterruptsHSm suite.
`ifdef H_SUPPORTED

covergroup InterruptsSm_h_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    ecall : coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    // csrsi mstatus, MSTATUS_MIE
    set_mie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd8) {
        bins mstatus = {CSR_MSTATUS};
    }
    write_zero : coverpoint ins.current.rs1_val {
        bins zero = {0};
    }
    hvip_all : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[10], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[6], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[2]} {
        bins all = {3'b111};
    }

    // mideleg bits 10, 6 and 2 (and 12 if GEILEN > 0) are read-only 1
    mideleg : coverpoint ins.current.insn[31:20] {
        bins mideleg = {CSR_MIDELEG};
    }
    cp_mideleg: cross priv_mode_m, csrrw, mideleg, write_zero;

    // mie and mip hold the hie and hip bits
    mie : coverpoint ins.current.insn[31:20] {
        bins mie = {CSR_MIE};
    }
    mip : coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
    }
    hie_vs : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12:0] {
        bins vs = {13'h0444};
    }
    cp_mie: cross priv_mode_m, csrr, mie, hie_vs;
    cp_mip: cross priv_mode_m, csrr, mip, hvip_all;

    // hie.SGEIE is writable when GEILEN > 0 and implementation-defined otherwise
    `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
        hie_sgei_vs : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12:0] {
            bins sgei_vs = {13'h1444};
        }
        cp_mie_gilen: cross priv_mode_m, csrr, mie, hie_sgei_vs;
    `endif

    // VS-level interrupts pending and enabled in mie are not taken in M-mode
    mie_vs : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[12:0] {
        bins vs = {13'h0444};
    }
    hideleg_none : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[10], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[6], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2]} {
        bins none = {3'b000};
    }
    cp_nohint_m: cross priv_mode_m, set_mie, mie_vs, hvip_all, hideleg_none;

    // Enter VS or VU mode with one M-level or S-level interrupt pending and mideleg.SEI/STI/SSI = 0 or 1, sampled at
    // the T-SBI call: an ecall with a0 = TSBI_GOTO_VSMODE (4) or TSBI_GOTO_VUMODE (5) (CTP abstraction.adoc)
    tsbi_goto_vs : coverpoint ins.prev.x_wdata[10] {
        bins goto_vs = {4};
    }
    tsbi_goto_vu : coverpoint ins.prev.x_wdata[10] {
        bins goto_vu = {5};
    }
    mideleg_s : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[1]} {
        bins zeros = {3'b000};
        bins ones  = {3'b111};
    }
    mip_pending : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[11], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[7],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[1]} {
        bins mei = {6'b100000};
        bins sei = {6'b010000};
        bins mti = {6'b001000};
        bins sti = {6'b000100};
        bins msi = {6'b000010};
        bins ssi = {6'b000001};
    }
    mie_ones : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[11], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[7],
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[1]} {
        bins ones = {6'b111111};
    }
    mstatus_mie_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mstatus")[3] {
        bins zero = {0};
    }
    cp_mideleg_mip_vs: cross priv_mode_m, ecall, tsbi_goto_vs, mideleg_s, mip_pending, mie_ones, mstatus_mie_zero;
    cp_mideleg_mip_vu: cross priv_mode_m, ecall, tsbi_goto_vu, mideleg_s, mip_pending, mie_ones, mstatus_mie_zero;

    // Enter VS or VU mode with two or three of MSI (M-level), SSI (delegated to HS-mode by mideleg) and VSSI
    // (delegated to VS-mode by hideleg) pending and enabled, sampled at the T-SBI call
    mip_levels : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[1], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[2]} {
        `ifdef UDB_MSI_INTR_IMPL
            `ifdef UDB_SSI_INTR_IMPL
                bins m_hs    = {3'b110};
                bins m_hs_vs = {3'b111};
            `endif
            bins m_vs = {3'b101};
        `endif
        `ifdef UDB_SSI_INTR_IMPL
            bins hs_vs = {3'b011};
        `endif
    }
    mie_levels : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[1], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[2]} {
        bins all = {3'b111};
    }
    mideleg_ssi : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[1]} {
        bins hs = {2'b01};
    }
    hideleg_vssi : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2] {
        bins vs = {1};
    }
    vsstatus_sie_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] {
        bins one = {1};
    }
    cp_priority_levels_vs: cross priv_mode_m, ecall, tsbi_goto_vs, mip_levels, mie_levels, mideleg_ssi, hideleg_vssi,
                                 mstatus_mie_zero, vsstatus_sie_one;
    cp_priority_levels_vu: cross priv_mode_m, ecall, tsbi_goto_vu, mip_levels, mie_levels, mideleg_ssi, hideleg_vssi,
                                 mstatus_mie_zero;

    // Each interrupt taken into M-mode with mtinst nonzero
    mtinst_nonzero : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mtinst", "mtinst") != 0) {
        bins nonzero = {1};
    }
    int_enabled : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[13:0] {
        bins ssi = {14'h0002};
        bins msi = {14'h0008};
        bins sti = {14'h0020};
        bins mti = {14'h0080};
        bins sei = {14'h0200};
        bins mei = {14'h0800};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofi = {14'h2000};
        `endif
    }
    cp_mtinst: cross priv_mode_m, set_mie, mtinst_nonzero, int_enabled;
endgroup

`endif // H_SUPPORTED

function void interruptssm_sample(int hart, int issue, ins_t ins);
    InterruptsSm_cg.sample(ins);
    `ifdef H_SUPPORTED
        InterruptsSm_h_cg.sample(ins);
    `endif
endfunction
