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

covergroup H_hscsr_cg with function sample(ins_t ins);
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
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                bins hedelegh = {CSR_HEDELEGH}; // every bit is reserved, so the walk checks that each reads zero
            `endif
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
    cp_hcsr_access:         cross priv_mode_hs, hcsrname, csraccesses;
    cp_hcsr_access_zero:    cross priv_mode_hs, hcsrname_zero, csraccesses;
    cp_hcsr_access_masked:  cross priv_mode_hs, hcsrname_masked, csraccesses_masked;
    cp_hcsr_access_ro:      cross priv_mode_hs, hgeip, csraccesses;
    cp_hcsrwalk:            cross priv_mode_hs, hcsrname, csrop, walking_ones {
        // vsepc and vstval may legalize invalid addresses, so they are walked with valid addresses instead
        ignore_bins vaddr = binsof(hcsrname.vsepc) || binsof(hcsrname.vstval);
    }
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

    // vsepc and vstval hold every address that sepc and stval hold: the current pc, an address in scratch, and each
    // canonical virtual address with one bit walked.  vsepc bit 0 is always 0, and bit 1 is 0 unless Zca allows
    // 2-byte instruction alignment.
    vsepc : coverpoint ins.current.insn[31:20] {
        bins vsepc = {CSR_VSEPC};
    }
    vstval : coverpoint ins.current.insn[31:20] {
        bins vstval = {CSR_VSTVAL};
    }
    xaddr_pc : coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch : coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    cp_vsepc_vaddr_pc:       cross priv_mode_hs, csrrw, vsepc, xaddr_pc;
    cp_vsepc_vaddr_scratch:  cross priv_mode_hs, csrrw, vsepc, xaddr_scratch;
    cp_vstval_vaddr_pc:      cross priv_mode_hs, csrrw, vstval, xaddr_pc;
    cp_vstval_vaddr_scratch: cross priv_mode_hs, csrrw, vstval, xaddr_scratch;
    `ifdef H_VADDR_WALK_MSB
        vaddr_walk1 : coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:`H_VADDR_WALK_MSB] };
        }
        vaddr_walk0 : coverpoint $clog2(~ins.current.rs1_val) iff ($onehot(~ins.current.rs1_val)) {
            bins b_0[] = { [0:`H_VADDR_WALK_MSB] };
        }
        cp_vsepc_vaddr_walk1:    cross priv_mode_hs, csrrw, vsepc, vaddr_walk1;
        cp_vsepc_vaddr_walk0:    cross priv_mode_hs, csrrw, vsepc, vaddr_walk0;
        cp_vstval_vaddr_walk1:   cross priv_mode_hs, csrrw, vstval, vaddr_walk1;
        cp_vstval_vaddr_walk0:   cross priv_mode_hs, csrrw, vstval, vaddr_walk0;
    `endif
    // vstval must hold 0 and, when the illegal instruction encoding is reported in it, every ILEN-bit value
    vstval_zero : coverpoint ins.current.rs1_val {
        bins zero = {0};
    }
    cp_vstval_zero:          cross priv_mode_hs, csrrw, vstval, vstval_zero;
    `ifdef UDB_REPORT_ENCODING_IN_VSTVAL_ON_ILLEGAL_INSTRUCTION
        vstval_ilen_walk1 : coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [0:31] };
        }
        vstval_ilen_ones : coverpoint ins.current.rs1_val {
            bins ones = {32'hFFFFFFFF};
        }
        cp_vstval_ilen_walk1: cross priv_mode_hs, csrrw, vstval, vstval_ilen_walk1;
        cp_vstval_ilen_ones:  cross priv_mode_hs, csrrw, vstval, vstval_ilen_ones;
    `endif

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
        // satp always supports Sv39 (RV64) or Sv32 (RV32), but vsatp need not
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins satp = {{CSR_VSATP, CSR_SATP}};
            `endif
        `elsif UDB_SV32_VSMODE_TRANSLATION
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

endgroup

// HS-mode writes each exception and interrupt code to vscause, which must hold the codes that scause holds
covergroup H_vscause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
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

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }
    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    nonzerord : coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }

    // Every M-mode CSR number raises illegal instruction in VS-mode, as in S_scsr_cg
    csr_machine : coverpoint ins.current.insn[31:20] {
        bins machine_0[]  = {[12'h300:12'h3FF]};
        bins machine_1a[] = {[12'h700:12'h7A9]};
        // ignore mscontext at 0x7aa, which is accessible from S mode
        bins machine_1b[] = {[12'h7AB:12'h7FF]};
        bins machine_2[]  = {[12'hB00:12'hBFF]};
        bins machine_3[]  = {[12'hF00:12'hFFF]};
    }
    cp_csr_insufficient_priv:        cross priv_mode_vs, csrr, csr_machine, nonzerord;

    // HS and VS H CSRs raise virtual instruction in VS-mode when the access is legal in HS-mode
    hsvscsrname : coverpoint ins.current.insn[31:20] {
        bins hstatus    = {CSR_HSTATUS};
        bins hedeleg    = {CSR_HEDELEG};
        bins hideleg    = {CSR_HIDELEG};
        bins hie        = {CSR_HIE};
        bins hcounteren = {CSR_HCOUNTEREN};
        bins hgeie      = {CSR_HGEIE};
        bins henvcfg    = {CSR_HENVCFG};
        bins htval      = {CSR_HTVAL};
        bins hip        = {CSR_HIP};
        bins hvip       = {CSR_HVIP};
        bins htinst     = {CSR_HTINST};
        bins hgatp      = {CSR_HGATP};
        bins hgeip      = {CSR_HGEIP};
        bins vsstatus   = {CSR_VSSTATUS};
        bins vsie       = {CSR_VSIE};
        bins vstval     = {CSR_VSTVAL};
        bins vsip       = {CSR_VSIP};
        bins vstvec     = {CSR_VSTVEC};
        bins vsscratch  = {CSR_VSSCRATCH};
        bins vsepc      = {CSR_VSEPC};
        bins vscause    = {CSR_VSCAUSE};
        bins vsatp      = {CSR_VSATP};
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
    cp_hcsr_virtualinstructionfault: cross priv_mode_vs, hsvscsrname, csraccesses;
    // The high halves of H CSRs do not exist on RV64, so they raise illegal instruction
    `ifdef UDB_MXLEN_64
        uppercsrname : coverpoint ins.current.insn[31:20] {
            bins hedelegh    = {CSR_HEDELEGH};
            bins htimedeltah = {CSR_HTIMEDELTAH};
            bins henvcfgh    = {CSR_HENVCFGH};
            bins vstimecmph  = {CSR_VSTIMECMPH};
        }
        cp_illegalupper:             cross priv_mode_vs, uppercsrname, csraccesses;
    `endif

    // In VS-mode, S CSR names access the VS replicas
    csrw : coverpoint ins.current.insn {
        wildcard bins csrw = {CSRW};
    }
    sreplicated : coverpoint ins.current.insn[31:20] {
        bins sstatus  = {CSR_SSTATUS};
        bins sie      = {CSR_SIE};
        bins stvec    = {CSR_STVEC};
        bins sscratch = {CSR_SSCRATCH};
        bins sepc     = {CSR_SEPC};
        bins scause   = {CSR_SCAUSE};
        bins stval    = {CSR_STVAL};
        bins sip      = {CSR_SIP};
        // satp always supports Sv39 (RV64) or Sv32 (RV32), but vsatp need not
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                bins satp = {CSR_SATP};
            `endif
        `elsif UDB_SV32_VSMODE_TRANSLATION
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
    }
    cp_nonreplica:          cross priv_mode_vs, snonreplicated, csraccesses;

    // scountinhibit raises illegal instruction with menvcfg.CDE = 0 and virtual instruction with CDE = 1
    `ifdef SSCCFG_SUPPORTED
        scountinhibit : coverpoint ins.current.insn[31:20] {
            bins scountinhibit = {CSR_SCOUNTINHIBIT};
        }
        `ifdef UDB_MXLEN_64
            menvcfg_cde : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "cde")[0] {
            }
        `else
            menvcfg_cde : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "cde")[0] {
            }
        `endif
        cp_scountinhibit_vs:    cross priv_mode_vs, scountinhibit, csraccesses, menvcfg_cde;
    `endif
