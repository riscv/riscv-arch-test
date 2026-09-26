///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor (H) extension tests executed in HS, VS, U and VU modes.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_H

`include "general/RISCV_coverage_hypervisor.svh"

// Accesses of each CSR test: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
`define H_CSRACCESSES \
    csraccesses : coverpoint ins.current.insn { \
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); \
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); \
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); \
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); \
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); \
    }

// Machine-level H-extension CSRs
`define H_MCSRS \
    bins mtval2 = {CSR_MTVAL2}; \
    bins mtinst = {CSR_MTINST};

// HS and VS H-extension CSRs (keep in sync with HCommon.py)
`define H_HSVSCSRS \
    bins hstatus    = {CSR_HSTATUS}; \
    bins hedeleg    = {CSR_HEDELEG}; \
    bins hideleg    = {CSR_HIDELEG}; \
    bins hie        = {CSR_HIE}; \
    bins hcounteren = {CSR_HCOUNTEREN}; \
    bins hgeie      = {CSR_HGEIE}; \
    bins henvcfg    = {CSR_HENVCFG}; \
    bins htval      = {CSR_HTVAL}; \
    bins hip        = {CSR_HIP}; \
    bins hvip       = {CSR_HVIP}; \
    bins htinst     = {CSR_HTINST}; \
    bins hgatp      = {CSR_HGATP}; \
    bins hgeip      = {CSR_HGEIP}; \
    bins vsstatus   = {CSR_VSSTATUS}; \
    bins vsie       = {CSR_VSIE}; \
    bins vstval     = {CSR_VSTVAL}; \
    bins vsip       = {CSR_VSIP}; \
    bins vstvec     = {CSR_VSTVEC}; \
    bins vsscratch  = {CSR_VSSCRATCH}; \
    bins vsepc      = {CSR_VSEPC}; \
    bins vscause    = {CSR_VSCAUSE}; \
    bins vsatp      = {CSR_VSATP};

// High halves of H CSRs, which are illegal on RV64
`define H_UPPERCSRS \
    bins hedelegh    = {CSR_HEDELEGH}; \
    bins htimedeltah = {CSR_HTIMEDELTAH}; \
    bins henvcfgh    = {CSR_HENVCFGH}; \
    bins vstimecmph  = {CSR_VSTIMECMPH};

// S CSRs with VS replicas, apart from satp
`define H_SREPLICATED \
    bins sstatus  = {CSR_SSTATUS}; \
    bins sie      = {CSR_SIE}; \
    bins stvec    = {CSR_STVEC}; \
    bins sscratch = {CSR_SSCRATCH}; \
    bins sepc     = {CSR_SEPC}; \
    bins scause   = {CSR_SCAUSE}; \
    bins stval    = {CSR_STVAL}; \
    bins sip      = {CSR_SIP};

