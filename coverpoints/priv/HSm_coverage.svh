///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor (H) extension tests executed in M-mode, or that need M-mode to take their traps.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_HSM

`include "general/RISCV_coverage_hypervisor.svh"

covergroup HSm_mcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }
    csraccesses_masked : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val != 0); // csrc mask
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val == 0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val != 0); // csrw mask
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val != 0); // csrs mask
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val == 0); // csrr
    }
    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // Machine, HS and VS H-extension CSRs accessed and walked without masked writes.  Keep in sync with HCommon.py.
    hcsrname : coverpoint ins.current.insn[31:20] {
        bins hedeleg    = {CSR_HEDELEG};
        bins hideleg    = {CSR_HIDELEG};
        bins hie        = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie      = {CSR_HGEIE};
        bins hip        = {CSR_HIP};
        bins hvip       = {CSR_HVIP};
        `ifdef ZICNTR_SUPPORTED
            bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        bins vsstatus   = {CSR_VSSTATUS};
        bins vsie       = {CSR_VSIE};
        bins vstval     = {CSR_VSTVAL};
        bins vsip       = {CSR_VSIP};
        bins vstvec     = {CSR_VSTVEC};
        bins vsscratch  = {CSR_VSSCRATCH};
        bins vsepc      = {CSR_VSEPC};
        `ifdef SSTC_SUPPORTED
            bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef ZICNTR_SUPPORTED
                bins htimedeltah = {CSR_HTIMEDELTAH};
            `endif
            `ifdef SSTC_SUPPORTED
                bins vstimecmph = {CSR_VSTIMECMPH};
            `endif
        `endif
    }
    // CSRs that need only hold zero: the readback is checked after writing zero and after clearing every bit
    hcsrname_zero : coverpoint ins.current.insn[31:20] {
        bins mtval2 = {CSR_MTVAL2};
        bins mtinst = {CSR_MTINST};
        bins htval  = {CSR_HTVAL};
        bins htinst = {CSR_HTINST};
        bins hgatp  = {CSR_HGATP};
        bins vsatp  = {CSR_VSATP};
        `ifdef UDB_MXLEN_32
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins hedelegh = {CSR_HEDELEGH};
            `endif
        `endif
    }
    // CSRs whose access and walk tests write only the checked fields
    hcsrname_masked : coverpoint ins.current.insn[31:20] {
        bins hstatus = {CSR_HSTATUS};
        bins henvcfg = {CSR_HENVCFG};
        `ifdef UDB_MXLEN_32
            bins henvcfgh = {CSR_HENVCFGH};
        `endif
    }
    hgeip : coverpoint ins.current.insn[31:20] {
        bins hgeip = {CSR_HGEIP};
    }

    cp_hcsr_access:         cross priv_mode_m, hcsrname, csraccesses;
    cp_hcsr_access_zero:    cross priv_mode_m, hcsrname_zero, csraccesses;
    cp_hcsr_access_masked:  cross priv_mode_m, hcsrname_masked, csraccesses_masked;
    cp_hcsr_access_ro:      cross priv_mode_m, hgeip, csraccesses;
    cp_hcsrwalk:            cross priv_mode_m, hcsrname, csrop, walking_ones;
    // Keep the lists below in sync with the masks in HCommon.py
    cp_hcsrwalk_masked:     cross priv_mode_m, hcsrname_masked, csrop, walking_ones {
        ignore_bins hstatus_not_walked = binsof(hcsrname_masked.hstatus) &&
            binsof(walking_ones) intersect {[0:5], [10:19], [23:63]};
        ignore_bins henvcfg_not_walked = binsof(hcsrname_masked.henvcfg) &&
            binsof(walking_ones) intersect {1, [8:31], [34:60]};
        `ifdef UDB_MXLEN_32
            ignore_bins henvcfgh_not_walked = binsof(hcsrname_masked.henvcfgh) &&
                binsof(walking_ones) intersect {[2:28]};
        `endif
    }

    // hgatp and vsatp: walk a 1 and a 0 through the non-MODE bits with a legal MODE
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    atpname : coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39X4_TRANSLATION
                bins hgatp = {CSR_HGATP};
            `endif
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins vsatp = {CSR_VSATP};
            `endif
        `else
            `ifdef UDB_SV32X4_TRANSLATION
                bins hgatp = {CSR_HGATP};
            `endif
            `ifdef UDB_SV32_VSMODE_TRANSLATION
                bins vsatp = {CSR_VSATP};
            `endif
        `endif
    }
    `ifdef UDB_MXLEN_64
        atp_walk1 : coverpoint $clog2(ins.current.rs1_val[59:0])
            iff (ins.current.rs1_val[63:60] == 8 && $onehot(ins.current.rs1_val[59:0])) {
            bins b[] = {[0:59]};
        }
        atp_walk0 : coverpoint $clog2(~ins.current.rs1_val[59:0])
            iff (ins.current.rs1_val[63:60] == 8 && $onehot(~ins.current.rs1_val[59:0])) {
            bins b[] = {[0:59]};
        }
    `else
        atp_walk1 : coverpoint $clog2(ins.current.rs1_val[30:0])
            iff (ins.current.rs1_val[31] && $onehot(ins.current.rs1_val[30:0])) {
            bins b[] = {[0:30]};
        }
        atp_walk0 : coverpoint $clog2(~ins.current.rs1_val[30:0])
            iff (ins.current.rs1_val[31] && $onehot(~ins.current.rs1_val[30:0])) {
            bins b[] = {[0:30]};
        }
    `endif
    cp_atpwalk1:            cross priv_mode_m, csrrw, atpname, atp_walk1;
    cp_atpwalk0:            cross priv_mode_m, csrrw, atpname, atp_walk0;

    // Read an S CSR right after writing its VS replica
    csrw_prev : coverpoint ins.prev.insn {
        wildcard bins csrw = {CSRW};
    }
    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    replica_pair : coverpoint {ins.prev.insn[31:20], ins.current.insn[31:20]} {
        bins sstatus  = {{CSR_VSSTATUS, CSR_SSTATUS}};
        bins sie      = {{CSR_VSIE, CSR_SIE}};
        bins stvec    = {{CSR_VSTVEC, CSR_STVEC}};
        bins sscratch = {{CSR_VSSCRATCH, CSR_SSCRATCH}};
        bins sepc     = {{CSR_VSEPC, CSR_SEPC}};
        bins scause   = {{CSR_VSCAUSE, CSR_SCAUSE}};
        bins stval    = {{CSR_VSTVAL, CSR_STVAL}};
        bins sip      = {{CSR_VSIP, CSR_SIP}};
        `ifdef H_REPLICA_SATP
            bins satp = {{CSR_VSATP, CSR_SATP}};
        `endif
    }
    cp_replica:             cross priv_mode_m, csrw_prev, csrr, replica_pair;

    // mtval must not be read-only zero with H
    mtval : coverpoint ins.current.insn[31:20] {
        bins mtval = {CSR_MTVAL};
    }
    rs1_ones : coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }
    cp_mtvala:              cross priv_mode_m, csrrw, mtval, rs1_ones;
endgroup

covergroup HSm_tvm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mstatus_tvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins off = {0};
        bins on  = {1};
    }
    hstatus_vtvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }
    csr_rw : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }
    satp_hgatp : coverpoint ins.current.insn[31:20] {
        bins satp  = {CSR_SATP};
        bins hgatp = {CSR_HGATP};
    }
    satp : coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }
    hfence : coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    sfence : coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }

    cp_tvm_hs:  cross priv_mode_hs, satp_hgatp, csr_rw, mstatus_tvm;
    cp_tvm_vs:  cross priv_mode_vs, satp, csr_rw, mstatus_tvm, hstatus_vtvm;
    cp_hfence:  cross priv_mode_m_hs_vs_u_vu, hfence, mstatus_tvm, hstatus_vtvm;
    cp_sfence:  cross priv_mode_m_hs_vs_u_vu, sfence, mstatus_tvm, hstatus_vtvm;
endgroup

covergroup HSm_inst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef H_TWO_STAGE
        hlv : coverpoint ins.current.insn {
            wildcard bins hlv_b  = {HLV_B};
            wildcard bins hlv_bu = {HLV_BU};
            wildcard bins hlv_h  = {HLV_H};
            wildcard bins hlv_hu = {HLV_HU};
            wildcard bins hlv_w  = {HLV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hlv_wu = {HLV_WU};
                wildcard bins hlv_d  = {HLV_D};
            `endif
        }
        hlvx : coverpoint ins.current.insn {
            wildcard bins hlvx_hu = {HLVX_HU};
            wildcard bins hlvx_wu = {HLVX_WU};
        }
        hsv : coverpoint ins.current.insn {
            wildcard bins hsv_b = {HSV_B};
            wildcard bins hsv_h = {HSV_H};
            wildcard bins hsv_w = {HSV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hsv_d = {HSV_D};
            `endif
        }
        cp_hlv:  cross priv_mode_m, hlv;
        cp_hlvx: cross priv_mode_m, hlvx;
        cp_hsv:  cross priv_mode_m, hsv;

        hlv_hsv : coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare  = {0};
            bins paged = {[1:15]};
        }
        guest_page_fault : coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
            bins load_store = {6'b110101, 6'b110111};
        }
        // Guest-page faults on the final translation (vsatp Bare) and on an implicit VS-stage access
        cp_guest_page_fault: cross priv_mode_m, hlv_hsv, vsatp_mode, guest_page_fault;
    `endif

    mret : coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    sret : coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    old_mpp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins u = {0};
        bins s = {1};
        bins m = {3};
    }
    `ifdef UDB_MXLEN_64
        old_mpv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv") {
    `else
        old_mpv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv") {
    `endif
        bins off = {0};
        bins on  = {1};
    }
    old_mpie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie") {
        bins off = {0};
        bins on  = {1};
    }
    old_spp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spp") {
        bins u = {0};
        bins s = {1};
    }
    old_spie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spie") {
        bins off = {0};
        bins on  = {1};
    }
    old_spv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") {
        bins off = {0};
        bins on  = {1};
    }

    cp_mret_m:  cross priv_mode_m, mret, old_mpp, old_mpv, old_mpie;
    cp_sret_m:  cross priv_mode_m, sret, old_spp, old_spv, old_spie;
endgroup

function void hsm_sample(int hart, int issue, ins_t ins);
    HSm_mcsr_cg.sample(ins);
    HSm_tvm_cg.sample(ins);
    HSm_inst_cg.sample(ins);
endfunction
