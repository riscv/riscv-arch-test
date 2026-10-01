///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Tianze Wu wutianze@ict.ac.cn 15 September 2026
// Assisted by the MLVP AI framework
//
// Copyright (C) 2026 Tianze Wu
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// H privilege, CSR and instruction behavior; no coverage execution claim.
`define COVER_H

function automatic bit h_peer_unchanged(ins_t ins);
    case (ins.current.insn[31:20])
        CSR_SSTATUS: return ins.current.mode_virt ? (ins.current.csr[CSR_SSTATUS] == ins.prev.csr[CSR_SSTATUS]) : (ins.current.csr[CSR_VSSTATUS] == ins.prev.csr[CSR_VSSTATUS]);
        CSR_VSSTATUS: return ins.current.csr[CSR_SSTATUS] == ins.prev.csr[CSR_SSTATUS];
        CSR_SIE: return ins.current.mode_virt ? (ins.current.csr[CSR_SIE] == ins.prev.csr[CSR_SIE]) : (ins.current.csr[CSR_VSIE] == ins.prev.csr[CSR_VSIE]);
        CSR_VSIE: return ins.current.csr[CSR_SIE] == ins.prev.csr[CSR_SIE];
        CSR_STVAL: return ins.current.mode_virt ? (ins.current.csr[CSR_STVAL] == ins.prev.csr[CSR_STVAL]) : (ins.current.csr[CSR_VSTVAL] == ins.prev.csr[CSR_VSTVAL]);
        CSR_VSTVAL: return ins.current.csr[CSR_STVAL] == ins.prev.csr[CSR_STVAL];
        CSR_SIP: return ins.current.mode_virt ? (ins.current.csr[CSR_SIP] == ins.prev.csr[CSR_SIP]) : (ins.current.csr[CSR_VSIP] == ins.prev.csr[CSR_VSIP]);
        CSR_VSIP: return ins.current.csr[CSR_SIP] == ins.prev.csr[CSR_SIP];
        CSR_STVEC: return ins.current.mode_virt ? (ins.current.csr[CSR_STVEC] == ins.prev.csr[CSR_STVEC]) : (ins.current.csr[CSR_VSTVEC] == ins.prev.csr[CSR_VSTVEC]);
        CSR_VSTVEC: return ins.current.csr[CSR_STVEC] == ins.prev.csr[CSR_STVEC];
        CSR_SSCRATCH: return ins.current.mode_virt ? (ins.current.csr[CSR_SSCRATCH] == ins.prev.csr[CSR_SSCRATCH]) : (ins.current.csr[CSR_VSSCRATCH] == ins.prev.csr[CSR_VSSCRATCH]);
        CSR_VSSCRATCH: return ins.current.csr[CSR_SSCRATCH] == ins.prev.csr[CSR_SSCRATCH];
        CSR_SEPC: return ins.current.mode_virt ? (ins.current.csr[CSR_SEPC] == ins.prev.csr[CSR_SEPC]) : (ins.current.csr[CSR_VSEPC] == ins.prev.csr[CSR_VSEPC]);
        CSR_VSEPC: return ins.current.csr[CSR_SEPC] == ins.prev.csr[CSR_SEPC];
        CSR_SCAUSE: return ins.current.mode_virt ? (ins.current.csr[CSR_SCAUSE] == ins.prev.csr[CSR_SCAUSE]) : (ins.current.csr[CSR_VSCAUSE] == ins.prev.csr[CSR_VSCAUSE]);
        CSR_VSCAUSE: return ins.current.csr[CSR_SCAUSE] == ins.prev.csr[CSR_SCAUSE];
        CSR_SATP: return ins.current.mode_virt ? (ins.current.csr[CSR_SATP] == ins.prev.csr[CSR_SATP]) : (ins.current.csr[CSR_VSATP] == ins.prev.csr[CSR_VSATP]);
        CSR_VSATP: return ins.current.csr[CSR_SATP] == ins.prev.csr[CSR_SATP];
        default: return 0;
    endcase
endfunction

function automatic bit h_outcome(ins_t ins, int expected);
    return expected == 0 ? !ins.current.trap :
        (ins.current.trap && ins.current.csr[CSR_MCAUSE] == expected);
endfunction

function automatic bit h_csr_outcome(ins_t ins);
    bit writing;
    bit readonly_csr;
    int privilege;
    int expected;
    writing = ins.current.insn[14:12] == 1 || ins.current.insn[19:15] != 0;
    readonly_csr = ins.current.insn[31:30] == 2'b11;
    privilege = int'(ins.current.insn[29:28]);
    expected = 0;
    if (readonly_csr && writing) expected = 2;
    else if (ins.current.mode_virt) begin
        if (privilege == 3) expected = 2;
        else if (privilege == 2 || (privilege == 1 && ins.current.mode == 0)) expected = 22;
        else if (ins.current.insn[31:20] == CSR_SATP && ins.prev.csr[CSR_HSTATUS][20]) expected = 22;
    end else if ((privilege == 3 && ins.current.mode != 3) ||
                 (privilege != 0 && ins.current.mode == 0)) expected = 2;
    else if (ins.current.mode == 1 && ins.current.insn[31:20] inside {CSR_SATP,CSR_HGATP} &&
             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") != 0) expected = 2;
    return h_outcome(ins, expected);
endfunction

covergroup H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    source_mode: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins m = {3'b011};
        bins hs = {3'b001};
        bins u = {3'b000};
        bins vs = {3'b101};
        bins vu = {3'b100};
    }
    mode_m: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins modes[] = {3};
    }
    mode_hs: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins modes[] = {1};
    }
    mode_vs: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins modes[] = {5};
    }
    mode_u: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins modes[] = {0};
    }
    mode_vu: coverpoint {ins.current.mode_virt, ins.current.mode} {
        bins modes[] = {4};
    }
    csr_operation: coverpoint {ins.current.insn[14:12], ins.current.insn[19:15] == 0} iff (ins.current.insn[6:0] == 7'h73 && ins.current.insn[14:12] inside {1,2,3}) {
        bins write = {4'b0010,4'b0011};
        bins set = {4'b0100};
        bins clear = {4'b0110};
        bins read = {4'b0101};
    }
    csr_set_clear: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'h73 && ins.current.insn[14:12] inside {1,2,3}) {
        bins set = {2};
        bins clear = {3};
    }
    csr_write: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'h73 && ins.current.insn[14:12] inside {1,2,3}) {
        bins write = {1};
    }
    csr_read: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'h73 && ins.current.insn[14:12] inside {1,2,3} && ins.current.insn[19:15] == 0) {
        bins read = {2};
    }
    retired: coverpoint ins.current.trap {
        bins no_trap = {0};
    }
    trap_seen: coverpoint ins.current.trap {
        bins trap = {1};
    }
    csr_expected_outcome: coverpoint h_csr_outcome(ins) {
        bins correct = {1};
    }
    illegal_outcome: coverpoint h_outcome(ins, 2) {
        bins correct = {1};
    }
    peer_unchanged: coverpoint h_peer_unchanged(ins) {
        bins unchanged = {1};
    }
    rd_nonzero: coverpoint ins.current.rd_val != 0 {
        bins nonzero = {1};
    }
    m_csrs: coverpoint ins.current.insn[31:20] {
        bins mtval2 = {CSR_MTVAL2};
        bins mtinst = {CSR_MTINST};
    }
    hs_vs_csrs: coverpoint ins.current.insn[31:20] {
        bins hstatus = {CSR_HSTATUS};
        bins hedeleg = {CSR_HEDELEG};
        bins hideleg = {CSR_HIDELEG};
        bins hie = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie = {CSR_HGEIE};
        bins henvcfg = {CSR_HENVCFG};
        bins htval = {CSR_HTVAL};
        bins hip = {CSR_HIP};
        bins hvip = {CSR_HVIP};
        bins htinst = {CSR_HTINST};
        bins vsstatus = {CSR_VSSTATUS};
        bins vsie = {CSR_VSIE};
        bins vstval = {CSR_VSTVAL};
        bins vsip = {CSR_VSIP};
        bins vstvec = {CSR_VSTVEC};
        bins vsscratch = {CSR_VSSCRATCH};
        bins vsepc = {CSR_VSEPC};
        bins vscause = {CSR_VSCAUSE};
        bins hgeip = {CSR_HGEIP};
        `ifdef ZICNTR_SUPPORTED
        bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
        bins hedelegh = {CSR_HEDELEGH};
        bins henvcfgh = {CSR_HENVCFGH};
        `ifdef ZICNTR_SUPPORTED
        bins htimedeltah = {CSR_HTIMEDELTAH};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
        `endif
    }
    all_h_csrs: coverpoint ins.current.insn[31:20] {
        bins mtval2 = {CSR_MTVAL2};
        bins mtinst = {CSR_MTINST};
        bins hstatus = {CSR_HSTATUS};
        bins hedeleg = {CSR_HEDELEG};
        bins hideleg = {CSR_HIDELEG};
        bins hie = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie = {CSR_HGEIE};
        bins henvcfg = {CSR_HENVCFG};
        bins htval = {CSR_HTVAL};
        bins hip = {CSR_HIP};
        bins hvip = {CSR_HVIP};
        bins htinst = {CSR_HTINST};
        bins vsstatus = {CSR_VSSTATUS};
        bins vsie = {CSR_VSIE};
        bins vstval = {CSR_VSTVAL};
        bins vsip = {CSR_VSIP};
        bins vstvec = {CSR_VSTVEC};
        bins vsscratch = {CSR_VSSCRATCH};
        bins vsepc = {CSR_VSEPC};
        bins vscause = {CSR_VSCAUSE};
        bins hgeip = {CSR_HGEIP};
        `ifdef ZICNTR_SUPPORTED
        bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
        bins hedelegh = {CSR_HEDELEGH};
        bins henvcfgh = {CSR_HENVCFGH};
        `ifdef ZICNTR_SUPPORTED
        bins htimedeltah = {CSR_HTIMEDELTAH};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
        `endif
    }
    mtval_csr: coverpoint ins.current.insn[31:20] {
        bins mtval = {CSR_MTVAL};
    }
    replica_csrs: coverpoint ins.current.insn[31:20] {
        bins sstatus = {CSR_SSTATUS};
        bins sie = {CSR_SIE};
        bins stval = {CSR_STVAL};
        bins sip = {CSR_SIP};
        bins stvec = {CSR_STVEC};
        bins sscratch = {CSR_SSCRATCH};
        bins sepc = {CSR_SEPC};
        bins scause = {CSR_SCAUSE};
        bins satp = {CSR_SATP};
        bins vsstatus = {CSR_VSSTATUS};
        bins vsie = {CSR_VSIE};
        bins vstval = {CSR_VSTVAL};
        bins vsip = {CSR_VSIP};
        bins vstvec = {CSR_VSTVEC};
        bins vsscratch = {CSR_VSSCRATCH};
        bins vsepc = {CSR_VSEPC};
        bins vscause = {CSR_VSCAUSE};
    }
    guest_s_csrs: coverpoint ins.current.insn[31:20] {
        bins sstatus = {CSR_SSTATUS};
        bins sie = {CSR_SIE};
        bins stval = {CSR_STVAL};
        bins sip = {CSR_SIP};
        bins stvec = {CSR_STVEC};
        bins sscratch = {CSR_SSCRATCH};
        bins sepc = {CSR_SEPC};
        bins scause = {CSR_SCAUSE};
        bins satp = {CSR_SATP};
    }
    hs_walk_csrs: coverpoint ins.current.insn[31:20] {
        bins hedeleg = {CSR_HEDELEG};
        bins hideleg = {CSR_HIDELEG};
        bins hie = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie = {CSR_HGEIE};
        bins henvcfg = {CSR_HENVCFG};
        bins htval = {CSR_HTVAL};
        bins hip = {CSR_HIP};
        bins hvip = {CSR_HVIP};
        bins htinst = {CSR_HTINST};
        bins vsie = {CSR_VSIE};
        bins vstval = {CSR_VSTVAL};
        bins vsip = {CSR_VSIP};
        bins vstvec = {CSR_VSTVEC};
        bins vsscratch = {CSR_VSSCRATCH};
        bins vsepc = {CSR_VSEPC};
        bins vscause = {CSR_VSCAUSE};
        `ifdef ZICNTR_SUPPORTED
        bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
        bins hedelegh = {CSR_HEDELEGH};
        bins henvcfgh = {CSR_HENVCFGH};
        `ifdef ZICNTR_SUPPORTED
        bins htimedeltah = {CSR_HTIMEDELTAH};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
        `endif
    }
    m_walking_field: coverpoint (ins.current.insn[31:20] * 64) + $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins mtval2[] = {[(CSR_MTVAL2 * 64)+0:(CSR_MTVAL2 * 64)+`UDB_MXLEN-1]};
        bins mtinst[] = {[(CSR_MTINST * 64)+0:(CSR_MTINST * 64)+`UDB_MXLEN-1]};
    }
    hs_walking_field: coverpoint (ins.current.insn[31:20] * 64) + $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins hedeleg[] = {(CSR_HEDELEG * 64)+0, (CSR_HEDELEG * 64)+1, (CSR_HEDELEG * 64)+2, (CSR_HEDELEG * 64)+3, (CSR_HEDELEG * 64)+4, (CSR_HEDELEG * 64)+5, (CSR_HEDELEG * 64)+6, (CSR_HEDELEG * 64)+7, (CSR_HEDELEG * 64)+8, (CSR_HEDELEG * 64)+12, (CSR_HEDELEG * 64)+13, (CSR_HEDELEG * 64)+15};
        bins hideleg[] = {(CSR_HIDELEG * 64)+2, (CSR_HIDELEG * 64)+6, (CSR_HIDELEG * 64)+10};
        bins hie[] = {(CSR_HIE * 64)+2, (CSR_HIE * 64)+6, (CSR_HIE * 64)+10, (CSR_HIE * 64)+12};
        bins hcounteren[] = {(CSR_HCOUNTEREN * 64)+0, (CSR_HCOUNTEREN * 64)+1, (CSR_HCOUNTEREN * 64)+2, (CSR_HCOUNTEREN * 64)+3, (CSR_HCOUNTEREN * 64)+4, (CSR_HCOUNTEREN * 64)+5, (CSR_HCOUNTEREN * 64)+6, (CSR_HCOUNTEREN * 64)+7, (CSR_HCOUNTEREN * 64)+8, (CSR_HCOUNTEREN * 64)+9, (CSR_HCOUNTEREN * 64)+10, (CSR_HCOUNTEREN * 64)+11, (CSR_HCOUNTEREN * 64)+12, (CSR_HCOUNTEREN * 64)+13, (CSR_HCOUNTEREN * 64)+14, (CSR_HCOUNTEREN * 64)+15, (CSR_HCOUNTEREN * 64)+16, (CSR_HCOUNTEREN * 64)+17, (CSR_HCOUNTEREN * 64)+18, (CSR_HCOUNTEREN * 64)+19, (CSR_HCOUNTEREN * 64)+20, (CSR_HCOUNTEREN * 64)+21, (CSR_HCOUNTEREN * 64)+22, (CSR_HCOUNTEREN * 64)+23, (CSR_HCOUNTEREN * 64)+24, (CSR_HCOUNTEREN * 64)+25, (CSR_HCOUNTEREN * 64)+26, (CSR_HCOUNTEREN * 64)+27, (CSR_HCOUNTEREN * 64)+28, (CSR_HCOUNTEREN * 64)+29, (CSR_HCOUNTEREN * 64)+30, (CSR_HCOUNTEREN * 64)+31};
        bins hgeie[] = {[(CSR_HGEIE * 64)+1:(CSR_HGEIE * 64)+`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
        bins henvcfg[] = {(CSR_HENVCFG * 64)+0};
        bins htval[] = {[(CSR_HTVAL * 64)+0:(CSR_HTVAL * 64)+`UDB_MXLEN-1]};
        bins hip[] = {(CSR_HIP * 64)+2};
        bins hvip[] = {(CSR_HVIP * 64)+2, (CSR_HVIP * 64)+6, (CSR_HVIP * 64)+10};
        bins htinst[] = {[(CSR_HTINST * 64)+0:(CSR_HTINST * 64)+`UDB_MXLEN-1]};
        bins vsie[] = {(CSR_VSIE * 64)+1, (CSR_VSIE * 64)+5, (CSR_VSIE * 64)+9};
        bins vstval[] = {[(CSR_VSTVAL * 64)+0:(CSR_VSTVAL * 64)+`UDB_MXLEN-1]};
        bins vsip[] = {(CSR_VSIP * 64)+1};
        bins vstvec[] = {[(CSR_VSTVEC * 64)+2:(CSR_VSTVEC * 64)+`UDB_MXLEN-1]};
        bins vsscratch[] = {[(CSR_VSSCRATCH * 64)+0:(CSR_VSSCRATCH * 64)+`UDB_MXLEN-1]};
        bins vsepc[] = {[(CSR_VSEPC * 64)+0:(CSR_VSEPC * 64)+`UDB_MXLEN-1]};
        bins vscause[] = {(CSR_VSCAUSE*64), (CSR_VSCAUSE*64)+1, (CSR_VSCAUSE*64)+2, (CSR_VSCAUSE*64)+3, (CSR_VSCAUSE*64)+`UDB_MXLEN-1};
        `ifdef ZICNTR_SUPPORTED
        bins htimedelta[] = {[(CSR_HTIMEDELTA*64):(CSR_HTIMEDELTA*64)+`UDB_MXLEN-1]};
        `ifdef UDB_MXLEN_32
        bins htimedeltah[] = {[(CSR_HTIMEDELTAH*64):(CSR_HTIMEDELTAH*64)+31]};
        `endif
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmp[] = {[(CSR_VSTIMECMP*64):(CSR_VSTIMECMP*64)+`UDB_MXLEN-1]};
        `ifdef UDB_MXLEN_32
        bins vstimecmph[] = {[(CSR_VSTIMECMPH*64):(CSR_VSTIMECMPH*64)+31]};
        `endif
        `endif
    }
    nonreplica_csrs: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
        bins scounteren = {CSR_SCOUNTEREN};
    }
    vscause_csr: coverpoint ins.current.insn[31:20] {
        bins vscause = {CSR_VSCAUSE};
    }
    sstatus_csr: coverpoint ins.current.insn[31:20] {
        bins sstatus = {CSR_SSTATUS};
    }
    high_half_csrs: coverpoint ins.current.insn[31:20] {
        bins hedelegh = {CSR_HEDELEGH};
        bins henvcfgh = {CSR_HENVCFGH};
        `ifdef ZICNTR_SUPPORTED
        bins htimedeltah = {CSR_HTIMEDELTAH};
        `endif
        `ifdef SSTC_SUPPORTED
        bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    vscause_value: coverpoint ins.current.rs1_val {
        bins exception_code[] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,15,20,21,22,23};
        bins software_interrupt = {(`UDB_MXLEN'(1) << (`UDB_MXLEN-1)) | 1};
        bins timer_interrupt = {(`UDB_MXLEN'(1) << (`UDB_MXLEN-1)) | 5};
        bins external_interrupt = {(`UDB_MXLEN'(1) << (`UDB_MXLEN-1)) | 9};
    }
    vscause_equal: coverpoint ins.current.csr[CSR_VSCAUSE] == ins.current.rs1_val {
        bins legal_value_retained = {1};
    }
    sd_attempt: coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins zero = {0};
        bins one = {1};
    }
    fs_written: coverpoint ins.current.rs1_val[14:13] {
        bins state[] = {[0:3]};
    }
    vs_written: coverpoint ins.current.rs1_val[10:9] {
        bins state[] = {[0:3]};
    }
    sd_correct: coverpoint ins.current.csr[CSR_VSSTATUS][`UDB_MXLEN-1] == ((ins.current.csr[CSR_VSSTATUS][14:13] == 3) || (ins.current.csr[CSR_VSSTATUS][10:9] == 3) || (ins.current.csr[CSR_VSSTATUS][16:15] == 3)) {
        bins guest_summary = {1};
    }
    cp_m_hcsr_access: cross mode_m, all_h_csrs, csr_operation, csr_expected_outcome;
    cp_m_hcsr_walk: cross mode_m, m_walking_field, csr_set_clear, retired;
    cp_m_replica: cross mode_m, replica_csrs, csr_operation, peer_unchanged, retired;
    cp_m_mtval: cross mode_m, mtval_csr, csr_read, rd_nonzero, retired;
    cp_hs_hcsr_access: cross mode_hs, hs_vs_csrs, csr_operation, csr_expected_outcome;
    cp_hs_hcsr_walk: cross mode_hs, hs_walking_field, csr_set_clear, retired;
    cp_hs_mcsr_denied: cross mode_hs, m_csrs, csr_operation, trap_seen, csr_expected_outcome;
    cp_hs_replica: cross mode_hs, replica_csrs, csr_operation, peer_unchanged, retired;
    cp_hs_vscause: cross mode_hs, vscause_csr, csr_write, vscause_value, vscause_equal, retired;
    cp_vs_mcsr_denied: cross mode_vs, m_csrs, csr_operation, trap_seen, csr_expected_outcome;
    `ifdef UDB_MXLEN_64
    cp_vs_high_half: cross mode_vs, high_half_csrs, csr_operation, trap_seen, illegal_outcome;
    `endif
    cp_vs_replica: cross mode_vs, guest_s_csrs, csr_operation, peer_unchanged, retired;
    cp_vs_nonreplica: cross mode_vs, nonreplica_csrs, csr_operation, retired;
    `ifdef F_SUPPORTED
    `ifdef V_SUPPORTED
    cp_vs_sd: cross mode_vs, sstatus_csr, csr_write, sd_attempt, fs_written, vs_written, sd_correct, retired;
    `endif
    `endif
    cp_u_hcsr_denied: cross mode_u, all_h_csrs, csr_operation, trap_seen, csr_expected_outcome;
    `ifdef UDB_MXLEN_64
    cp_u_high_half: cross mode_u, high_half_csrs, csr_operation, trap_seen, illegal_outcome;
    `endif
    cp_vu_csr_denied: cross mode_vu, all_h_csrs, csr_operation, trap_seen, csr_expected_outcome;
    `ifdef UDB_MXLEN_64
    cp_vu_high_half: cross mode_vu, high_half_csrs, csr_operation, trap_seen, illegal_outcome;
    `endif
endgroup

function void h_sample(int hart, int issue, ins_t ins);
    H_cg.sample(ins);
endfunction
