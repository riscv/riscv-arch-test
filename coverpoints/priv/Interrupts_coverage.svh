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

`define COVER_INTERRUPTS

// The Interrupts suite has one covergroup per group of test files:
//   Interrupts_cg                 boots to S-mode (Interrupts_<topic>_<mode> files)
//   Interrupts_Sm_cg              boots to M-mode (Interrupts_Sm_*)
//   Interrupts_Sgei_cg            guest external interrupts, boots to S-mode (Interrupts_Sgei_*)
//   Interrupts_SgeiSm_cg          guest external interrupts with mideleg = 0, boots to M-mode
//   Interrupts_Shlcofideleg_cg    LCOFI delegated to VS-mode, boots to S-mode
//   Interrupts_SmShlcofideleg_cg  LCOFI with mideleg[13] = 0, boots to M-mode

`ifdef S_SUPPORTED

// Interrupts_cg boots to S-mode with mideleg delegating every S-level interrupt (set once at boot
// and never changed), so every interrupt here traps to S. With H, the coverpoints also include
// VS and VU modes and the VSEI, VSTI, and VSSI interrupts, as Interrupts_Sm_cg does.

covergroup Interrupts_cg with function sample(ins_t ins);
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

    // mideleg delegates every S-level interrupt, as it does from boot. Bits outside INTR_S_LEVEL are
    // don't care: the tests never delegate M-level interrupts, and H hardwires the VS bits to 1.
    mideleg_s_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0] & `INTR_S_LEVEL) == `INTR_S_LEVEL) {
        bins ones = {1'b1};
    }

    // sie written all 1s: every S-level enable is set. The VS enables live in hie, which a write to
    // sie cannot reach, so they are left out; requiring them would make every cross below that
    // uses sie_ones unreachable on a config with H.
    sie_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_S_LEVEL) == `INTR_S_LEVEL) {
        bins ones = {1'b1};
    }

    sie_stie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "stie")[0] {
        bins zero = {1'b0};
        `ifdef UDB_STI_INTR_IMPL
            bins one = {1'b1}; // STIE is read-only zero without STI
        `endif
    }
    `ifdef UDB_STI_INTR_IMPL
        sie_stie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "stie")[0] {
            bins one = {1'b1};
        }
    `endif

    // Exactly one interrupt in INTR_BELOW_M enabled. M-level enables are not touched by writes to sie
    // or hie, so they are masked off.
    walking_sie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) {
        `ifdef UDB_SEI_INTR_IMPL
            bins seie = {16'h0200};
        `endif
        `ifdef UDB_STI_INTR_IMPL
            bins stie = {16'h0020};
        `endif
        `ifdef UDB_SSI_INTR_IMPL
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

    // Every interrupt in INTR_BELOW_M enabled except one: the complement of mie, masked to INTR_BELOW_M,
    // is one-hot. The bin names the single interrupt left disabled. The tests write the same value to
    // sie and hie, so with H the VS enables are set too unless one of them is the one left out.
    walking_sie_zero: coverpoint ((~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0]) & `INTR_BELOW_M) {
        `ifdef UDB_SEI_INTR_IMPL
            bins seie = {16'h0200};
        `endif
        `ifdef UDB_STI_INTR_IMPL
            bins stie = {16'h0020};
        `endif
        `ifdef UDB_SSI_INTR_IMPL
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

    // The single enabled interrupt in walking_sie_one is pending
    sip_matches_sie_one: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) != 16'h0) {
        bins pending = {1'b1};
    }

    // The single disabled interrupt in walking_sie_zero is pending
    sip_matches_sie_zero: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & ~get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) != 16'h0) {
        bins pending = {1'b1};
    }

    // Exactly two interrupts in INTR_BELOW_M enabled. One bin per pair: 3 for S, 6 for S+Sscofpmf,
    // 15 for S+H, and 21 for S+H+Sscofpmf.
    sie_pairs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) {
        // The second term drops pairs naming a bit this config does not implement, which would
        // otherwise be declared as bins that can never be hit.
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_BELOW_M) == 0);
    }

    // With H a pair can be split between sie (S-level and LCOFI) and hie (VS-level). Only a T-SBI
    // write of mie enables both at once, so S-mode tests take split pairs on the mret, and S-mode's
    // direct crosses below cover the pairs held in one CSR. Without H every pair is in one CSR.
    `define ONE_CSR_PAIR(item) ((item & `INTR_S_LEVEL) == 0 || (item & 16'h0444) == 0)
    sie_pairs_one_csr: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) {
        bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_BELOW_M) == 0 && `ONE_CSR_PAIR(item));
    }
    `ifdef H_SUPPORTED
        sie_pairs_split: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0] & `INTR_BELOW_M) {
            bins pairs[] = {[0:$]} with ($countones(item) == 2 && (item & ~`INTR_BELOW_M) == 0 && !`ONE_CSR_PAIR(item));
        }
    `endif

    // One interrupt in INTR_BELOW_M pending at a time. M-level bits are masked off: the tests neither
    // raise nor depend on them.
    sip_walking: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_BELOW_M) {
        `ifdef UDB_SEI_INTR_IMPL
            bins seip = {16'h0200};
        `endif
        `ifdef UDB_STI_INTR_IMPL
            bins stip = {16'h0020};
        `endif
        `ifdef UDB_SSI_INTR_IMPL
            bins ssip = {16'h0002};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofip = {16'h2000};
        `endif
        `ifdef H_SUPPORTED
            bins vseip = {16'h0400};
            bins vstip = {16'h0040};
            bins vssip = {16'h0004};
        `endif
    }

    // Exactly two interrupts in INTR_BELOW_M pending at once. With H, each VS-level member of the pair
    // that hideleg delegates to VS-mode is also marked one bit up, in the M-level position next to it
    // (VSEI 10 -> 11, VSTI 6 -> 7, VSSI 2 -> 3), which INTR_BELOW_M never uses. So each pair has one
    // bin per subset of its VS-level members that is delegated: 3 for S, 6 for S+Sscofpmf, 36 for S+H
    // and 42 for S+H+Sscofpmf.
    `ifdef H_SUPPORTED
        `define S_PAIR(mip, hideleg) ((mip & `INTR_BELOW_M) | ((mip & hideleg & 16'h0444) << 1))
        `define S_PAIR_OK(item) ($countones(item & `INTR_BELOW_M) == 2 && (item & ~(`INTR_BELOW_M | 16'h0888)) == 0 && \
                                 ((item >> 1) & 16'h0444 & ~item) == 0)
    `else
        `define S_PAIR(mip, hideleg) (mip & `INTR_BELOW_M)
        `define S_PAIR_OK(item) ($countones(item) == 2 && (item & ~`INTR_BELOW_M) == 0)
    `endif
    `define S_PAIR_NOW `S_PAIR(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hideleg", "hideleg")[15:0])
    sip_pairs: coverpoint `S_PAIR_NOW {
        bins pairs[] = {[0:$]} with (`S_PAIR_OK(item));
    }
    // The pairs held in one enable CSR and the split ones, as for sie_pairs_one_csr and sie_pairs_split
    sip_pairs_one_csr: coverpoint `S_PAIR_NOW {
        bins pairs[] = {[0:$]} with (`S_PAIR_OK(item) && `ONE_CSR_PAIR((item & `INTR_BELOW_M)));
    }
    `ifdef H_SUPPORTED
        sip_pairs_split: coverpoint `S_PAIR_NOW {
            bins pairs[] = {[0:$]} with (`S_PAIR_OK(item) && !`ONE_CSR_PAIR((item & `INTR_BELOW_M)));
        }
    `endif

    // Every S-level interrupt pending at once. The VS pending bits are raised through hvip, which is
    // out of reach of the S-level macros, so they are masked off as in sie_ones.
    sip_all_ones: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_S_LEVEL) == `INTR_S_LEVEL) {
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

    // The trigger crosses follow the interrupt to the level that takes it. With H, a pending VS-level
    // interrupt that hideleg delegates goes to VS-mode: sip_walking_deleg puts it in a _vs bin, and the
    // global enable and trap vector of the cross are then vsstatus.SIE and vstvec.MODE instead of
    // sstatus.SIE and stvec.MODE. HS-mode and U-mode never take it; VS-mode takes it when
    // vsstatus.SIE = 1 and VU-mode always does.
    `ifdef H_SUPPORTED
        `define S_TO_VS ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & \
                          get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hideleg", "hideleg")[15:0] & 16'h0444) != 16'h0)
    `else
        `define S_TO_VS 1'b0
    `endif
    sip_walking_deleg: coverpoint {`S_TO_VS, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & `INTR_BELOW_M} {
        `ifdef UDB_SEI_INTR_IMPL
            bins seip = {17'h00200};
        `endif
        `ifdef UDB_STI_INTR_IMPL
            bins stip = {17'h00020};
        `endif
        `ifdef UDB_SSI_INTR_IMPL
            bins ssip = {17'h00002};
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofip = {17'h02000};
        `endif
        `ifdef H_SUPPORTED
            bins vseip = {17'h00400};
            bins vstip = {17'h00040};
            bins vssip = {17'h00004};
            bins vseip_vs = {17'h10400};
            bins vstip_vs = {17'h10040};
            bins vssip_vs = {17'h10004};
        `endif
    }
    trigger_sie: coverpoint (`S_TO_VS ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] :
                                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0]) {
        // autofill 0/1
    }
    trigger_tvec: coverpoint (`S_TO_VS ? get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstvec", "vstvec")[1:0] :
                                          get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stvec", "mode")[1:0]) {
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
    // As sstatus_sie_on_return, or vsstatus.SIE for an interrupt delegated to VS-mode, which the xret leaves alone
    trigger_sie_on_return: coverpoint (`S_TO_VS ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] :
                                       (ins.current.insn == SRET) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] :
                                                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")[0]) {
        // autofill 0/1
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

    cp_trigger:                 cross priv_mode_interrupts, sip_walking_deleg, trigger_sie, mideleg_s_ones, sie_ones, trigger_tvec {
        // A delegated interrupt that the test mode cannot raise itself is raised through T-SBI and
        // taken on the xret back to the test, before any test instruction retires. cp_trigger_tsbi
        // records those. What S can raise itself: SSI and LCOFI through sip, STI through stimecmp
        // when Sstc is implemented, and SSI and SEI through the platform interrupt controller.
        // U has no sip or stimecmp access, so it reaches only the interrupt controller.
        // U cannot reach stimecmp or mip.STIP, so U-mode STI is raised through T-SBI (cp_trigger_tsbi)
        `ifdef UDB_STI_INTR_IMPL
            ignore_bins u_sti_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(sip_walking_deleg.stip);
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            // U has no sip, so U-mode LCOFI is raised through T-SBI and recorded by cp_trigger_tsbi
            ignore_bins u_lcofi_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(sip_walking_deleg.lcofip);
        `endif
        `ifdef H_SUPPORTED
            // VS and VU are like U: in VS, sip and stimecmp are vsip and vstimecmp. The VS-level
            // interrupts are raised through hvip, which only HS writes, so below HS they are raised
            // through T-SBI and taken on the sret.
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       (binsof(sip_walking_deleg.vseip) || binsof(sip_walking_deleg.vstip) || binsof(sip_walking_deleg.vssip) ||
                                        binsof(sip_walking_deleg.vseip_vs) || binsof(sip_walking_deleg.vstip_vs) || binsof(sip_walking_deleg.vssip_vs));
        `endif
        `ifndef SSTC_SUPPORTED
            `ifdef UDB_STI_INTR_IMPL
                // Without Sstc, STI is raised only by an M-mode write to mip.STIP. With SIE = 0 it stays
                // pending in S and is recorded here; with SIE = 1 it is taken on the mret.
                ignore_bins s_sti_tsbi = binsof(priv_mode_interrupts.S_mode) && binsof(sip_walking_deleg.stip) &&
                                         binsof(trigger_sie) intersect {1};
            `endif
        `endif
    }
    // Every S-level interrupt has a T-SBI path: mip.STIP, mip.SSIP, mip.SEIP, and mip.LCOFIP are
    // written in M, and sip.SSIP in the S handler on behalf of U. The VS-level interrupts have one
    // only below HS: HS writes hvip itself.
    cp_trigger_tsbi:            cross tsbi_return, sip_walking_deleg, trigger_sie_on_return, mideleg_s_ones, sie_ones, trigger_tvec {
        `ifdef H_SUPPORTED
            ignore_bins s_writes_hvip = binsof(tsbi_return.S_mode) &&
                                        (binsof(sip_walking_deleg.vseip) || binsof(sip_walking_deleg.vstip) || binsof(sip_walking_deleg.vssip) ||
                                         binsof(sip_walking_deleg.vseip_vs) || binsof(sip_walking_deleg.vstip_vs) || binsof(sip_walking_deleg.vssip_vs));
        `endif
    }
    // Every interrupt taken into HS-mode from HS-mode writes htinst = 0. The trigger cases preload htinst
    // with a nonzero value, and the trap record checks it afterwards. Below HS-mode the T-SBI calls that
    // enter the mode or raise the interrupt write htinst themselves, so only HS-mode is crossed. Without
    // Sstc, HS-mode STI is raised through T-SBI and taken on the mret.
    `ifdef H_SUPPORTED
        htinst_nonzero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htinst", "htinst") != 0) {
            bins nonzero = {1};
        }
        cp_trigger_htinst:      cross priv_mode_hs, sip_walking, sstatus_sie_one, htinst_nonzero {
            `ifndef SSTC_SUPPORTED
                `ifdef UDB_STI_INTR_IMPL
                    ignore_bins sti_tsbi = binsof(sip_walking.stip);
                `endif
            `endif
        }
    `endif

    // mip is an M CSR, so S and U write it through T-SBI and the write is recorded in M.
    // S writes sip.SSIP directly; U writes it through T-SBI, which the S handler services itself.
    // Whether the write fires the interrupt in each mode is cp_trigger/cp_trigger_tsbi.
    `ifdef UDB_SSI_INTR_IMPL
        cp_trigger_reg_mip_ssip: cross csrrs, csr_mip, rs1_ssip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;
        cp_trigger_reg_sip_ssip: cross csrrs_csrrsi, csr_sip, rs1_ssip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;
    `endif
    `ifdef UDB_SEI_INTR_IMPL
        cp_trigger_reg_mip_seip: cross csrrs, csr_mip, rs1_seip, sstatus_sie, mideleg_s_ones, sie_ones, stvec_both;
    `endif

    `ifdef SSTC_SUPPORTED
        cp_trigger_sti_sstc:    cross priv_mode_interrupts, menvcfg_stce, sstatus_sie, sie_ones, mideleg_s_ones, stvec_both, stimecmp_max_min {
            // U-mode cannot write stimecmp. With STCE = 1 the S handler writes it on U's behalf and
            // STI is taken on the sret, so only cp_trigger_sti_sstc_tsbi records it.
            // With STCE = 0 the S handler cannot write stimecmp either (it is not accessible in S),
            // so the generator skips U-mode STCE = 0; Interrupts_Sm_cg covers it from M-mode.
            ignore_bins u_min = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} && binsof(stimecmp_max_min.min);
        }
        cp_trigger_sti_sstc_tsbi: cross tsbi_return_sret, menvcfg_stce_one, stimecmp_min, sstatus_sie_on_return, sie_ones, mideleg_s_ones, stvec_both;
    `endif

    // can not check whether the conditions correspond to each other
    cp_enable_one:              cross priv_mode_interrupts, mideleg_s_ones, sstatus_sie_one, walking_sie_one, sip_matches_sie_one {
        // STI and LCOFI are raised through T-SBI by RVTEST_SET_STIME_INT and RVTEST_SET_LCOFI_INT,
        // so with their enable set they are taken on the xret and covered by cp_enable_one_tsbi
        `ifdef UDB_STI_INTR_IMPL
            ignore_bins sti_tsbi = binsof(walking_sie_one.stie); // taken on the T-SBI xret: cp_enable_one_tsbi
        `endif
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
        `ifdef UDB_SSI_INTR_IMPL
            ignore_bins platform_ssi = binsof(walking_sie_one.ssie);
        `endif
        `ifdef UDB_SEI_INTR_IMPL
            ignore_bins platform_sei = binsof(walking_sie_one.seie);
        `endif
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

    // Hypervisor interrupt CSRs, sampled in HS-mode, and sip in VS-mode
    `ifdef H_SUPPORTED
        csrr: coverpoint ins.current.insn {
            wildcard bins csrr = {CSRR};
        }
        csrrw: coverpoint ins.current.insn {
            wildcard bins csrrw = {CSRRW};
        }
        csr_hip: coverpoint ins.current.insn[31:20] {
            bins hip = {CSR_HIP};
        }
        csr_hie: coverpoint ins.current.insn[31:20] {
            bins hie = {CSR_HIE};
        }
        // csrw (csrrw) and csrr (csrrs with rs1 = x0)
        csr_rw: coverpoint ins.current.insn[14:12] {
            bins csrrw = {3'b001};
            bins csrrs = {3'b010};
        }
        csr_vsie_vsip: coverpoint ins.current.insn[31:20] {
            bins vsie = {CSR_VSIE};
            bins vsip = {CSR_VSIP};
        }
        // VS-level bits {VSEI, VSTI, VSSI} of hideleg, one bin per combination
        hideleg_vs: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[10],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[6],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2]};
        hideleg_vs_all: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[10],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[6],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2]} {
            bins all = {3'b111};
        }
        hip_write: coverpoint ins.current.rs1_val {
            bins ones  = {16'hFFFF};
            bins zeros = {0};
        }
        // mie written 0x444, or 0x1444 when GEILEN > 0 (SGEIE is implementation-defined otherwise)
        mie_444: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[12:0] {
            bins vs = {13'h0444};
            `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
                bins sgei_vs = {13'h1444};
            `endif
        }
        // With vsstatus.SIE = 1 a pending VSSI is taken on entry, and the VS handler clears vsip.SSIP before
        // the read; cp_trigger_tsbi covers vsstatus.SIE = 0/1 for the delegated VS-level interrupts
        vsstatus_sie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] {
            bins zero = {0};
        }
        hvip_vssip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[2] {
            // autofill 0/1
        }
        mip_ssip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[1] {
            bins one = {1};
        }

        // Only hip.VSSIP is writable, and it is an alias of hvip.VSSIP
        cp_hip_write:   cross priv_mode_hs, csrrw, csr_hip, hip_write;
        // hie is a view of mie, including SGEIE when GEILEN > 0
        cp_hie:         cross priv_mode_hs, csrr, csr_hie, mie_444;
        // vsie and vsip: reads and writes for each combination of hideleg.VS*I
        cp_vsip_vsie:   cross priv_mode_hs, csr_rw, csr_vsie_vsip, hideleg_vs;
        // In VS-mode, sip is vsip: it shows hvip.VSSIP when delegated and never the HS-level sip.SSIP
        `ifdef UDB_SSI_INTR_IMPL
            cp_sie_vs:      cross priv_mode_vs, csrr, csr_sip, vsstatus_sie_zero, hvip_vssip, mip_ssip_one, hideleg_vs_all;
        `endif

        // Sscofpmf makes mideleg[13] (LCOFI) writable. HS-mode clears it through T-SBI, then writes 1 to bit 13 of
        // hideleg, hie and hip and reads it back: each is read-only zero while mideleg[13] = 0.
        `ifdef SSCOFPMF_SUPPORTED
            // csrw writing bit 13 = 1, or csrr (csrrs with rs1 = x0, leaving bit 13 alone)
            csrw_one_csrr: coverpoint {ins.current.insn[14:12], ins.current.rs1_val[13]} {
                bins csrw_one = {4'b0011};
                bins csrr     = {4'b0100};
            }
            csr_hideleg_hie_hip: coverpoint ins.current.insn[31:20] {
                bins hideleg = {CSR_HIDELEG};
                bins hie     = {CSR_HIE};
                bins hip     = {CSR_HIP};
            }
            mideleg_lcofi_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[13] {
                bins zero = {0};
            }
            cp_hideleg_lcofi_roz: cross priv_mode_hs, csrw_one_csrr, csr_hideleg_hie_hip, mideleg_lcofi_zero;
        `endif
    `endif

endgroup

`undef S_SPV
`undef S_SRET_TO
`undef ONE_CSR_PAIR
`undef S_PAIR
`undef S_PAIR_OK
`undef S_PAIR_NOW
`undef S_TO_VS

`endif // S_SUPPORTED

`ifndef EXCLUDE_SM

// Classify mideleg for mideleg_both: 1 when every implemented S-level interrupt is delegated, 0 when
// no S- or M-level interrupt is, and 2 otherwise. H hardwires the VS bits to 1, so they are not checked.
function automatic logic [1:0] interrupts_mideleg_class(logic [15:0] mideleg);
    if ((mideleg & `INTR_S_LEVEL) == `INTR_S_LEVEL) return 2'd1;
    if ((mideleg & (`INTR_S_LEVEL | 16'h0888)) == 16'h0) return 2'd0;
    return 2'd2;
endfunction

covergroup Interrupts_Sm_cg with function sample(ins_t ins);
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
        mideleg_both: coverpoint interrupts_mideleg_class(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "mideleg")[15:0]) {
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

    // mip_walking for the trigger crosses, with each VS-level interrupt also in a _vs bin when hideleg
    // delegates it to VS-mode. The global enable of the cross is then vsstatus.SIE instead of
    // mstatus.SIE (sm_trigger_sie). Only VS-mode (with vsstatus.SIE = 1) and VU-mode take it.
    `ifdef H_SUPPORTED
        `define SM_TO_VS ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0] & \
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hideleg", "hideleg")[15:0] & 16'h0444) != 16'h0)
    `else
        `define SM_TO_VS 1'b0
    `endif
    mip_walking_deleg: coverpoint {`SM_TO_VS, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[15:0]} {
        `ifdef UDB_MEI_INTR_IMPL
            wildcard bins meip = {17'b0_??0?100?000?000?};
        `endif
        `ifdef UDB_MTI_INTR_IMPL
            wildcard bins mtip = {17'b0_??0?000?100?000?};
        `endif
        `ifdef UDB_MSI_INTR_IMPL
            wildcard bins msip = {17'b0_??0?000?000?100?};
        `endif
        `ifdef S_SUPPORTED
            `ifdef UDB_SEI_INTR_IMPL
                wildcard bins seip = {17'b0_??0?001?000?000?};
            `endif
            `ifdef UDB_STI_INTR_IMPL
                wildcard bins stip = {17'b0_??0?000?001?000?};
            `endif
            `ifdef UDB_SSI_INTR_IMPL
                wildcard bins ssip = {17'b0_??0?000?000?001?};
            `endif
        `endif
        `ifdef SSCOFPMF_SUPPORTED
            wildcard bins lcofip = {17'b0_??1?000?000?000?};
        `endif
        `ifdef H_SUPPORTED
            wildcard bins vseip = {17'b0_??0?010?000?000?};
            wildcard bins vstip = {17'b0_??0?000?010?000?};
            wildcard bins vssip = {17'b0_??0?000?000?010?};
            wildcard bins vseip_vs = {17'b1_??0?010?000?000?};
            wildcard bins vstip_vs = {17'b1_??0?000?010?000?};
            wildcard bins vssip_vs = {17'b1_??0?000?000?010?};
        `endif
    }
    // mtvec.MODE, or vstvec.MODE for an interrupt delegated to VS-mode
    sm_trigger_tvec: coverpoint (`SM_TO_VS ? get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstvec", "vstvec")[1:0] :
                                             get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtvec", "mode")[1:0]) {
        `ifdef UDB_MTVEC_MODES_0
            bins direct = {2'b00};
        `endif
        `ifdef UDB_MTVEC_MODES_1
            bins vector = {2'b01};
        `endif
    }
    sm_trigger_sie: coverpoint (`SM_TO_VS ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] :
                                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0]) {
        bins zero = {0};
        `ifdef S_SUPPORTED
            bins one = {1}; // SIE is read-only zero without S
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

    cp_trigger:                 cross priv_mode_interrupts, mip_walking_deleg, mstatus_mie, sm_trigger_sie, mideleg_both, mie_ones, sm_trigger_tvec {
        // MSI and MTI are the only interrupts with no pending bit reachable below M: they cannot be
        // delegated, so once pending they are enabled regardless of mstatus.MIE and are taken on the
        // mret out of the T-SBI handler that set them, before any S/U instruction retires.
        // cp_trigger_tsbi records them there. Everything else is reachable in S/U: sip.SSIP and
        // sip.LCOFIP are read-write, stimecmp is S-accessible when menvcfg.STCE is 1, and MEI/SEI
        // come from the interrupt controller. VS and VU are like U (3'b101, 3'b100).
        ignore_bins tsbi = binsof(priv_mode_interrupts) intersect {3'b001, 3'b000, 3'b101, 3'b100} &&
                           binsof(mip_walking_deleg) intersect {17'h00008, 17'h00080};
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
                                                 binsof(mip_walking_deleg.lcofip);
                ignore_bins lcofi_needs_mideleg = binsof(priv_mode_interrupts) intersect {3'b001} &&
                                                  binsof(mip_walking_deleg.lcofip) && binsof(mideleg_both.zeros);
            `endif
            // Same for STI: sip.STIP is read-only and U cannot reach stimecmp, so every U-mode STI
            // is raised from M and taken on the mret, whatever mideleg says. VS and VU likewise.
            `ifdef UDB_STI_INTR_IMPL
                ignore_bins u_cannot_raise_sti = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                                 binsof(mip_walking_deleg.stip);
            `endif
        `endif
        `ifdef H_SUPPORTED
            // The VS-level interrupts are raised through hvip, which only M and HS can write. Below HS
            // the T-SBI call that writes it returns with the interrupt enabled, so it is taken on the mret.
            ignore_bins vs_ints_tsbi = binsof(priv_mode_interrupts) intersect {3'b000, 3'b101, 3'b100} &&
                                       (binsof(mip_walking_deleg.vseip) || binsof(mip_walking_deleg.vstip) || binsof(mip_walking_deleg.vssip) ||
                                        binsof(mip_walking_deleg.vseip_vs) || binsof(mip_walking_deleg.vstip_vs) || binsof(mip_walking_deleg.vssip_vs));
        `endif
    }
    // Every interrupt taken into M-mode from M-mode writes mtinst = 0. The trigger cases preload mtinst with a
    // nonzero value, and the trap record checks it afterwards. Below M-mode the T-SBI ecall that enters the
    // mode writes mtinst itself, so only M-mode is crossed.
    `ifdef H_SUPPORTED
        mtinst_nonzero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mtinst", "mtinst") != 0) {
            bins nonzero = {1};
        }
        cp_trigger_mtinst:      cross priv_mode_m, mip_walking, mstatus_mie_one, mideleg_zeros, mtinst_nonzero;
    `endif
    `ifdef U_SUPPORTED
        cp_trigger_tsbi:        cross priv_mode_m, mret_insn, mstatus_mpv_mpp, mip_walking_deleg, mstatus_mpie, sm_trigger_sie, mideleg_both, mie_ones, sm_trigger_tvec {
            `ifdef H_SUPPORTED
                // HS writes hvip itself, so its VS-level interrupts never sit pending across an mret
                ignore_bins hs_writes_hvip = binsof(mstatus_mpv_mpp.S_mode) &&
                                             (binsof(mip_walking_deleg.vseip) || binsof(mip_walking_deleg.vstip) || binsof(mip_walking_deleg.vssip) ||
                                        binsof(mip_walking_deleg.vseip_vs) || binsof(mip_walking_deleg.vstip_vs) || binsof(mip_walking_deleg.vssip_vs));
            `endif
            // MEI is the only interrupt with no mip write path: it is raised by a store to the
            // interrupt controller from whatever mode the test runs in, so it never sits pending
            // across an mret. Every other interrupt can be written to mip through T-SBI for either
            // mideleg value (MIP_SEIP, MIP_SSIP, LCOFI, and the SSI fallback when the DUT defines no
            // RVMODEL_SET_SSW_INT). cp_trigger also records SSI and LCOFI when S writes sip itself
            // or the DUT raises SSI through its interrupt controller.
            ignore_bins mei_has_no_mip_write = binsof(mip_walking_deleg) intersect {17'h00800};
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

    // mip.SEIP reads the OR of the software bit and the platform's SEI, and csrrs and csrrc write back only the
    // software bit. Tested only when the platform has a supervisor external interrupt controller.
    `ifdef RVMODEL_SEXT_INT_EXTERNAL
        `ifdef UDB_SEI_INTR_IMPL
            `ifdef UDB_SSI_INTR_IMPL
                csrrs_csrrc: coverpoint ins.current.insn {
                    wildcard bins csrrs = {CSRRS};
                    wildcard bins csrrc = {CSRRC};
                }
                rs1_zero_ssip: coverpoint ins.current.rs1_val {
                    bins zero = {0};
                    bins ssip = {'h2};
                }
                mip_seip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[9] {
                    bins one = {1};
                }
                cp_mip_seip:    cross priv_mode_m, csrrs_csrrc, csr_mip, rs1_zero_ssip, mip_seip_one, mideleg_zeros, mie_zeros;
            `endif
        `endif
    `endif

    // Hypervisor interrupt CSRs from M-mode, and interrupt levels in VS and VU modes
    `ifdef H_SUPPORTED
        csrr: coverpoint ins.current.insn {
            wildcard bins csrr = {CSRR};
        }
        csr_mie_mip: coverpoint ins.current.insn[31:20] {
            bins mie = {CSR_MIE};
            bins mip = {CSR_MIP};
        }
        // {hvip.VS*IP == 0x444, hie[12:0]}: hie = 0x444, hie = 0x1444 (SGEIE is writable when GEILEN > 0 and
        // implementation-defined otherwise), or hvip = 0x444 with hie = 0
        alias_setup: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[15:0] & 16'h0444) == 16'h0444,
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12:0]} {
            bins hie_444  = {14'h0444};
            `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
                bins hie_1444 = {14'h1444};
            `endif
            bins hvip_444 = {14'h2000};
        }
        // mie.VS*IE and mie.SGEIE are aliases of hie, and mip.VS*IP reflect hvip
        cp_mie_mip:     cross priv_mode_m, csrr, csr_mie_mip, alias_setup;

        // Enter VS or VU mode with two or three of MSI (M-level), SSI (delegated to HS-mode by mideleg) and VSSI
        // (delegated to VS-mode by hideleg) pending and enabled, sampled at the T-SBI call: an ecall with
        // a0 = TSBI_GOTO_VSMODE (4) or TSBI_GOTO_VUMODE (5) (CTP abstraction.adoc)
        ecall: coverpoint ins.current.insn {
            bins ecall = {ECALL};
        }
        tsbi_goto_vs_vu: coverpoint ins.prev.x_wdata[10] {
            bins goto_vs = {4};
            bins goto_vu = {5};
        }
        mip_levels: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mip")[1],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "hvip")[2]} {
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
        mie_levels: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[1],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[2]} {
            bins all = {3'b111};
        }
        mideleg_ssi: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[3], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[1]} {
            bins hs = {2'b01};
        }
        hideleg_vssi: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[2] {
            bins vs = {1};
        }
        mstatus_mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
            bins zero = {0};
        }
        vsstatus_sie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] {
            bins one = {1};
        }
        cp_priority_levels:    cross priv_mode_m, ecall, tsbi_goto_vs_vu, mip_levels, mie_levels, mideleg_ssi, hideleg_vssi,
                                     mstatus_mie_zero, vsstatus_sie_one;
    `endif

endgroup

`undef SM_TO_VS
`ifdef SM_MPV
    `undef SM_MPV
`endif
`ifdef SM_WFI_PRIV
    `undef SM_WFI_PRIV
`endif

`endif // EXCLUDE_SM

// MPV is mstatus bit 39, which lands in mstatush when MXLEN is 32
`ifdef UDB_MXLEN_64
    `define INT_MPV get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0]
`else
    `define INT_MPV get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0]
`endif
// The mode an instruction runs in, or for an mret the mode it returns to: {mret, V, mode}
`define INT_ENTRY ((ins.current.insn == MRET) ? {1'b1, `INT_MPV, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} : \
                                                {1'b0, ins.prev.mode_virt, ins.prev.mode})

// Guest external interrupts exist when H is implemented with GEILEN > 0 (RVTEST_SGEI_INTR_IMPL, derived_config.svh);
// the DUT then provides RVMODEL_SET/CLR_GUEST_EXT_INT to raise them
`ifdef RVTEST_SGEI_INTR_IMPL

// Guest external interrupts taken from HS, U, VS and VU modes, and hgeip, hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI
// priority, sampled in HS-mode
covergroup Interrupts_Sgei_cg with function sample(ins_t ins);
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
    sip_s : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[9], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[5], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "sip")[1]} {
        bins none = {3'b000};
        bins sei  = {3'b100};
        bins sti  = {3'b010};
        bins ssi  = {3'b001};
    }
    mstatus_mpv_mpp_lower : coverpoint {`INT_MPV, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
        bins U_mode  = {3'b000};
        bins VS_mode = {3'b101};
        bins VU_mode = {3'b100};
    }
    // SGEI goes to HS-mode. Sampled at the csrw hie in HS-mode, or at the mret into U, VS or VU mode.
    cp_trigger_sgei:       cross priv_mode_hs, csrrw, hie, hie_write_sgeie, sstatus_sie, sgei_pending;
    mret_insn : coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    hie_sgeie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12];
    cp_trigger_sgei_lower: cross priv_mode_m, mret_insn, mstatus_mpv_mpp_lower, hie_sgeie, sgei_pending;
    // A pending S-level interrupt, or none, is taken before SGEI, which is taken before the VS-level interrupts
    cp_priority_sgei:      cross priv_mode_hs, set_sie, sgei_pending, hie_1444, sie_ones, sip_s, hvip_all, hideleg_none;

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
    // VGEIN = 0 selects no guest external interrupt: hip.VSEIP = 0 with every implemented hgeip bit set
    vgein : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12] {
        bins zero = {0};
        bins b[] = {[1:`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
    }
    hgeip_vs_vgein : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == 0 ? 0 :
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") == (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]) ? 1 :
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip")[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]] ? 3 : 2) {
        bins none   = {0};
        bins i      = {1};
        bins others = {2};
    }
    hgeie_vgein : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hstatus")[17:12]];
    // With VGEIN = 0, hgeip bit 0 is read-only zero, so every pending bit is one of the "others"
    cp_trigger_vsei_hgeip: cross priv_mode_hs, csrr, hip, vgein, hgeip_vs_vgein, hgeie_vgein {
        ignore_bins vgein_zero = binsof(vgein.zero) && (binsof(hgeip_vs_vgein.none) || binsof(hgeip_vs_vgein.i) ||
                                                        binsof(hgeie_vgein) intersect {1});
        // With GEILEN = 1 there is no implemented bit other than i, so "others" is the same case as "none"
        `ifdef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_1
            ignore_bins no_others = !binsof(vgein.zero) && binsof(hgeip_vs_vgein.others);
        `endif
    }
endgroup

`ifndef EXCLUDE_SM
// With mideleg = 0, SGEI still goes to HS-mode because mideleg[12] is read-only one. Sampled at an M-mode
// instruction, or at the mret into HS, U, VS or VU mode, whose MPIE is the M-mode MIE before the T-SBI call.
covergroup Interrupts_SgeiSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    sgei_mode : coverpoint `INT_ENTRY {
        bins M_mode  = {4'b0011};
        bins HS_mode = {4'b1001};
        bins U_mode  = {4'b1000};
        bins VS_mode = {4'b1101};
        bins VU_mode = {4'b1100};
    }
    mstatus_mie_on_entry : coverpoint ((ins.current.insn == MRET) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie")[0] :
                                                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0]) {
        // autofill 0/1
    }
    mstatus_sie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
        // autofill 0/1
    }
    hie_sgeie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "hie")[12];
    sgei_pending : coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "hgeip") & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "hgeie")) != 0) {
        bins pending = {1};
    }
    mideleg_zeros : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[15:0] {
        wildcard bins zeros = {16'b??0?0?0?0?0?0?0?};
    }
    cp_trigger_sgei: cross sgei_mode, mstatus_mie_on_entry, mstatus_sie, hie_sgeie, sgei_pending, mideleg_zeros;
endgroup
`endif // EXCLUDE_SM

`endif // RVTEST_SGEI_INTR_IMPL

`ifdef SHLCOFIDELEG_SUPPORTED

// hideleg[13] = 1 delegates LCOFI to VS-mode. LCOFI is raised through T-SBI, so it is sampled on the xret
// back to the test: the mret to an HS-mode test, or the sret to a U, VS or VU mode test.
covergroup Interrupts_Shlcofideleg_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    tsbi_return : coverpoint (((ins.current.insn == MRET) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] == 2'b01)) ? 3'b001 :
                              (ins.current.insn == SRET) ? {1'b1, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv")[0],
                                                           get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0]} : 3'b000) {
        bins HS_mode = {3'b001};
        bins U_mode  = {3'b100};
        bins VS_mode = {3'b111};
        bins VU_mode = {3'b110};
    }
    vsstatus_sie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[1] {
        // autofill 0/1
    }
    hideleg_lcofi : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[13] {
        // autofill 0/1
    }
    hideleg_lcofi_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[13] {
        bins one = {1};
    }
    sie_lcofie_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[13] {
        bins one = {1};
    }
    mip_lcofip_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[13] {
        bins one = {1};
    }
    csr_rw : coverpoint ins.current.insn[14:12] {
        bins csrrw = {3'b001};
        bins csrrs = {3'b010};
    }
    csr_vsie_vsip : coverpoint ins.current.insn[31:20] {
        bins vsie = {CSR_VSIE};
        bins vsip = {CSR_VSIP};
    }
    // HS-mode and U-mode never take LCOFI; VS-mode takes it when vsstatus.SIE = 1 and VU-mode always does
    cp_trigger_lcofi_vs: cross tsbi_return, vsstatus_sie, hideleg_lcofi_one, sie_lcofie_one, mip_lcofip_one;
    // vsip.LCOFIP and vsie.LCOFIE alias sip.LCOFIP and sie.LCOFIE when hideleg[13] = 1 and read zero otherwise
    cp_vsip_vsie_lcofi:  cross priv_mode_hs, csr_rw, csr_vsie_vsip, hideleg_lcofi;
endgroup

`ifndef EXCLUDE_SM
// With mideleg[13] = 0, hideleg[13] is read-only zero and LCOFI goes to M-mode from every mode. Sampled at the
// M-mode instruction that raises it, or at the mret into HS, U, VS or VU mode.
covergroup Interrupts_SmShlcofideleg_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    lcofi_mode : coverpoint {`INT_ENTRY, (ins.current.insn == MRET) ? 1'b0 : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0]} {
        bins M_mie0  = {5'b00110};
        bins M_mie1  = {5'b00111};
        bins HS_mode = {5'b10010};
        bins U_mode  = {5'b10000};
        bins VS_mode = {5'b11010};
        bins VU_mode = {5'b11000};
    }
    mideleg_lcofi_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "mideleg")[13] {
        bins zero = {0};
    }
    hideleg_lcofi_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "hideleg")[13] {
        bins zero = {0};
    }
    mie_lcofie_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[13] {
        bins one = {1};
    }
    mip_lcofip_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip")[13] {
        bins one = {1};
    }
    cp_trigger_lcofi_m: cross lcofi_mode, mideleg_lcofi_zero, hideleg_lcofi_zero, mie_lcofie_one, mip_lcofip_one;
endgroup
`endif // EXCLUDE_SM

`endif // SHLCOFIDELEG_SUPPORTED

`undef INT_MPV
`undef INT_ENTRY

function void interrupts_sample(int hart, int issue, ins_t ins);
    `ifdef S_SUPPORTED
        Interrupts_cg.sample(ins);
    `endif
    `ifndef EXCLUDE_SM
        Interrupts_Sm_cg.sample(ins);
    `endif
    `ifdef RVTEST_SGEI_INTR_IMPL
        Interrupts_Sgei_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Interrupts_SgeiSm_cg.sample(ins);
        `endif
    `endif
    `ifdef SHLCOFIDELEG_SUPPORTED
        Interrupts_Shlcofideleg_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Interrupts_SmShlcofideleg_cg.sample(ins);
        `endif
    `endif
endfunction
