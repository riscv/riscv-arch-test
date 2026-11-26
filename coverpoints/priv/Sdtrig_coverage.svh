///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Sdtrig groups H and HSm: triggers in VS-mode and VU-mode, guest breakpoint delegation, the H-only textra selects
// and hcontext.
// Written: David_Harris@hmc.edu 19 October 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SDTRIG
`include "general/RISCV_coverage_sdtrig_derived.svh"
`include "general/RISCV_coverage_sdtrig_functions.svh"

`ifdef H_SUPPORTED
// addi x0, x0, 0x5a: the instruction an icount trigger armed with count = 1 is taken on, which runs when it does not fire
`define SDTRIG_H_MARKER 32'h05a00013

// 1 when a trigger breakpoint was taken on this record into M, HS or VS
function automatic logic sdtrig_h_bp_taken(ins_t ins);
    return sdtrig_bp_taken(ins) || sdtrig_bp_into(ins, CSR_VSCAUSE);
endfunction

// Mode that took the trigger breakpoint on this record: 3 = M, 1 = HS, 2 = VS, 0 = none
function automatic logic [1:0] sdtrig_h_bp_handler(ins_t ins);
    if (sdtrig_bp_into(ins, CSR_MCAUSE)) return 2'd3;
    if (sdtrig_bp_into(ins, CSR_SCAUSE)) return 2'd1;
    if (sdtrig_bp_into(ins, CSR_VSCAUSE)) return 2'd2;
    return 2'd0;
endfunction

// 1 when the breakpoint taken on this record left the GVA bit of the mode that took it as specified: 1 for an
// mcontrol6 address trigger, whose tval is a guest virtual address, and 0 for icount, which writes tval = 0. A
// breakpoint taken into VS-mode has no GVA bit.
function automatic logic sdtrig_h_gva_ok(ins_t ins);
    logic gva_expected = get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] == 4'd6;
    case (sdtrig_h_bp_handler(ins))
        2'd3: `ifdef UDB_MXLEN_64
                  return get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MSTATUS, "gva")[0] == gva_expected;
              `else
                  return get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MSTATUSH, "gva")[0] == gva_expected;
              `endif
        2'd1: return get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS, "gva")[0] == gva_expected;
        2'd2: return 1'b1;
        default: return 1'b0;
    endcase
endfunction

// Outcome for the selected trigger, whose tdata1 bit own enables it in the guest mode under test and whose bits
// others enable it in every other mode:
//   1: own set, others clear, and a breakpoint was taken    2: own clear, others set, and no breakpoint    0: other
// A bit of a mode that the hart cannot enable reads 0, so "others set" needs only one of them.
function automatic logic [1:0] sdtrig_h_mode_outcome(ins_t ins, int own, logic [XLEN-1:0] others);
    logic [XLEN-1:0] tdata1 = get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1);
    logic bp = sdtrig_h_bp_taken(ins);
    if (tdata1[own] && (tdata1 & others) == '0 && bp) return 2'd1;
    if (!tdata1[own] && (tdata1 & others) != '0 && !bp) return 2'd2;
    return 2'd0;
endfunction

// {V, mode} the trap on this record was taken from: an interrupt taken on an mret record is taken in the mode the
// mret returns to
function automatic logic [2:0] sdtrig_h_trap_origin(ins_t ins);
    logic mpv;
    `ifdef UDB_MXLEN_64
        mpv = get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpv")[0];
    `else
        mpv = get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUSH, "mpv")[0];
    `endif
    if (ins.current.insn == MRET) return {mpv, get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp")[1:0]};
    return {ins.prev.mode_virt, ins.prev.mode};
endfunction

// 1 when a trap with cause was taken into HS-mode on this record
function automatic logic sdtrig_h_hs_trap(ins_t ins, logic [XLEN-1:0] cause);
    return sdtrig_trap_wrote(ins, CSR_SCAUSE) && ins.current.csr[CSR_SCAUSE] == cause;
endfunction

// With an icount trigger selected: the marker, or the record that takes the breakpoint, which the trace puts on the
// counted instruction before the marker
function automatic logic sdtrig_h_icount_point(ins_t ins);
    return get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] == 4'd3 &&
           (ins.current.insn == `SDTRIG_H_MARKER || sdtrig_h_bp_taken(ins));