covergroup H_hscsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `H_CSRACCESSES
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
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // HS and VS H-extension CSRs accessed and walked without masked writes
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
    mcsrname : coverpoint ins.current.insn[31:20] {
        `H_MCSRS
    }

    cp_hcsr_access:         cross priv_mode_hs, hcsrname, csraccesses;
    cp_hcsr_access_zero:    cross priv_mode_hs, hcsrname_zero, csraccesses;
    cp_hcsr_access_masked:  cross priv_mode_hs, hcsrname_masked, csraccesses_masked;
    cp_hcsr_access_ro:      cross priv_mode_hs, hgeip, csraccesses;
    cp_hcsr_inaccessible:   cross priv_mode_hs, mcsrname, csraccesses;
    cp_hcsrwalk:            cross priv_mode_hs, hcsrname, csrop, walking_ones;
    // Keep the lists below in sync with the masks in HCommon.py
    cp_hcsrwalk_masked:     cross priv_mode_hs, hcsrname_masked, csrop, walking_ones {
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
    cp_atpwalk1:            cross priv_mode_hs, csrrw, atpname, atp_walk1;
    cp_atpwalk0:            cross priv_mode_hs, csrrw, atpname, atp_walk0;

    // Read an S CSR in HS-mode right after writing its VS replica
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
    cp_replica:             cross priv_mode_hs, csrw_prev, csrr, replica_pair;

    // hstatus.VGEIN holds 0 through GEILEN
    hstatus : coverpoint ins.current.insn[31:20] {
        bins hstatus = {CSR_HSTATUS};
    }
    vgein : coverpoint ins.current.rs1_val[17:12] {
        bins zero      = {0};
        `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
            bins one       = {1};
            bins geilen_m1 = {`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS - 1};
            bins geilen    = {`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS};
        `endif
    }
    cp_hstatus_vgein:       cross priv_mode_hs, csrrw, hstatus, vgein;

    // vscause holds each exception and interrupt code
    vscause : coverpoint ins.current.insn[31:20] {
        bins vscause = {CSR_VSCAUSE};
    }
    vscause_interrupt : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins interrupt = {1};
    }
    vscause_exception : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
        bins exception = {0};
    }
    vscause_exception_values : coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        bins b_0_instruction_address_misaligned = {0};
        bins b_1_instruction_address_fault = {1};
        bins b_2_illegal_instruction = {2};
        bins b_3_breakpoint = {3};
        bins b_4_load_address_misaligned = {4};
        bins b_5_load_access_fault = {5};
        bins b_6_store_address_misaligned = {6};
        bins b_7_store_access_fault = {7};
        bins b_8_ecall_u = {8};
        bins b_9_ecall_s = {9};
        bins b_12_instruction_page_fault = {12};
        bins b_13_load_page_fault = {13};
        bins b_15_store_page_fault = {15};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            // vscause must hold exception codes 0-31
            bins b_10_ecall_vs = {10};
            bins b_11_ecall_m = {11};
            bins b_14_reserved = {14};
            bins b_16_double_trap = {16};
            bins b_17_reserved = {17};
            bins b_18_software_check = {18};
            bins b_19_hardware_error = {19};
            bins b_20_instr_guest_page_fault = {20};
            bins b_21_load_guest_page_fault = {21};
            bins b_22_virtual_instruction = {22};
            bins b_23_store_guest_page_fault = {23};
            bins b_31_24_custom[] = {[31:24]};
        `endif
    }
    vscause_interrupt_values : coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        bins b_1_supervisor_software = {1};
        bins b_3_machine_software = {3};
        bins b_5_supervisor_timer = {5};
        bins b_7_machine_timer = {7};
        bins b_9_supervisor_external = {9};
        bins b_11_machine_external = {11};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            bins b_0_reserved = {0};
            bins b_2_vs_software = {2};
            bins b_4_reserved = {4};
            bins b_6_vs_timer = {6};
            bins b_8_reserved = {8};
            bins b_10_vs_external = {10};
            bins b_12_supervisor_guest_external = {12};
            bins b_13_counter_overflow = {13};
            bins b_14_reserved = {14};
            bins b_15_reserved = {15};
            bins b_31_16_custom[] = {[31:16]};
        `endif
    }
    cp_vscause_write_exception: cross priv_mode_hs, csrrw, vscause, vscause_exception_values, vscause_exception;
    cp_vscause_write_interrupt: cross priv_mode_hs, csrrw, vscause, vscause_interrupt_values, vscause_interrupt;
endgroup

