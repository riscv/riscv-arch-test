///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu October 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSS

// InterruptsS boots to S-mode with mideleg delegating every S-level interrupt (set once at boot
// and never changed), so every interrupt here traps to S. With H, the coverpoints also include
// VS and VU modes and the VSEI, VSTI, and VSSI interrupts, as InterruptsSm does.

covergroup InterruptsS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    // Uses ins.prev instead of ins.current because RVVI updates CSRs after instruction retirement,
    // so ins.current shows post-trap state while ins.prev shows pre-trap state.
    // mip is the exception: the instruction that raises an interrupt records the new pending bit and
    // the trap's CSR updates together, so mip is read from ins.current to line up with ins.prev sstatus.
    // sstatus fields are read from sstatus. mstatus is read only for TW and MPP, which sstatus does not have.
    sstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0] {
        // autofill 0/1
    }
    sstatus_sie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0] {
        bins one = {1};
    }
    mstatus_tw_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
        bins zero = {0}; // WFI is permitted in S mode
    }
    mstatus_tw_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
        bins one = {1}; // WFI in S/U traps after the implementation-defined timeout
    }
    mstatus_tw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw")[0] {
        // autofill 0/1
    }
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

    // Privilege modes below M this config implements
    priv_mode_interrupts: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
        bins S_mode = {3'b001};
        bins U_mode = {3'b000};
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b101};
            bins VU_mode = {3'b100};
        `endif
    }

    // S-level interrupt bits: SEI, STI, SSI, and LCOFI with Sscofpmf
    `ifdef SSCOFPMF_SUPPORTED
        `define INTS_NOH_MASK 16'h2222
    `else
        `define INTS_NOH_MASK 16'h0222
    `endif

    // Interrupt bits this config supports below M: the S-level bits, plus VSEI, VSTI, and VSSI with H
    `ifdef H_SUPPORTED
        `define INTS_MASK (`INTS_NOH_MASK | 16'h0444)
    `else
        `define INTS_MASK `INTS_NOH_MASK
    `endif

    // mideleg delegates every S-level interrupt, as it does from boot. Bits outside INTS_NOH_MASK are
    // don't care: the tests never delegate M-level interrupts, and H hardwires the VS bits to 1.
    mideleg_s_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0] & `INTS_NOH_MASK) == `INTS_NOH_MASK) {
        bins ones = {1'b1};
    }

    // sie written all 1s: every S-level enable is set. The VS enables live in hie, which a write to
    // sie cannot reach, so they are left out; requiring them would make every cross below that
    // uses sie_ones unreachable on a config with H.
    sie_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_NOH_MASK) == `INTS_NOH_MASK) {
        bins ones = {1'b1};
    }

    sie_stie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "stie")[0] {
        // autofill 0/1
    }
    sie_stie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "stie")[0] {
        bins one = {1'b1};
    }

    // Exactly one interrupt in INTS_MASK enabled. M-level enables are not touched by writes to sie
    // or hie, so they are masked off.
    walking_sie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_MASK) {
        bins seie = {16'h0200};
        bins stie = {16'h0020};
        bins ssie = {16'h0002};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofie = {16'h2000};
        `endif
        `ifdef H_SUPPORTED
            bins vseie = {16'h0400};
            bins vstie = {16'h0040};
            bins vssie = {16'h0004};
        `endif
    }

    // Every S-level interrupt enabled except one: the complement of mie, masked to INTS_NOH_MASK,
    // is one-hot. The bin names the single interrupt left disabled. As in sie_ones, the VS enables
    // are in hie rather than sie, so they are masked off.
    walking_sie_zero: coverpoint ((~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0]) & `INTS_NOH_MASK) {
        bins seie = {16'h0200};
        bins stie = {16'h0020};
        bins ssie = {16'h0002};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofie = {16'h2000};
        `endif
    }

    // The single enabled interrupt in walking_sie_one is pending
    sip_matches_sie_one: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_MASK) != 16'h0) {
        bins pending = {1'b1};
    }

    // The single disabled interrupt in walking_sie_zero is pending
    sip_matches_sie_zero: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & ~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_NOH_MASK) != 16'h0) {
        bins pending = {1'b1};
    }

    // Exactly two interrupts in INTS_MASK enabled. One bin per pair: 3 for S, 6 for S+Sscofpmf,
    // 15 for S+H, and 21 for S+H+Sscofpmf.
    sie_pairs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_MASK) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0);
    }

    // With H a pair can be split between sie (S-level and LCOFI) and hie (VS-level). Only a T-SBI
    // write of mie enables both at once, so S-mode tests take split pairs on the mret, and S-mode's
    // direct crosses below cover the pairs held in one CSR. Without H every pair is in one CSR.
    `define ONE_CSR_PAIR(item) ((item & `INTS_NOH_MASK) == 0 || (item & 16'h0444) == 0)
    sie_pairs_one_csr: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_MASK) {
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0 && `ONE_CSR_PAIR(item));
    }
    `ifdef H_SUPPORTED
        sie_pairs_split: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTS_MASK) {
            bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0 && !`ONE_CSR_PAIR(item));
        }
    `endif

    // One interrupt in INTS_MASK pending at a time. M-level bits are masked off: the tests neither
    // raise nor depend on them.
    sip_walking: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTS_MASK) {
        bins seip = {16'h0200};
        bins stip = {16'h0020};
        bins ssip = {16'h0002};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofip = {16'h2000};
        `endif
        `ifdef H_SUPPORTED
            bins vseip = {16'h0400};
            bins vstip = {16'h0040};
            bins vssip = {16'h0004};
        `endif
    }

    // Exactly two interrupts in INTS_MASK pending at once. One bin per pair, counted as in sie_pairs.
    sip_pairs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTS_MASK) {
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0);
    }
    // The pairs held in one enable CSR and the split ones, as for sie_pairs_one_csr and sie_pairs_split
    sip_pairs_one_csr: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTS_MASK) {
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0 && `ONE_CSR_PAIR(item));
    }
    `ifdef H_SUPPORTED
        sip_pairs_split: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTS_MASK) {
            bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTS_MASK) == 0 && !`ONE_CSR_PAIR(item));
        }
    `endif

    // Every S-level interrupt pending at once. The VS pending bits are raised through hvip, which is
    // out of reach of the S-level macros, so they are masked off as in sie_ones.
    sip_all_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTS_NOH_MASK) == `INTS_NOH_MASK) {
        bins ones = {1'b1};
    }

    stvec_both: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stvec", "mode")[1:0] {
        `ifdef UDB_STVEC_MODES_0
            bins direct = {2'b00};
        `endif
        `ifdef UDB_STVEC_MODES_1
            bins vector = {2'b01};
        `endif
    }

    // Interrupts raised through T-SBI fire on the xret that returns to the test, before any test
    // instruction retires, so they are recorded on that xret:
    //   S-mode test: S ecall -> M handler -> mret to S (MPP = S). The interrupt is taken if SIE = 1.
    //   U-mode test: U ecall -> S handler (-> M handler -> mret back to the S handler) -> sret to
    //                U (SPP = U). The S handler runs with SIE = 0, so the interrupt waits for the sret.
    //   VS/VU-mode test: as for U, but the sret returns to VS or VU (hstatus.SPV = 1, SPP = S or U).
    // The mret back into the S handler also has MPP = S, but with SIE = 0, which is why the crosses
    // below that need SIE = 1 do not pick it up.
    `ifdef H_SUPPORTED
        `define S_SPV get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv")[0]
    `else
        `define S_SPV 1'b0
    `endif
    `define S_SRET_TO ((ins.current.insn == SRET) ? {1'b1, `S_SPV, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0]} : 3'b000)
    tsbi_return: coverpoint (((ins.current.insn == MRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] == 2'b01)) ? 3'b001 : `S_SRET_TO) {
        bins S_mode = {3'b001};
        bins U_mode = {3'b100}; // sret, SPV = 0, SPP = U
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b111}; // sret, SPV = 1, SPP = S
            bins VU_mode = {3'b110}; // sret, SPV = 1, SPP = U
        `endif
    }
    // The sret flavors alone: U, VS, and VU write sie through T-SBI, while S writes it directly
    // The mret flavor alone: an S-mode test's T-SBI call returning to it
    tsbi_return_mret: coverpoint ((ins.current.insn == MRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] == 2'b01)) {
        bins S_mode = {1'b1};
    }
    tsbi_return_sret: coverpoint `S_SRET_TO {
        bins U_mode = {3'b100};
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b111};
            bins VU_mode = {3'b110};
        `endif
    }
    // sstatus.SIE the test runs with after the xret: mret leaves SIE alone, sret restores it from SPIE
    sstatus_sie_on_return: coverpoint ((ins.current.insn == SRET) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] :
                                                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0]) {
        // autofill 0/1
    }
    sstatus_sie_on_return_one: coverpoint ((ins.current.insn == SRET) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] :
                                                                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0]) {
        bins one = {1};
    }

    // Building blocks for the software writes to mip.SSIP, mip.SEIP, and sip.SSIP
    csrrs: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csr_mip: coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
    }
    csr_sip: coverpoint ins.current.insn[31:20] {
        bins sip = {CSR_SIP};
    }
    // S-mode writes sip.SSIP with csrsi, which puts the value in insn[19:15] instead of rs1.
    // The T-SBI handler writes it with csrs on behalf of U-mode.
    csrrs_csrrsi: coverpoint ins.current.insn {
        wildcard bins csrrs_csrrsi = {CSRRS, CSRRSI};
    }
    rs1_ssip: coverpoint (ins.current.insn[14] ? XLEN'(ins.current.insn[19:15]) : ins.current.rs1_val) {
        bins ssip = {'h2};
    }
    rs1_seip: coverpoint ins.current.rs1_val {
        bins seip = {'h200};
    }

    // Building blocks for the Sstc crosses
    `ifdef SSTC_SUPPORTED
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
            stimecmp_min: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "stimecmp") {
                bins min = {'0};
            }
        `else
            stimecmp_max_min: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmph", "stimecmph"), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "stimecmp")} {
                bins min = {'0};
                bins max = {'1};
            }
            stimecmp_min: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmph", "stimecmph"), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "stimecmp")} {
                bins min = {'0};
            }
        `endif
    `endif

    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }

    // main coverpoints

    cp_trigger:                 cross priv_mode_interrupts, sip_walking, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both {
        // A delegated interrupt that the test mode cannot raise itself is raised through T-SBI and
        // taken on the xret back to the test, before any test instruction retires. cp_trigger_tsbi
        // records those. What S can raise itself: SSI and LCOFI through sip, STI through stimecmp
        // when Sstc is implemented, and SSI and SEI through the platform interrupt controller.
        // U has no sip or stimecmp access, so it reaches only the interrupt controller.
        // U cannot reach stimecmp or mip.STIP, so U-mode STI is raised through T-SBI (cp_trigger_tsbi)
        ignore_bins u_sti_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(sip_walking.stip);
        `ifdef SSCOFPMF_SUPPORTED
            // U has no sip, so U-mode LCOFI is raised through T-SBI and recorded by cp_trigger_tsbi
            ignore_bins u_lcofi_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(sip_walking.lcofip);
        `endif
        `ifdef H_SUPPORTED
            // VS and VU are like U: in VS, sip and stimecmp are vsip and vstimecmp. The VS-level
            // interrupts are raised through hvip, which only HS writes, so below HS they are raised
            // through T-SBI and taken on the sret.
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       (binsof(sip_walking.vseip) || binsof(sip_walking.vstip) || binsof(sip_walking.vssip));
        `endif
        `ifndef SSTC_SUPPORTED
            // Without Sstc, STI is raised only by an M-mode write to mip.STIP. With SIE = 0 it stays
            // pending in S and is recorded here; with SIE = 1 it is taken on the mret.
            ignore_bins s_sti_tsbi = binsof(priv_mode_interrupts.S_mode) && binsof(sip_walking.stip) &&
                                     binsof(sstatus_sie) intersect {1};
        `endif
    }
    // Every S-level interrupt has a T-SBI path: mip.STIP, mip.SSIP, mip.SEIP, and mip.LCOFIP are
    // written in M, and sip.SSIP in the S handler on behalf of U. The VS-level interrupts have one
    // only below HS: HS writes hvip itself.
    cp_trigger_tsbi:            cross tsbi_return, sip_walking, sstatus_sie_on_return, mideleg_s_ones, sie_ones, stvec_both {
        `ifdef H_SUPPORTED
            ignore_bins s_writes_hvip = binsof(tsbi_return.S_mode) &&
                                        (binsof(sip_walking.vseip) || binsof(sip_walking.vstip) || binsof(sip_walking.vssip));
        `endif
    }

    // mip is an M CSR, so S and U write it through T-SBI and the write is recorded in M.
    // S writes sip.SSIP directly; U writes it through T-SBI, which the S handler services itself.
    // Whether the write fires the interrupt in each mode is cp_trigger/cp_trigger_tsbi.
    cp_trigger_reg_mip_ssip:    cross csrrs, csr_mip, rs1_ssip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;
    cp_trigger_reg_mip_seip:    cross csrrs, csr_mip, rs1_seip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;
    cp_trigger_reg_sip_ssip:    cross csrrs_csrrsi, csr_sip, rs1_ssip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;

    `ifdef SSTC_SUPPORTED
        cp_trigger_sti_sstc:    cross priv_mode_interrupts, menvcfg_stce, sstatus_sie, sie_ones, mideleg_s_ones, stvec_both, stimecmp_max_min {
            // U-mode cannot write stimecmp. With STCE = 1 the S handler writes it on U's behalf and
            // STI is taken on the sret, so only cp_trigger_sti_sstc_tsbi records it.
            // With STCE = 0 the S handler cannot write stimecmp either (it is not accessible in S),
            // so the generator skips U-mode STCE = 0; InterruptsSm covers it from M-mode.
            ignore_bins u_min = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(stimecmp_max_min.min);
        }
        cp_trigger_sti_sstc_tsbi: cross tsbi_return_sret, menvcfg_stce_one, stimecmp_min, sstatus_sie_on_return, sie_ones, mideleg_s_ones, stvec_both;
    `endif

    // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_interrupts, mideleg_s_ones, sstatus_sie_one, walking_sie_one, sip_matches_sie_one {
        // STI and LCOFI are raised through T-SBI by RVTEST_SET_STIME_INT and RVTEST_SET_LCOFI_INT,
        // so with their enable set they are taken on the xret and covered by cp_enable_one_tsbi
        ignore_bins sti_tsbi = binsof(walking_sie_one.stie); // taken on the T-SBI xret: cp_enable_one_tsbi
        `ifdef SSCOFPMF_SUPPORTED
            ignore_bins lcofi_tsbi = binsof(walking_sie_one.lcofie); // taken on the T-SBI xret: cp_enable_one_tsbi
        `endif
        `ifdef H_SUPPORTED
            // Below HS the VS-level interrupts are raised through T-SBI (hvip): cp_enable_one_tsbi
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       (binsof(walking_sie_one.vseie) || binsof(walking_sie_one.vstie) || binsof(walking_sie_one.vssie));
        `endif
    }
    // sstatus_sie_on_return_one also keeps out the U-mode path's mret into the S handler, which
    // runs with SIE = 0.
    cp_enable_one_tsbi:         cross tsbi_return, mideleg_s_ones, sstatus_sie_on_return_one, walking_sie_one, sip_matches_sie_one {
        // SSI and SEI come from the platform interrupt controller, written from the test mode itself
        ignore_bins platform = binsof(walking_sie_one.ssie) || binsof(walking_sie_one.seie);
        `ifdef H_SUPPORTED
            // S writes hvip directly, so its VS-level interrupts are taken in S (cp_enable_one)
            ignore_bins s_writes_hvip = binsof(tsbi_return.S_mode) &&
                                        (binsof(walking_sie_one.vseie) || binsof(walking_sie_one.vstie) || binsof(walking_sie_one.vssie));
        `endif
    }
    // No _tsbi twin: cp_enable_zero checks that the disabled interrupt does not fire, so the test
    // instruction retires with it pending and is observed directly.
    cp_enable_zero:             cross priv_mode_interrupts, mideleg_s_ones, sstatus_sie_one, walking_sie_zero, sip_matches_sie_zero;

    // The pair is raised with sie = 0, then sie is written. S writes sie directly, so the higher
    // priority interrupt is taken on that csrw. U writes sie through T-SBI, so it is taken on the
    // sret out of the S handler and recorded by the _tsbi crosses.
    cp_priority_sip:            cross priv_mode_interrupts, sstatus_sie_one, mideleg_s_ones, sie_ones, sip_pairs_one_csr {
        // U, VS, and VU write sie through T-SBI: cp_priority_sip_tsbi
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100};
    }
    cp_priority_sie:            cross priv_mode_interrupts, sstatus_sie_one, mideleg_s_ones, sip_all_ones, sie_pairs_one_csr {
        // U, VS, and VU write sie through T-SBI: cp_priority_sie_tsbi
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100};
    }
    cp_priority_sip_tsbi:       cross tsbi_return_sret, mideleg_s_ones, sie_ones, sip_pairs;
    cp_priority_sie_tsbi:       cross tsbi_return_sret, mideleg_s_ones, sip_all_ones, sie_pairs;
    // S enables a split pair by a T-SBI write of mie, so it is taken on the mret. SIE = 1 keeps out
    // the mret back into the S handler on the U, VS, and VU paths, which runs with SIE = 0.
    `ifdef H_SUPPORTED
        cp_priority_sip_split_tsbi: cross tsbi_return_mret, sstatus_sie_on_return_one, mideleg_s_ones, sie_ones, sip_pairs_split;
        cp_priority_sie_split_tsbi: cross tsbi_return_mret, sstatus_sie_on_return_one, mideleg_s_ones, sip_all_ones, sie_pairs_split;
    `endif

    // WFI wakes on the Sstc supervisor timer whether or not SIE is set. Not tested in U-mode: with
    // S-mode implemented, U-mode WFI traps after a bounded time (cp_wfi_timeout). VS-mode WFI waits
    // only with hstatus.VTW = 0; VU-mode WFI never waits.
    `ifdef SSTC_SUPPORTED
        cp_wfi:                 cross priv_mode_s, sstatus_sie, sie_stie_one, mstatus_tw_zero, menvcfg_stce_one, mideleg_s_ones, wfi;
        `ifdef H_SUPPORTED
            cp_wfi_vs:          cross priv_mode_vs, sstatus_sie, sie_stie_one, mstatus_tw_zero, hstatus_vtw_zero, menvcfg_stce_one, mideleg_s_ones, wfi;
        `endif
    `endif

    // mstatus.TW = 1 traps WFI in S and U. U-mode WFI also times out with TW = 0 because S exists.
    cp_wfi_timeout:             cross priv_mode_s_u, sstatus_sie, sie_stie, mstatus_tw_one, wfi;
    cp_wfi_timeout_tw_zero:     cross priv_mode_u, sstatus_sie, sie_stie, mstatus_tw_zero, wfi;
    // In VS-mode, TW = 1 raises illegal instruction whatever VTW is, and TW = 0 with VTW = 1 raises
    // virtual instruction. In VU-mode, TW = 0 raises virtual instruction whatever VTW is.
    `ifdef H_SUPPORTED
        cp_wfi_timeout_vs:          cross priv_mode_vs, sstatus_sie, sie_stie, mstatus_tw_one, hstatus_vtw, wfi;
        cp_wfi_timeout_vs_vtw_one:  cross priv_mode_vs, sstatus_sie, sie_stie, mstatus_tw_zero, hstatus_vtw_one, wfi;
        cp_wfi_timeout_vu:          cross priv_mode_vu, sstatus_sie, sie_stie, mstatus_tw, hstatus_vtw, wfi;
        // Every TW and VTW in VS-mode: the WFI waits with TW = VTW = 0 (cp_wfi_vs, which needs Sstc) and times
        // out otherwise
        `ifdef SSTC_SUPPORTED
            cp_wfi_vs_tw_vtw:       cross priv_mode_vs, sstatus_sie, mstatus_tw, hstatus_vtw, wfi;
        `endif
    `endif