endgroup

// vsstatus.SD is read-only and summarizes FS, VS and XS.  VS-mode writes it through sstatus, as S_sstatus_cg.
covergroup H_vsstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cp_vsstatus_sd : coverpoint ins.current.rs1_val[`UDB_MXLEN-1] {
    }
    cp_vsstatus_fs : coverpoint ins.current.rs1_val[14:13] {
    }
    cp_vsstatus_vs : coverpoint ins.current.rs1_val[10:9] {
    }
    cp_vsstatus_xs : coverpoint ins.current.rs1_val[16:15] {
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    sstatus : coverpoint ins.current.insn[31:20] {
        bins sstatus = {CSR_SSTATUS};
    }
    cp_vsstatus_sd_write: cross priv_mode_vs, csrrw, sstatus, cp_vsstatus_sd, cp_vsstatus_fs, cp_vsstatus_vs, cp_vsstatus_xs;
endgroup

// Accesses from VU-mode, as U_ucsr_cg from U-mode: every CSR number that is not a user CSR raises illegal or virtual
// instruction, and so does every write to a user read-only CSR
covergroup H_vucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csr_nonuser: coverpoint ins.current.insn[31:20]  {
        bins nonuser_0[]  = {[12'h100:12'h3FF]};
        bins nonuser_1a[] = {[12'h500:12'h7A9]};
        // ignore mscontext at 0x7aa, which may be accessible from S mode
        bins nonuser_1b[] = {[12'h7AB:12'h7FF]};
        bins nonuser_2[] = {[12'h900:12'hBFF]};
        bins nonuser_3[] = {[12'hD00:12'hFFF]};
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    csrw: coverpoint ins.current.insn  {
        wildcard bins csrw = {CSRRW};
    }
    csr_uro: coverpoint ins.current.insn[31:20]  {
        bins sro[] = {[12'hC00:12'hCFF]};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }

    cp_csr_insufficient_priv: cross priv_mode_vu, csrr, csr_nonuser, nonzerord;
    cp_csr_ro:                cross priv_mode_vu, csrw, csr_uro;
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
        // hlv, hlvx and hsv from HS-mode and from U-mode with hstatus.HU = 1, which U-mode needs to execute them
        hstatus_hu : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu")[0] {
            bins on = {1};
        }
        cp_hlv:  cross priv_mode_s_u, hlv, hstatus_hu;
        cp_hlvx: cross priv_mode_s_u, hlvx, hstatus_hu;
        cp_hsv:  cross priv_mode_s_u, hsv, hstatus_hu;

        hlv_hsv : coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare  = {0};
            bins paged = {[1:15]};
        }
        // The instruction traps to HS-mode with a load (21) or store (23) guest-page fault.  csr_wb shows that this
        // instruction wrote scause, so the scause of an earlier trap does not count.
        guest_page_fault : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code")
                           iff (ins.current.csr_wb[CSR_SCAUSE]) {
            bins load_store = {21, 23};
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

    // hfence.vvma and hfence.gvma execute in HS-mode and raise virtual instruction in VS-mode and VU-mode and illegal
    // instruction in U-mode, as S_sprivinst_cg executes sfence.vma.  Sm_H_tvm_cg/cp_hfence adds mstatus.TVM and
    // hstatus.VTVM, and SvH checks the translations they remove.
    hfence : coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    cp_hfence:        cross priv_mode_hs_vs_u_vu, hfence;

    // hstatus.VTVM = 1 makes sfence.vma and satp accesses raise virtual instruction in VS-mode, but does not trap
    // hfence.vvma in HS-mode.  mstatus.TVM needs M-mode, so it is in Sm_H.
    hstatus_vtvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm")[0] {
    }
    sfence_vma : coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }
    hfence_vvma : coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
    }
    satp_access : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }
    satp : coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }
    cp_vtvm_sfence:      cross priv_mode_vs, sfence_vma, hstatus_vtvm;
    cp_vtvm_satp:        cross priv_mode_vs, satp_access, satp, hstatus_vtvm;
    cp_vtvm_hfence_vvma: cross priv_mode_hs, hfence_vvma, hstatus_vtvm;

    // In VS-mode the trace reports vsstatus as sstatus
    old_spp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
    }
    old_spie : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spie")[0] {
    }
    old_spv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv")[0] {
    }
    old_vtsr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr")[0] {
    }
    cp_sret_hs:  cross priv_mode_hs, sret, old_spp, old_spie, old_spv;
    cp_sret_vs:  cross priv_mode_vs, sret, old_spp, old_spie, old_vtsr;
endgroup

// Counter access and htimedelta in HS, VS, U and VU modes.
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
`ifdef ZICNTR_SUPPORTED
covergroup H_Zicntr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // The counter accessed: one that exists and whose mcounteren, hcounteren and scounteren bits are writable
    counter: coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MCOUNTENABLE_EN_0 `ifdef UDB_HCOUNTENABLE_EN_0 `ifdef UDB_SCOUNTENABLE_EN_0
            bins cycle_csr = {CSR_CYCLE};
            `ifdef UDB_MXLEN_32
                bins cycleh_csr = {CSR_CYCLEH};
            `endif
        `endif `endif `endif
        `ifdef UDB_MCOUNTENABLE_EN_1 `ifdef UDB_HCOUNTENABLE_EN_1 `ifdef UDB_SCOUNTENABLE_EN_1
            bins time_csr = {CSR_TIME};
            `ifdef UDB_MXLEN_32
                bins timeh_csr = {CSR_TIMEH};
            `endif
        `endif `endif `endif
        `ifdef UDB_MCOUNTENABLE_EN_2 `ifdef UDB_HCOUNTENABLE_EN_2 `ifdef UDB_SCOUNTENABLE_EN_2
            bins instret_csr = {CSR_INSTRET};
            `ifdef UDB_MXLEN_32
                bins instreth_csr = {CSR_INSTRETH};
            `endif
        `endif `endif `endif
        `ifdef ZIHPM_SUPPORTED
            `ifdef UDB_HPM_COUNTER_EN_3 `ifdef UDB_MCOUNTENABLE_EN_3 `ifdef UDB_HCOUNTENABLE_EN_3 `ifdef UDB_SCOUNTENABLE_EN_3
                bins hpmcounter3_csr = {CSR_HPMCOUNTER3};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter3h_csr = {CSR_HPMCOUNTER3H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_4 `ifdef UDB_MCOUNTENABLE_EN_4 `ifdef UDB_HCOUNTENABLE_EN_4 `ifdef UDB_SCOUNTENABLE_EN_4
                bins hpmcounter4_csr = {CSR_HPMCOUNTER4};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter4h_csr = {CSR_HPMCOUNTER4H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_5 `ifdef UDB_MCOUNTENABLE_EN_5 `ifdef UDB_HCOUNTENABLE_EN_5 `ifdef UDB_SCOUNTENABLE_EN_5
                bins hpmcounter5_csr = {CSR_HPMCOUNTER5};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter5h_csr = {CSR_HPMCOUNTER5H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_6 `ifdef UDB_MCOUNTENABLE_EN_6 `ifdef UDB_HCOUNTENABLE_EN_6 `ifdef UDB_SCOUNTENABLE_EN_6
                bins hpmcounter6_csr = {CSR_HPMCOUNTER6};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter6h_csr = {CSR_HPMCOUNTER6H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_7 `ifdef UDB_MCOUNTENABLE_EN_7 `ifdef UDB_HCOUNTENABLE_EN_7 `ifdef UDB_SCOUNTENABLE_EN_7
                bins hpmcounter7_csr = {CSR_HPMCOUNTER7};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter7h_csr = {CSR_HPMCOUNTER7H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_8 `ifdef UDB_MCOUNTENABLE_EN_8 `ifdef UDB_HCOUNTENABLE_EN_8 `ifdef UDB_SCOUNTENABLE_EN_8
                bins hpmcounter8_csr = {CSR_HPMCOUNTER8};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter8h_csr = {CSR_HPMCOUNTER8H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_9 `ifdef UDB_MCOUNTENABLE_EN_9 `ifdef UDB_HCOUNTENABLE_EN_9 `ifdef UDB_SCOUNTENABLE_EN_9
                bins hpmcounter9_csr = {CSR_HPMCOUNTER9};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter9h_csr = {CSR_HPMCOUNTER9H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_10 `ifdef UDB_MCOUNTENABLE_EN_10 `ifdef UDB_HCOUNTENABLE_EN_10 `ifdef UDB_SCOUNTENABLE_EN_10
                bins hpmcounter10_csr = {CSR_HPMCOUNTER10};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter10h_csr = {CSR_HPMCOUNTER10H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_11 `ifdef UDB_MCOUNTENABLE_EN_11 `ifdef UDB_HCOUNTENABLE_EN_11 `ifdef UDB_SCOUNTENABLE_EN_11
                bins hpmcounter11_csr = {CSR_HPMCOUNTER11};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter11h_csr = {CSR_HPMCOUNTER11H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_12 `ifdef UDB_MCOUNTENABLE_EN_12 `ifdef UDB_HCOUNTENABLE_EN_12 `ifdef UDB_SCOUNTENABLE_EN_12
                bins hpmcounter12_csr = {CSR_HPMCOUNTER12};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter12h_csr = {CSR_HPMCOUNTER12H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_13 `ifdef UDB_MCOUNTENABLE_EN_13 `ifdef UDB_HCOUNTENABLE_EN_13 `ifdef UDB_SCOUNTENABLE_EN_13
                bins hpmcounter13_csr = {CSR_HPMCOUNTER13};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter13h_csr = {CSR_HPMCOUNTER13H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_14 `ifdef UDB_MCOUNTENABLE_EN_14 `ifdef UDB_HCOUNTENABLE_EN_14 `ifdef UDB_SCOUNTENABLE_EN_14
                bins hpmcounter14_csr = {CSR_HPMCOUNTER14};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter14h_csr = {CSR_HPMCOUNTER14H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_15 `ifdef UDB_MCOUNTENABLE_EN_15 `ifdef UDB_HCOUNTENABLE_EN_15 `ifdef UDB_SCOUNTENABLE_EN_15
                bins hpmcounter15_csr = {CSR_HPMCOUNTER15};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter15h_csr = {CSR_HPMCOUNTER15H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_16 `ifdef UDB_MCOUNTENABLE_EN_16 `ifdef UDB_HCOUNTENABLE_EN_16 `ifdef UDB_SCOUNTENABLE_EN_16
                bins hpmcounter16_csr = {CSR_HPMCOUNTER16};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter16h_csr = {CSR_HPMCOUNTER16H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_17 `ifdef UDB_MCOUNTENABLE_EN_17 `ifdef UDB_HCOUNTENABLE_EN_17 `ifdef UDB_SCOUNTENABLE_EN_17
                bins hpmcounter17_csr = {CSR_HPMCOUNTER17};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter17h_csr = {CSR_HPMCOUNTER17H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_18 `ifdef UDB_MCOUNTENABLE_EN_18 `ifdef UDB_HCOUNTENABLE_EN_18 `ifdef UDB_SCOUNTENABLE_EN_18
                bins hpmcounter18_csr = {CSR_HPMCOUNTER18};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter18h_csr = {CSR_HPMCOUNTER18H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_19 `ifdef UDB_MCOUNTENABLE_EN_19 `ifdef UDB_HCOUNTENABLE_EN_19 `ifdef UDB_SCOUNTENABLE_EN_19
                bins hpmcounter19_csr = {CSR_HPMCOUNTER19};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter19h_csr = {CSR_HPMCOUNTER19H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_20 `ifdef UDB_MCOUNTENABLE_EN_20 `ifdef UDB_HCOUNTENABLE_EN_20 `ifdef UDB_SCOUNTENABLE_EN_20
                bins hpmcounter20_csr = {CSR_HPMCOUNTER20};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter20h_csr = {CSR_HPMCOUNTER20H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_21 `ifdef UDB_MCOUNTENABLE_EN_21 `ifdef UDB_HCOUNTENABLE_EN_21 `ifdef UDB_SCOUNTENABLE_EN_21
                bins hpmcounter21_csr = {CSR_HPMCOUNTER21};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter21h_csr = {CSR_HPMCOUNTER21H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_22 `ifdef UDB_MCOUNTENABLE_EN_22 `ifdef UDB_HCOUNTENABLE_EN_22 `ifdef UDB_SCOUNTENABLE_EN_22
                bins hpmcounter22_csr = {CSR_HPMCOUNTER22};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter22h_csr = {CSR_HPMCOUNTER22H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_23 `ifdef UDB_MCOUNTENABLE_EN_23 `ifdef UDB_HCOUNTENABLE_EN_23 `ifdef UDB_SCOUNTENABLE_EN_23
                bins hpmcounter23_csr = {CSR_HPMCOUNTER23};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter23h_csr = {CSR_HPMCOUNTER23H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_24 `ifdef UDB_MCOUNTENABLE_EN_24 `ifdef UDB_HCOUNTENABLE_EN_24 `ifdef UDB_SCOUNTENABLE_EN_24
                bins hpmcounter24_csr = {CSR_HPMCOUNTER24};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter24h_csr = {CSR_HPMCOUNTER24H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_25 `ifdef UDB_MCOUNTENABLE_EN_25 `ifdef UDB_HCOUNTENABLE_EN_25 `ifdef UDB_SCOUNTENABLE_EN_25
                bins hpmcounter25_csr = {CSR_HPMCOUNTER25};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter25h_csr = {CSR_HPMCOUNTER25H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_26 `ifdef UDB_MCOUNTENABLE_EN_26 `ifdef UDB_HCOUNTENABLE_EN_26 `ifdef UDB_SCOUNTENABLE_EN_26
                bins hpmcounter26_csr = {CSR_HPMCOUNTER26};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter26h_csr = {CSR_HPMCOUNTER26H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_27 `ifdef UDB_MCOUNTENABLE_EN_27 `ifdef UDB_HCOUNTENABLE_EN_27 `ifdef UDB_SCOUNTENABLE_EN_27
                bins hpmcounter27_csr = {CSR_HPMCOUNTER27};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter27h_csr = {CSR_HPMCOUNTER27H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_28 `ifdef UDB_MCOUNTENABLE_EN_28 `ifdef UDB_HCOUNTENABLE_EN_28 `ifdef UDB_SCOUNTENABLE_EN_28
                bins hpmcounter28_csr = {CSR_HPMCOUNTER28};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter28h_csr = {CSR_HPMCOUNTER28H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_29 `ifdef UDB_MCOUNTENABLE_EN_29 `ifdef UDB_HCOUNTENABLE_EN_29 `ifdef UDB_SCOUNTENABLE_EN_29
                bins hpmcounter29_csr = {CSR_HPMCOUNTER29};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter29h_csr = {CSR_HPMCOUNTER29H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_30 `ifdef UDB_MCOUNTENABLE_EN_30 `ifdef UDB_HCOUNTENABLE_EN_30 `ifdef UDB_SCOUNTENABLE_EN_30
                bins hpmcounter30_csr = {CSR_HPMCOUNTER30};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter30h_csr = {CSR_HPMCOUNTER30H};
                `endif
            `endif `endif `endif `endif
            `ifdef UDB_HPM_COUNTER_EN_31 `ifdef UDB_MCOUNTENABLE_EN_31 `ifdef UDB_HCOUNTENABLE_EN_31 `ifdef UDB_SCOUNTENABLE_EN_31
                bins hpmcounter31_csr = {CSR_HPMCOUNTER31};
                `ifdef UDB_MXLEN_32
                    bins hpmcounter31h_csr = {CSR_HPMCOUNTER31H};
                `endif
            `endif `endif `endif `endif
        `endif
    }

    // The enable bit of the accessed counter in each counter-enable register
    mcounteren_bit: coverpoint ins.current.csr[CSR_MCOUNTEREN][ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    hcounteren_bit: coverpoint ins.current.csr[CSR_HCOUNTEREN][ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    scounteren_bit: coverpoint ins.current.csr[CSR_SCOUNTEREN][ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    // The same bits held while another counter-enable register is walked
    mcounteren_one: coverpoint ins.current.csr[CSR_MCOUNTEREN][ins.current.insn[24:20]] {
        bins one = {1};
    }
    hcounteren_one: coverpoint ins.current.csr[CSR_HCOUNTEREN][ins.current.insn[24:20]] {
        bins one = {1};
    }
    hcounteren_zero: coverpoint ins.current.csr[CSR_HCOUNTEREN][ins.current.insn[24:20]] {
        bins zero = {0};
    }
    scounteren_one: coverpoint ins.current.csr[CSR_SCOUNTEREN][ins.current.insn[24:20]] {
        bins one = {1};
    }
    scounteren_zero: coverpoint ins.current.csr[CSR_SCOUNTEREN][ins.current.insn[24:20]] {
        bins zero = {0};
    }

    csraccess: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }

    // htimedelta = {0, 2^30, 2^32-1, 2^60, -1, -2^30, -2^60} while time and timeh are read
    csrr_time: coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRR) {
        bins read_time = {CSR_TIME};
        `ifdef UDB_MXLEN_32
            bins read_timeh = {CSR_TIMEH};
        `endif
    }
    `ifdef UDB_MXLEN_64
        htimedelta: coverpoint ins.current.csr[CSR_HTIMEDELTA] {
    `else
        htimedelta: coverpoint {ins.current.csr[CSR_HTIMEDELTAH][31:0], ins.current.csr[CSR_HTIMEDELTA][31:0]} {
    `endif
        bins zero       = {64'h0000000000000000};
        bins pos_2p30   = {64'h0000000040000000};
        bins pos_2p32m1 = {64'h00000000FFFFFFFF};
        bins pos_2p60   = {64'h1000000000000000};
        bins neg_1      = {64'hFFFFFFFFFFFFFFFF};
        bins neg_2p30   = {64'hFFFFFFFFC0000000};
        bins neg_2p60   = {64'hF000000000000000};
    }

    // HS-mode
    cp_scounteren_access_hs: cross csraccess, counter, scounteren_bit, mcounteren_one, hcounteren_zero, priv_mode_hs;
    cp_delta_hs: cross csrr_time, htimedelta, priv_mode_hs;

    // VS-mode
    cp_mcounteren_access_vs: cross csraccess, counter, mcounteren_bit, hcounteren_one, scounteren_zero, priv_mode_vs;
    cp_mcounteren_access_vs_h0: cross csraccess, counter, mcounteren_bit, hcounteren_zero, scounteren_zero, priv_mode_vs;
    cp_hcounteren_access_vs: cross csraccess, counter, hcounteren_bit, mcounteren_one, scounteren_zero, priv_mode_vs;
    cp_delta_vs: cross csrr_time, htimedelta, priv_mode_vs;

    // U-mode
    cp_scounteren_access_u: cross csraccess, counter, scounteren_bit, mcounteren_one, hcounteren_zero, priv_mode_u;
    cp_delta_u: cross csrr_time, htimedelta, priv_mode_u;

    // VU-mode
    cp_mcounteren_access_vu: cross csraccess, counter, mcounteren_bit, hcounteren_one, scounteren_one, priv_mode_vu;
    cp_mcounteren_access_vu_hs0: cross csraccess, counter, mcounteren_bit, hcounteren_zero, scounteren_zero, priv_mode_vu;
    cp_hcounteren_access_vu: cross csraccess, counter, hcounteren_bit, mcounteren_one, scounteren_one, priv_mode_vu;
    cp_scounteren_access_vu: cross csraccess, counter, scounteren_bit, mcounteren_one, hcounteren_one, priv_mode_vu;
    cp_delta_vu: cross csrr_time, htimedelta, priv_mode_vu;
endgroup
`endif

function void h_sample(int hart, int issue, ins_t ins);
    H_hscsr_cg.sample(ins);
    H_vscause_cg.sample(ins);
    H_vscsr_cg.sample(ins);
    H_vsstatus_cg.sample(ins);
    H_vucsr_cg.sample(ins);
    H_inst_cg.sample(ins);
    `ifdef ZICNTR_SUPPORTED
        H_Zicntr_cg.sample(ins);
    `endif
endfunction