endfunction

// textra: {mhvalue, mhselect[2]}, 14 bits on RV64 and 7 on RV32
function automatic logic [13:0] sdtrig_h_mhvalue_sel(logic [XLEN-1:0] t3);
    return {sdtrig_textra_mhvalue(t3), sdtrig_textra_mhselect(t3)[2]};
endfunction
// mhselect = 1/5: {mhvalue, mhselect[2]} equals the low bits of mcontext, in the MHVALUE_LEN + 1 bits it implements
function automatic logic sdtrig_h_mctx_match(logic [XLEN-1:0] t3, logic [XLEN-1:0] mcontext);
    logic [13:0] mask = 14'((2 << `UDB_SDTRIG_TEXTRA_MHVALUE_LEN) - 1);
    return (sdtrig_h_mhvalue_sel(t3) & mask) == (14'(mcontext) & mask);
endfunction
// mhselect = 2/6: the low VMIDMAX bits of {mhvalue, mhselect[2]} equal hgatp.VMID (RV64 57:44, RV32 28:22)
function automatic logic sdtrig_h_vmid_match(logic [XLEN-1:0] t3, logic [XLEN-1:0] hgatp);
    return sdtrig_h_mhvalue_sel(t3) == 14'((XLEN == 64) ? ((hgatp >> 44) & 'h3fff) : ((hgatp >> 22) & 'h7f));
endfunction
// 1: the context matches and a breakpoint was taken    2: it does not match and no breakpoint    0: other
function automatic logic [1:0] sdtrig_h_textra_outcome(ins_t ins, logic match);
    logic bp = sdtrig_h_bp_taken(ins);
    if (match && bp) return 2'd1;
    if (!match && !bp) return 2'd2;
    return 2'd0;
endfunction

covergroup Sdtrig_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    // mcontrol6: a sw to the address that a store address trigger watches (select = 0, store = 1)
    sw_watched: coverpoint ins.current.insn iff (
            get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] == 4'd6 &&
            get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "store")[0] &&
            !get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "select")[0] &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA2) == ins.current.eff_addr) {
        type_option.weight = 0;
        wildcard bins sw = {SW};
    }
    // mcontrol6 mode bits: vs 24, vu 23, m 6, s 4, u 3
    mcontrol6_outcome_vs: coverpoint sdtrig_h_mode_outcome(ins, 24, (1 << 23) | (1 << 6) | (1 << 4) | (1 << 3)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VS_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    mcontrol6_outcome_vu: coverpoint sdtrig_h_mode_outcome(ins, 23, (1 << 24) | (1 << 6) | (1 << 4) | (1 << 3)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VU_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    // icount: the marker or the breakpoint taken before it
    icount_point: coverpoint sdtrig_h_icount_point(ins) {
        type_option.weight = 0;
        bins marker_or_breakpoint = {1'b1};
    }
    // icount mode bits: vs 26, vu 25, m 9, s 7, u 6
    icount_outcome_vs: coverpoint sdtrig_h_mode_outcome(ins, 26, (1 << 25) | (1 << 9) | (1 << 7) | (1 << 6)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VS_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    icount_outcome_vu: coverpoint sdtrig_h_mode_outcome(ins, 25, (1 << 26) | (1 << 9) | (1 << 7) | (1 << 6)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VU_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    // delegation: the type of the trigger whose breakpoint was taken, and where it was taken
    bp_type: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        bins icount    = {4'd3};
        bins mcontrol6 = {4'd6};
    }
    // {medeleg[3], hedeleg[3], the mode that took the breakpoint}
    bp_routing: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3],
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG)[3],
                            sdtrig_h_bp_handler(ins)} iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        `ifdef UDB_MEDELEG_DELEGATABLE_3  // medeleg[3] is read-only 0 on a hart that uses tcontrol for reentrancy
            bins delegated_to_hs = {4'b10_01};
            bins delegated_to_vs = {4'b11_10};
        `endif
    }
    bp_gva: coverpoint sdtrig_h_gva_ok(ins) iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        bins as_specified = {1'b1};
    }
    // textra
    guest_mode: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
        type_option.weight = 0;
        bins VS_mode = {3'b101};
        bins VU_mode = {3'b100};
    }
    mhselect_mctx: coverpoint sdtrig_textra_mhselect(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3)) {
        type_option.weight = 0;
        bins mcontext_select_0 = {3'd1};
        bins mcontext_select_1 = {3'd5};
    }
    mctx_outcome: coverpoint sdtrig_h_textra_outcome(ins, sdtrig_h_mctx_match(
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3),
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MCONTEXT))) {
        type_option.weight = 0;
        bins match_fired      = {2'd1};
        bins mismatch_no_fire = {2'd2};
    }
    mhselect_vmid: coverpoint sdtrig_textra_mhselect(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3)) {
        type_option.weight = 0;
        bins vmid_select_0 = {3'd2};
        bins vmid_select_1 = {3'd6};
    }
    vmid_outcome: coverpoint sdtrig_h_textra_outcome(ins, sdtrig_h_vmid_match(
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3),
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP))) {
        type_option.weight = 0;
        bins match_fired      = {2'd1};
        bins mismatch_no_fire = {2'd2};
    }
    sselect_asid: coverpoint sdtrig_textra_sselect(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3)) {
        type_option.weight = 0;
        bins asid = {2'd2};
    }
    asid_outcome: coverpoint sdtrig_h_textra_outcome(ins, sdtrig_textra_asid_match(
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA3),
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP))) {
        type_option.weight = 0;
        bins match_fired      = {2'd1};
        bins mismatch_no_fire = {2'd2};
    }
    // hcontext
    csr_hcontext: coverpoint ins.current.insn[31:20] {
        type_option.weight = 0;
        bins hcontext = {CSR_HCONTEXT};
    }

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
        cp_mcontrol6_vs: cross priv_mode_vs, triggernum_mcontrol6, sw_watched, mcontrol6_outcome_vs;  // mcontrol6 triggers * 2 outcomes
        cp_mcontrol6_vu: cross priv_mode_vu, triggernum_mcontrol6, sw_watched, mcontrol6_outcome_vu;  // mcontrol6 triggers * 2 outcomes
    `endif
    `ifdef SDTRIG_ICOUNT_ANY
        cp_icount_vs: cross priv_mode_vs, triggernum_icount, icount_point, icount_outcome_vs;  // icount triggers * 2 outcomes
        cp_icount_vu: cross priv_mode_vu, triggernum_icount, icount_point, icount_outcome_vu;  // icount triggers * 2 outcomes
    `endif
    `ifdef UDB_MEDELEG_DELEGATABLE_3
        cp_breakpoint_delegate_vs: cross priv_mode_vs, triggernum, bp_type, bp_routing, bp_gva;  // NTRIG * 2 types * 2 (into HS, into VS)
        cp_breakpoint_delegate_vu: cross priv_mode_vu, triggernum, bp_type, bp_routing, bp_gva;  // NTRIG * 2 types * 2 (into HS, into VS)
    `endif
    `ifdef SDTRIG_ICOUNT_ANY
        `ifdef UDB_SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH
            cp_textra_mctx_sel:   cross guest_mode, triggernum_icount, icount_point, mhselect_mctx, mctx_outcome;  // 2 modes * icount triggers * 2 selects * 2
        `endif
        `ifdef UDB_SDTRIG_TEXTRA_MHSELECT_VMID_MATCH
            cp_textra_vmid_sel:   cross guest_mode, triggernum_icount, icount_point, mhselect_vmid, vmid_outcome;  // 2 modes * icount triggers * 2 selects * 2
        `endif
        `ifdef UDB_SDTRIG_TEXTRA_SSELECT_ASID_MATCH
            cp_textra_vsatp_asid: cross guest_mode, triggernum_icount, icount_point, sselect_asid, asid_outcome;   // 2 modes * icount triggers * 2
        `endif
    `endif
    `ifdef UDB_HCONTEXT_IMPLEMENTED
        cp_hcontext_hs: cross priv_mode_hs, csr_read_write, csr_hcontext;  // 2
    `endif
endgroup

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Sdtrig_HSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    // delegation: breakpoints from the guest into M-mode
    bp_type: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        bins icount    = {4'd3};
        bins mcontrol6 = {4'd6};
    }
    // {medeleg[3], the mode that took the breakpoint}
    bp_routing: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3], sdtrig_h_bp_handler(ins)} iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        bins not_delegated_to_m = {3'b0_11};
    }
    bp_gva: coverpoint sdtrig_h_gva_ok(ins) iff (sdtrig_h_bp_taken(ins)) {
        type_option.weight = 0;
        bins as_specified = {1'b1};
    }
    // itrigger and etrigger: the trap was taken from VS-mode or VU-mode
    trap_from_vs: coverpoint sdtrig_h_trap_origin(ins) {
        type_option.weight = 0;
        bins VS_mode = {3'b101};
    }
    trap_from_vu: coverpoint sdtrig_h_trap_origin(ins) {
        type_option.weight = 0;
        bins VU_mode = {3'b100};
    }
    // an itrigger selecting SSI is selected, and an SSI was taken into HS-mode on this record
    itrigger_ssi: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] iff (
            sdtrig_h_hs_trap(ins, {1'b1, (XLEN-1)'(1)}) && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA2)[1]) {
        type_option.weight = 0;
        bins itrigger = {4'd4};
    }
    // an etrigger selecting virtual instruction is selected, and a virtual-instruction exception was taken into
    // HS-mode on this record
    etrigger_virtual: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA1, "type")[3:0] iff (
            sdtrig_h_hs_trap(ins, 22) && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_TDATA2)[22]) {
        type_option.weight = 0;
        bins etrigger = {4'd5};
    }
    // itrigger and etrigger mode bits: vs 12, vu 11, m 9, s 7, u 6
    trap_outcome_vs: coverpoint sdtrig_h_mode_outcome(ins, 12, (1 << 11) | (1 << 9) | (1 << 7) | (1 << 6)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VS_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    trap_outcome_vu: coverpoint sdtrig_h_mode_outcome(ins, 11, (1 << 12) | (1 << 9) | (1 << 7) | (1 << 6)) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_VU_WRITABLE
            bins own_fired  = {2'd1};
        `endif
        bins others_no_fire = {2'd2};
    }
    // hcontext
    csr_hcontext: coverpoint ins.current.insn[31:20] {
        type_option.weight = 0;
        bins hcontext = {CSR_HCONTEXT};
    }

    // main coverpoints
    cp_breakpoint_delegate_vs: cross priv_mode_vs, triggernum, bp_type, bp_routing, bp_gva;  // NTRIG * 2 types
    cp_breakpoint_delegate_vu: cross priv_mode_vu, triggernum, bp_type, bp_routing, bp_gva;  // NTRIG * 2 types
    `ifdef SDTRIG_ITRIGGER_ANY
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_1
    `ifdef UDB_SSI_INTR_IMPL
        cp_itrigger_vs: cross trap_from_vs, triggernum_itrigger, itrigger_ssi, trap_outcome_vs;  // itrigger triggers * 2 outcomes
        cp_itrigger_vu: cross trap_from_vu, triggernum_itrigger, itrigger_ssi, trap_outcome_vu;  // itrigger triggers * 2 outcomes
    `endif
    `endif
    `endif
    `ifdef SDTRIG_ETRIGGER_ANY
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_22
        cp_etrigger_vs: cross trap_from_vs, triggernum_etrigger, etrigger_virtual, trap_outcome_vs;  // etrigger triggers * 2 outcomes
        cp_etrigger_vu: cross trap_from_vu, triggernum_etrigger, etrigger_virtual, trap_outcome_vu;  // etrigger triggers * 2 outcomes
    `endif
    `endif
    `ifdef UDB_HCONTEXT_IMPLEMENTED
        cp_hcontext_m: cross priv_mode_m, csr_read_write, csr_hcontext;  // 2
    `endif
endgroup
`endif

`undef SDTRIG_H_MARKER
`endif

function void sdtrig_sample(int hart, int issue, ins_t ins);
    `ifdef H_SUPPORTED
        Sdtrig_H_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Sdtrig_HSm_cg.sample(ins);
        `endif
    `endif
endfunction