endgroup

`undef INTS_MASK
`undef INTS_NOH_MASK
`undef S_SPV
`undef S_SRET_TO
`undef ONE_CSR_PAIR

// Hypervisor interrupt CSRs and VS-level interrupts in VS, VU and U modes, from the hypervisor branch's
// InterruptsH and InterruptsHGei suites.
`ifdef H_SUPPORTED

// VS-level interrupt bits {VSEI, VSTI, VSSI} of an hvip, hip, hie or hideleg value
`define INTERRUPTSH_VS(v) {v[10], v[6], v[2]}

// Every coverpoint but the WFI ones is sampled in HS-mode, the guest ones at the T-SBI call that enters the guest
covergroup InterruptsS_h_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // csrsi sstatus, SSTATUS_SIE
    set_sie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd2) {
        bins sstatus = {CSR_SSTATUS};
    }
    hvip : coverpoint ins.current.insn[31:20] {
        bins hvip = {CSR_HVIP};
    }
    hip : coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hie : coverpoint ins.current.insn[31:20] {
        bins hie = {CSR_HIE};
    }
    hip_vsip : coverpoint ins.current.insn[31:20] {
        bins hip  = {CSR_HIP};
        bins vsip = {CSR_VSIP};
    }
    hie_vsie : coverpoint ins.current.insn[31:20] {
        bins hie  = {CSR_HIE};
        bins vsie = {CSR_VSIE};
    }
    vsie : coverpoint ins.current.insn[31:20] {
        bins vsie = {CSR_VSIE};
    }
    vsip : coverpoint ins.current.insn[31:20] {
        bins vsip = {CSR_VSIP};
    }
    hideleg : coverpoint ins.current.insn[31:20] {
        bins hideleg = {CSR_HIDELEG};
    }

    // Setup CSRs sampled before the instruction, with one bin per combination of the VS-level bits
    hideleg_vs  : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg"));
    hvip_vs     : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip"));
    hie_vs      : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie"));
    hideleg_all : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")) { bins all = {3'b111}; }
    hvip_all    : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip"))    { bins all = {3'b111}; }
    hie_all     : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie"))     { bins all = {3'b111}; }
    hideleg_none : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")) {
        bins none = {3'b000};
    }
    sstatus_sie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sstatus")[1];
    sstatus_sie_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sstatus")[1] {
        bins one = {1};
    }
    hvip_write : coverpoint `INTERRUPTSH_VS(ins.current.rs1_val);
    ones_16 : coverpoint ins.current.rs1_val {
        bins ones = {16'hFFFF};
    }

    // Raise each VS-level interrupt through hvip with sstatus.SIE, hideleg and hie = 0/1
    hideleg_vseip : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[10];
    hideleg_vstip : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[6];
    hideleg_vssip : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2];
    hie_vseie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[10];
    hie_vstie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[6];
    hie_vssie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[2];
    set_vseip : coverpoint ins.current.rs1_val {
        bins vseip = {'h400};
    }
    set_vstip : coverpoint ins.current.rs1_val {
        bins vstip = {'h40};
    }
    set_vssip : coverpoint ins.current.rs1_val {
        bins vssip = {'h4};
    }
    cp_trigger_vsei: cross priv_mode_hs, csrrs, hvip, set_vseip, sstatus_sie, hideleg_vseip, hie_vseie;
    cp_trigger_vsti: cross priv_mode_hs, csrrs, hvip, set_vstip, sstatus_sie, hideleg_vstip, hie_vstie;
    cp_trigger_vssi: cross priv_mode_hs, csrrs, hvip, set_vssip, sstatus_sie, hideleg_vssip, hie_vssie;

    // Write hip = 0xFFFF and 0: only VSSIP is writable
    hip_write : coverpoint ins.current.rs1_val {
        bins ones  = {16'hFFFF};
        bins zeros = {0};
    }
    cp_hip_write: cross priv_mode_hs, csrrw, hip, hip_write;

    // Each combination of pending VS-level interrupts with each combination of hie or hideleg
    cp_priority_en_vsi:    cross priv_mode_hs, csrrw, hvip, hvip_write, hie_vs, hideleg_none, sstatus_sie_one;
    cp_priority_deleg_vsi: cross priv_mode_hs, csrrw, hvip, hvip_write, hideleg_vs, hie_all, sstatus_sie_one;

    // A pending S-level interrupt, or none, with every VS-level interrupt pending and enabled
    sie_ones : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[1]} {
        bins ones = {3'b111};
    }
    sip_s : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[1]} {
        bins sei  = {3'b100};
        bins sti  = {3'b010};
        bins ssi  = {3'b001};
        bins none = {3'b000};
    }
    cp_priority_s: cross priv_mode_hs, set_sie, sip_s, sie_ones, hvip_all, hie_all, hideleg_none;

    // A pending LCOFI with every VS-level interrupt pending and enabled: LCOFI is taken last
    `ifdef SSCOFPMF_SUPPORTED
        sip_lcofi : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[13], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[5],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[1]} {
            bins lcofi = {4'b1000};
        }
        sie_lcofi : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[13], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[5],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[1]} {
            bins lcofi = {4'b1000};
        }
        cp_priority_lcofi: cross priv_mode_hs, set_sie, sip_lcofi, sie_lcofi, hvip_all, hie_all, hideleg_none;
    `endif

    // hie, hip, vsie and vsip through hideleg
    mie_vs_all : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")) {
        bins all = {3'b111};
    }
    cp_hie:           cross priv_mode_hs, csrr, hie_vsie, hideleg_vs, mie_vs_all;
    cp_hip:           cross priv_mode_hs, csrr, hip_vsip, hideleg_vs, hvip_all;
    cp_hideleg:       cross priv_mode_hs, csrrw, hideleg, ones_16;
    cp_vsie:          cross priv_mode_hs, csrr, vsie, hideleg_vs, hie_vs;
    cp_vsip:          cross priv_mode_hs, csrr, vsip, hideleg_vs, hvip_vs;
    cp_vsie_from_hie: cross priv_mode_hs, csrrw, vsie, ones_16, hideleg_vs;

    // hie.SGEIE is an alias of mie.SGEIE, which is writable when GEILEN > 0 and implementation-defined otherwise
    `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
        mie_1444 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[12:0] {
            bins sgei_vs = {13'h1444};
        }
        cp_hie_gilen: cross priv_mode_hs, csrr, hie, mie_1444;
    `endif

    // Each interrupt taken into HS-mode with htinst nonzero
    htinst_nonzero : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htinst", "htinst") != 0) {
        bins nonzero = {1};
    }
    int_enabled : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[13:0] | get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[13:0]) {
        bins ssi  = {14'h0002};
        bins vssi = {14'h0004};
        bins sti  = {14'h0020};
        bins vsti = {14'h0040};
        bins sei  = {14'h0200};
        bins vsei = {14'h0400};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofi = {14'h2000};
        `endif
    }
    cp_htinst: cross priv_mode_hs, set_sie, htinst_nonzero, int_enabled;

    // The T-SBI calls that enter U, VS and VU mode: an ecall with a0 = TSBI_GOTO_UMODE (3), TSBI_GOTO_VSMODE (4)
    // or TSBI_GOTO_VUMODE (5), the function IDs of the T-SBI interface (CTP abstraction.adoc)
    ecall : coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    tsbi_goto_u : coverpoint ins.prev.x_wdata[10] {
        bins goto_u = {3};
    }
    tsbi_goto_vs : coverpoint ins.prev.x_wdata[10] {
        bins goto_vs = {4};
    }
    tsbi_goto_vu : coverpoint ins.prev.x_wdata[10] {
        bins goto_vu = {5};
    }
    vsstatus_sie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1];
    vsstatus_sie_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] {
        bins one = {1};
    }

    // Enter VS or VU mode with each combination of two of hideleg, hvip and hie, the third being 0x444
    cp_hideleg_hip_vs: cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_vs, hvip_vs, hie_all, vsstatus_sie_one;
    cp_hideleg_hie_vs: cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_vs, hvip_all, hie_vs, vsstatus_sie_one;
    cp_hip_hie_vs:     cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_all, hvip_vs, hie_vs, vsstatus_sie_one;
    cp_sie_vs:         cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_all, hvip_all, hie_all, vsstatus_sie;
    cp_hideleg_hip_vu: cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_vs, hvip_vs, hie_all;
    cp_hideleg_hie_vu: cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_vs, hvip_all, hie_vs;
    cp_hip_hie_vu:     cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_all, hvip_vs, hie_vs;

    // Enter VS-mode with a vectored vstvec and one delegated VS-level interrupt pending
    `ifdef UDB_VSTVEC_MODES_1
        vstvec_vectored : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstvec", "vstvec")[1:0] {
            bins vect = {1};
        }
        hvip_one : coverpoint `INTERRUPTSH_VS(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")) {
            bins vsei = {3'b100};
            bins vsti = {3'b010};
            bins vssi = {3'b001};
        }
        cp_vsint_vectored: cross priv_mode_hs, ecall, tsbi_goto_vs, vstvec_vectored, hideleg_all, hvip_one,
                                 vsstatus_sie_one;
    `endif

    // Enter U-mode with the VS-level interrupts pending, enabled and delegated: none is taken
    cp_vsint_disabled_u: cross priv_mode_hs, ecall, tsbi_goto_u, hideleg_all, hvip_all, hie_all;
endgroup

`undef INTERRUPTSH_VS

// Guest external interrupts exist when H is implemented with GEILEN > 0 (RVTEST_SGEI_INTR_IMPL, derived_config.svh);
// the DUT then provides RVMODEL_SET/CLR_GUEST_EXT_INT to raise them
`ifdef RVTEST_SGEI_INTR_IMPL

// Read mip from M-mode with a guest external interrupt pending
covergroup InterruptsS_gei_m_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    mip : coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
    }
    sgei_pending : coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")) != 0) {
        bins pending = {1};
    }
    cp_mip_gilen: cross priv_mode_m, csrr, mip, sgei_pending;
endgroup

// hgeip, hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority, sampled in HS-mode
covergroup InterruptsS_gei_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // csrsi sstatus, SSTATUS_SIE
    set_sie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd2) {
        bins sstatus = {CSR_SSTATUS};
    }
    hip : coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hie : coverpoint ins.current.insn[31:20] {
        bins hie = {CSR_HIE};
    }
    sstatus_sie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sstatus")[1];
    hvip_all : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[10], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[6], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[2]} {
        bins all = {3'b111};
    }
    hideleg_none : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[10], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[6], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2]} {
        bins none = {3'b000};
    }
    sie_ones : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "sie")[1]} {
        bins ones = {3'b111};
    }

    sgei_pending : coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")) != 0) {
        bins pending = {1};
    }
    hie_write_sgeie : coverpoint ins.current.rs1_val[12];
    hie_1444 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12:0] {
        bins sgei_vs = {13'h1444};
    }
    sip_s_pending : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[1]} {
        bins sei  = {3'b100};
        bins sti  = {3'b010};
        bins ssi  = {3'b001};
    }
    sip_s_none : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[1]} {
        bins none = {3'b000};
    }
    cp_trigger_sgei:    cross priv_mode_hs, csrrw, hie, hie_write_sgeie, sstatus_sie, sgei_pending;
    cp_priority_sgei:   cross priv_mode_hs, set_sie, sgei_pending, hie_1444, sie_ones, sip_s_none, hvip_all,
                              hideleg_none;
    cp_priority_sgei_s: cross priv_mode_hs, set_sie, sgei_pending, hie_1444, sie_ones, sip_s_pending, hvip_all,
                              hideleg_none;

    // Each guest external interrupt i enabled alone, with hgeip = 0, bit i or every implemented bit
    hgeie_bit : coverpoint $clog2(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")) iff ($onehot(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie"))) {
        bins b[] = {[1:`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
    }
    // With GEILEN = 1, every implemented bit is bit i, so "all" is the same case as "i"
    hgeip_vs_hgeie : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == 0 ? 0 : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie") ? 1 : 2) {
        bins none = {0};
        bins i    = {1};
        `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_1
            bins all = {2};
        `endif
    }
    cp_hgeie: cross priv_mode_hs, csrr, hip, hgeie_bit, hgeip_vs_hgeie;

    // hstatus.VGEIN = i selects hgeip bit i into hip.VSEIP, whatever hgeie holds
    vgein : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12] {
        bins b[] = {[1:`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
    }
    vgein_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12] {
        bins zero = {0};
    }
    hgeip_vs_vgein : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == 0 ? 0 :
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]) ? 1 :
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip")[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]] ? 3 : 2) {
        bins none   = {0};
        bins i      = {1};
        // With GEILEN = 1 there is no implemented bit other than i, so "others" is the same case as "none"
        `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_1
            bins others = {2};
        `endif
    }
    hgeie_vgein : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]];
    hgeip_nonzero : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") != 0) {
        bins nonzero = {1};
    }
    cp_trigger_vsei_hgeip: cross priv_mode_hs, csrr, hip, vgein, hgeip_vs_vgein, hgeie_vgein;
    cp_hgeip0:             cross priv_mode_hs, csrr, hip, vgein_zero, hgeip_nonzero, sgei_pending;
endgroup

`endif // RVTEST_SGEI_INTR_IMPL

`endif // H_SUPPORTED

function void interruptss_sample(int hart, int issue, ins_t ins);
    InterruptsS_cg.sample(ins);
    `ifdef H_SUPPORTED
        InterruptsS_h_cg.sample(ins);
        `ifdef RVTEST_SGEI_INTR_IMPL
            InterruptsS_gei_m_cg.sample(ins);
            InterruptsS_gei_cg.sample(ins);
        `endif
    `endif
endfunction
