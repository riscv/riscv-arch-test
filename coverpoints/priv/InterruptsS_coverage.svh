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
    // The mret back into the S handler also has MPP = S, but with SIE = 0, which is why the crosses
    // below that need SIE = 1 do not pick it up.
    tsbi_return: coverpoint (((ins.current.insn == MRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] == 2'b01)) ? 2'd1 :
                             ((ins.current.insn == SRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] == 1'b0)) ? 2'd2 : 2'd0) {
        bins S_mode = {2'd1};
        bins U_mode = {2'd2};
    }
    tsbi_return_u: coverpoint ((ins.current.insn == SRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] == 1'b0)) {
        bins U_mode = {1'b1};
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
            stimecmp_max_min: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "") {
                bins min = {'0};
                bins max = {'1};
            }
            stimecmp_min: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "") {
                bins min = {'0};
            }
        `else
            stimecmp_max_min: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmph", ""), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "")} {
                bins min = {'0};
                bins max = {'1};
            }
            stimecmp_min: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmph", ""), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stimecmp", "")} {
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
        ignore_bins u_sti_tsbi = binsof(priv_mode_interrupts.U_mode) && binsof(sip_walking.stip);
        `ifdef SSCOFPMF_SUPPORTED
            // U has no sip, so U-mode LCOFI is raised through T-SBI and recorded by cp_trigger_tsbi
            ignore_bins u_lcofi_tsbi = binsof(priv_mode_interrupts.U_mode) && binsof(sip_walking.lcofip);
        `endif
        `ifndef SSTC_SUPPORTED
            // Without Sstc, STI is raised only by an M-mode write to mip.STIP. With SIE = 0 it stays
            // pending in S and is recorded here; with SIE = 1 it is taken on the mret.
            ignore_bins s_sti_tsbi = binsof(priv_mode_interrupts.S_mode) && binsof(sip_walking.stip) &&
                                     binsof(sstatus_sie) intersect {1};
        `endif
    }
    // Every S-level interrupt has a T-SBI path: mip.STIP, mip.SSIP, mip.SEIP, and mip.LCOFIP are
    // written in M, and sip.SSIP in the S handler on behalf of U.
    cp_trigger_tsbi:            cross tsbi_return, sip_walking, sstatus_sie_on_return, mideleg_s_ones, sie_ones, stvec_both;

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
            ignore_bins u_min = binsof(priv_mode_interrupts.U_mode) && binsof(stimecmp_max_min.min);
        }
        cp_trigger_sti_sstc_tsbi: cross tsbi_return_u, menvcfg_stce_one, stimecmp_min, sstatus_sie_on_return, sie_ones, mideleg_s_ones, stvec_both;
    `endif

    // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_interrupts, mideleg_s_ones, sstatus_sie_one, walking_sie_one, sip_matches_sie_one {
        // STI and LCOFI are raised through T-SBI by RVTEST_SET_STIME_INT and RVTEST_SET_LCOFI_INT,
        // so with their enable set they are taken on the xret and covered by cp_enable_one_tsbi
        ignore_bins sti_tsbi = binsof(walking_sie_one.stie); // taken on the T-SBI xret: cp_enable_one_tsbi
        `ifdef SSCOFPMF_SUPPORTED
            ignore_bins lcofi_tsbi = binsof(walking_sie_one.lcofie); // taken on the T-SBI xret: cp_enable_one_tsbi
        `endif
    }
    // sstatus_sie_on_return_one also keeps out the U-mode path's mret into the S handler, which
    // runs with SIE = 0.
    cp_enable_one_tsbi:         cross tsbi_return, mideleg_s_ones, sstatus_sie_on_return_one, walking_sie_one, sip_matches_sie_one {
        // SSI and SEI come from the platform interrupt controller, written from the test mode itself
        ignore_bins platform = binsof(walking_sie_one.ssie) || binsof(walking_sie_one.seie);
    }
    // No _tsbi twin: cp_enable_zero checks that the disabled interrupt does not fire, so the test
    // instruction retires with it pending and is observed directly.
    cp_enable_zero:             cross priv_mode_interrupts, mideleg_s_ones, sstatus_sie_one, walking_sie_zero, sip_matches_sie_zero;

    // The pair is raised with sie = 0, then sie is written. S writes sie directly, so the higher
    // priority interrupt is taken on that csrw. U writes sie through T-SBI, so it is taken on the
    // sret out of the S handler and recorded by the _tsbi crosses.
    cp_priority_sip:            cross priv_mode_interrupts, sstatus_sie_one, mideleg_s_ones, sie_ones, sip_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts.U_mode); // U writes sie through T-SBI: cp_priority_sip_tsbi
    }
    cp_priority_sie:            cross priv_mode_interrupts, sstatus_sie_one, mideleg_s_ones, sip_all_ones, sie_pairs {
        ignore_bins tsbi = binsof(priv_mode_interrupts.U_mode); // U writes sie through T-SBI: cp_priority_sie_tsbi
    }
    cp_priority_sip_tsbi:       cross tsbi_return_u, mideleg_s_ones, sie_ones, sip_pairs;
    cp_priority_sie_tsbi:       cross tsbi_return_u, mideleg_s_ones, sip_all_ones, sie_pairs;

    // WFI wakes on the Sstc supervisor timer whether or not SIE is set. Not tested in U-mode: with
    // S-mode implemented, U-mode WFI traps after a bounded time (cp_wfi_timeout).
    `ifdef SSTC_SUPPORTED
        cp_wfi:                 cross priv_mode_s, sstatus_sie, sie_stie_one, mstatus_tw_zero, menvcfg_stce_one, mideleg_s_ones, wfi;
    `endif

    // mstatus.TW = 1 traps WFI in S and U. U-mode WFI also times out with TW = 0 because S exists.
    cp_wfi_timeout:             cross priv_mode_s_u, sstatus_sie, sie_stie, mstatus_tw_one, wfi;
    cp_wfi_timeout_tw_zero:     cross priv_mode_u, sstatus_sie, sie_stie, mstatus_tw_zero, wfi;

endgroup

`undef INTS_MASK
`undef INTS_NOH_MASK

function void interruptss_sample(int hart, int issue, ins_t ins);
    InterruptsS_cg.sample(ins);
endfunction