covergroup H_vscsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `H_CSRACCESSES
    mcsrname : coverpoint ins.current.insn[31:20] {
        `H_MCSRS
    }
    hsvscsrname : coverpoint ins.current.insn[31:20] {
        `H_HSVSCSRS
        `ifdef ZICNTR_SUPPORTED
            bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        `ifdef SSTC_SUPPORTED
            bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins hedelegh = {CSR_HEDELEGH};
            `endif
            `ifdef ZICNTR_SUPPORTED
                bins htimedeltah = {CSR_HTIMEDELTAH};
            `endif
            bins henvcfgh = {CSR_HENVCFGH};
            `ifdef SSTC_SUPPORTED
                bins vstimecmph = {CSR_VSTIMECMPH};
            `endif
        `endif
    }
    cp_hcsr_inaccessible:            cross priv_mode_vs, mcsrname, csraccesses;
    cp_hcsr_virtualinstructionfault: cross priv_mode_vs, hsvscsrname, csraccesses;
    `ifdef UDB_MXLEN_64
        uppercsrname : coverpoint ins.current.insn[31:20] {
            `H_UPPERCSRS
        }
        cp_illegalupper:             cross priv_mode_vs, uppercsrname, csraccesses;
    `endif

    // In VS-mode, S CSR names access the VS replicas
    csrw : coverpoint ins.current.insn {
        wildcard bins csrw = {CSRW};
    }
    sreplicated : coverpoint ins.current.insn[31:20] {
        `H_SREPLICATED
        `ifdef H_REPLICA_SATP
            bins satp = {CSR_SATP};
        `endif
    }
    cp_replica:             cross priv_mode_vs, csrw, sreplicated;

    // S CSRs without VS replicas are accessed normally
    snonreplicated : coverpoint ins.current.insn[31:20] {
        bins scounteren = {CSR_SCOUNTEREN};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            bins senvcfg = {CSR_SENVCFG};
        `endif
        `ifdef SSCCFG_SUPPORTED
            bins scountinhibit = {CSR_SCOUNTINHIBIT};
        `endif
    }
    cp_nonreplica:          cross priv_mode_vs, snonreplicated, csraccesses;

    // vsstatus.SD is read-only and summarizes FS, VS and XS
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    sstatus : coverpoint ins.current.insn[31:20] {
        bins sstatus = {CSR_SSTATUS};
    }
    sstatus_sd : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
    }
    sstatus_fs : coverpoint ins.current.rs1_val[14:13] {
    }
    sstatus_xs : coverpoint ins.current.rs1_val[16:15] {
    }
    sstatus_vs : coverpoint ins.current.rs1_val[10:9] {
    }
    cp_vsstatus_sd_write:   cross priv_mode_vs, csrrw, sstatus, sstatus_sd, sstatus_fs, sstatus_xs, sstatus_vs;
endgroup

// Accesses from U-mode and VU-mode to every H CSR and every S CSR
covergroup H_ucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `H_CSRACCESSES
    mcsrname : coverpoint ins.current.insn[31:20] {
        `H_MCSRS
    }
    hsvscsrname : coverpoint ins.current.insn[31:20] {
        `H_HSVSCSRS
        `ifdef ZICNTR_SUPPORTED
            bins htimedelta = {CSR_HTIMEDELTA};
        `endif
        `ifdef SSTC_SUPPORTED
            bins vstimecmp = {CSR_VSTIMECMP};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins hedelegh = {CSR_HEDELEGH};
            `endif
            `ifdef ZICNTR_SUPPORTED
                bins htimedeltah = {CSR_HTIMEDELTAH};
            `endif
            bins henvcfgh = {CSR_HENVCFGH};
            `ifdef SSTC_SUPPORTED
                bins vstimecmph = {CSR_VSTIMECMPH};
            `endif
        `endif
    }
    snames : coverpoint ins.current.insn[31:20] {
        `H_SREPLICATED
        bins satp       = {CSR_SATP};
        bins scounteren = {CSR_SCOUNTEREN};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            bins senvcfg = {CSR_SENVCFG};
        `endif
        `ifdef SSCCFG_SUPPORTED
            bins scountinhibit = {CSR_SCOUNTINHIBIT};
        `endif
    }
    // Machine-level H CSRs raise illegal instruction in U-mode and VU-mode
    cp_hcsr_inaccessible:            cross priv_mode_u_vu, mcsrname, csraccesses;
    // HS and VS H CSRs raise illegal instruction in U-mode and virtual instruction in VU-mode
    cp_hcsr_inaccessible_u:          cross priv_mode_u, hsvscsrname, csraccesses;
    cp_hcsr_virtualinstructionfault: cross priv_mode_vu, hsvscsrname, csraccesses;
    // S CSRs raise illegal instruction in U-mode and virtual instruction in VU-mode
    cp_scsr:                         cross priv_mode_u_vu, snames, csraccesses;
    `ifdef UDB_MXLEN_64
        uppercsrname : coverpoint ins.current.insn[31:20] {
            `H_UPPERCSRS
        }
        cp_illegalupper:             cross priv_mode_u_vu, uppercsrname, csraccesses;
    `endif
endgroup

covergroup H_inst_cg with function sample(ins_t ins);
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
        // hlv, hlvx and hsv from HS-mode and from U-mode with hstatus.HU = 1
        cp_hlv:  cross priv_mode_s_u, hlv;
        cp_hlvx: cross priv_mode_s_u, hlvx;
        cp_hsv:  cross priv_mode_s_u, hsv;

        hlv_hsv : coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare  = {0};
            bins paged = {[1:15]};
        }
        guest_page_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0]} {
            bins load_store = {6'b110101, 6'b110111};
        }
        // Guest-page faults on the final translation (vsatp Bare) and on an implicit VS-stage access
        cp_guest_page_fault: cross priv_mode_hs, hlv_hsv, vsatp_mode, guest_page_fault;
    `endif

    mret : coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    sret : coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    cp_mret_illegal:  cross priv_mode_hs_vs_vu, mret;
    cp_sret_illegal:  cross priv_mode_vu, sret;

    // In VS-mode the trace reports vsstatus as sstatus
    old_spp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp") {
        bins u = {0};
        bins s = {1};
    }
    old_spie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie") {
        bins off = {0};
        bins on  = {1};
    }
    old_spv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") {
        bins off = {0};
        bins on  = {1};
    }
    old_vtsr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr") {
        bins off = {0};
        bins on  = {1};
    }
    cp_sret_hs:  cross priv_mode_hs, sret, old_spp, old_spie, old_spv;
    cp_sret_vs:  cross priv_mode_vs, sret, old_spp, old_spie, old_vtsr;
endgroup

function void h_sample(int hart, int issue, ins_t ins);
    H_hscsr_cg.sample(ins);
    H_vscsr_cg.sample(ins);
    H_ucsr_cg.sample(ins);
    H_inst_cg.sample(ins);
endfunction
