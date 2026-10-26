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
        // vscause holds the same codes as scause (vscause_wlrl), which with H include the H causes
        bins b_10_ecall_vs = {10};
        bins b_20_instr_guest_page_fault = {20};
        bins b_21_load_guest_page_fault = {21};
        bins b_22_virtual_instruction = {22};
        bins b_23_store_guest_page_fault = {23};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            // vscause must hold exception codes 0-31
            bins b_11_ecall_m = {11};
            bins b_14_reserved = {14};
            bins b_16_double_trap = {16};
            bins b_17_reserved = {17};
            bins b_18_software_check = {18};
            bins b_19_hardware_error = {19};
            bins b_31_24_custom[] = {[31:24]};
        `elsif ZICFILP_SUPPORTED
            bins b_18_software_check = {18};
        `elsif ZICFISS_SUPPORTED
            bins b_18_software_check = {18};
        `endif
    }
    vscause_interrupt_values : coverpoint ins.current.rs1_val[`UDB_MXLEN-2:0] {
        bins b_1_supervisor_software = {1};
        bins b_3_machine_software = {3};
        bins b_5_supervisor_timer = {5};
        bins b_7_machine_timer = {7};
        bins b_9_supervisor_external = {9};
        bins b_11_machine_external = {11};
        bins b_2_vs_software = {2};
        bins b_6_vs_timer = {6};
        bins b_10_vs_external = {10};
        bins b_12_supervisor_guest_external = {12};
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            bins b_0_reserved = {0};
            bins b_4_reserved = {4};
            bins b_8_reserved = {8};
            bins b_13_counter_overflow = {13};
            bins b_14_reserved = {14};
            bins b_15_reserved = {15};
            bins b_31_16_custom[] = {[31:16]};
        `elsif SSCOFPMF_SUPPORTED
            bins b_13_counter_overflow = {13};
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
// H_F, H_V and H_VF tests (H_F-NN.S, H_V_*-NN.S, H_VF-NN.S) are part of the H suite and run only
// when F, Zve32x or Zve32f is also supported. They parallel S_F, S_V and S_VF in S_coverage.svh,
// using vsstatus in VS-mode and VU-mode crossed with the HS-level sstatus, and share their coverpoints through
// the general/RISCV_coverage_priv_* includes.
`ifdef F_SUPPORTED
covergroup H_F_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_f_coverpoints.svh"

    // vsstatus.FS is sampled from vsstatus; the HS-level FS from sstatus
    vsstatus_FS: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "fs")[1:0] {
        bins off     = {2'b00};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins initial_state = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean   = {2'b10};
        `endif
        bins dirty   = {2'b11};
    }
    hsstatus_FS: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs")[1:0] {
        bins off     = {2'b00};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins initial_state = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean   = {2'b10};
        `endif
        bins dirty   = {2'b11};
    }
    vsstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }
    hsstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }

    // main coverpoints
    cp_fcsr_access:           cross priv_mode_vs_vu, fcsrname, csraccesses, vsstatus_FS, hsstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with vsstatus.FS and sstatus.FS
    cp_vsstatus_FS_transition: cross priv_mode_vs_vu, deterministic_instrs, vsstatus_FS, hsstatus_FS;
    cp_vsstatus_FS_transition_nondeterministic: cross priv_mode_vs_vu, nondeterministic_instrs, vsstatus_FS_off_dirty, hsstatus_FS_off_dirty;
endgroup
`endif

`ifdef ZVE32X_SUPPORTED
covergroup H_V_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_v_coverpoints.svh"

    // crosses of the shared vector coverpoints
    cp_vcsrrswc                 : cross priv_mode_vs_vu, vcsrs, csrops;
    cp_vcsrs_walking1s          : cross priv_mode_vs_vu, writable_vcsrs, csrw, walking_ones_rs1;
    cp_sew_lmul_vsetvl          : cross priv_mode_vs_vu, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(rs2_sew) intersect { 3'b000 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_sew_lmul_vset_i_vli      : cross priv_mode_vs_vu, vset_i_vli_instructions, vset_sew, vset_lmul {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(vset_sew) intersect { 3'b000 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_vill_vsetvl              : cross priv_mode_vs_vu, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal, rs2_sew_all_supported, rs2_lmul_8;
    cp_vill_vset_i_vli          : cross priv_mode_vs_vu, vset_i_vli_instructions, vtype_prev_vill_set, current_vset_sew_all_supported, current_vset_lmul_8;
    cp_vill_vsetvl_rs2_vill     : cross priv_mode_vs_vu, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal_no_msb, rs2_sew_all_supported, rs2_lmul_8, rs2_vill_set;
    cp_vsetvl_rs2_vill          : cross priv_mode_vs_vu, vsetvl_instruction, rs2_vill_set, rs2_sew_supported, rs2_lmul_1, rs2_vtype_legal_no_msb, vtype_prev_vill_clear;
    cp_vtype_vill_set_vl_0      : cross priv_mode_vs_vu, vsetvl_instruction, rs1_non_zero, rs2_vill_set, vl_nonzero;
    cp_vsetvl_i_rd_nx0_rs1_x0   : cross priv_mode_vs_vu, vsetvl_i_instructions, vl_not_max, rd_n0, rs1_x0, vtype_all_sew_supported, vtype_all_lmul_supported {
        // SEW > LMUL*ELEN sets vill=1 and forces vtype.vsew/vlmul to 0,
        // so these BEFORE-state (sew, lmul) pairs are architecturally unreachable.
        ignore_bins illegal_sew_lmul =
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.half))   ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.sixteen)   && binsof(vtype_all_lmul_supported.eighth));
    }
    cp_vsetvl_i_rd_x0_rs1_x0    : cross priv_mode_vs_vu, vsetvl_i_instructions, vl_nonzero, rd_x0, rs1_x0, vset_i_vli_vlmax_unchanged;
    cp_vsetvl_i_avl_eq_zero     : cross priv_mode_vs_vu, vsetvl_i_instructions, rs1_eq_zero;
    cp_vsetvl_i_avl_eq_vlmax    : cross priv_mode_vs_vu, vsetvl_i_instructions, rs1_eq_vlmax;
    cp_vsetvl_i_avl_lt_2x_vlmax : cross priv_mode_vs_vu, vsetvl_i_instructions, rs1_lt_2x_vlmax_gt_vlmax;
    cp_vsetvl_i_avl_eq_2x_vlmax : cross priv_mode_vs_vu, vsetvl_i_instructions, rs1_eq_2x_vlmax;
    cp_vsetvl_i_avl_gt_2x_vlmax : cross priv_mode_vs_vu, vsetvl_i_instructions, rs1_gt_2x_vlmax;
    cp_vsetivli_avl_edges       : cross priv_mode_vs_vu, vsetivli_instruction, vtype_all_sew_supported, imm5_edges, vtype_lmul_1;
    cp_vstart_out_of_bounds     : cross priv_mode_vs_vu, vstart_csr, csr_write, rs1_2_to_16;
    cp_vl_walking1s_sew_lmul    : cross priv_mode_vs_vu, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1 {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            // SEW > LMUL*ELEN sets vill; the tests skip these unless the DUT supports the extra fractional LMULs.
            // Encodings are {vsew, vlmul}. ELEN is at most 64, so ELEN>=128 pairs are never legal.
            ignore_bins illegal_sew_lmul = binsof(vsetivli_prev_sew_lmul) intersect {
                5'b01_101,  // e16, mf8
                5'b10_110,  // e32, mf4
                5'b10_101,  // e32, mf8
                5'b11_111,  // e64, mf2
                5'b11_110,  // e64, mf4
                5'b11_101   // e64, mf8
            };
            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 = binsof(vsetivli_prev_sew_lmul) intersect {
                    5'b00_101,  // e8, mf8
                    5'b01_110,  // e16, mf4
                    5'b10_111   // e32, mf2
                };
            `endif
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////
    // cp_vsstatus_vs_*
    // tests vsstatus and sstatus ability to set clean and initial to dirty only when supposed to.
    // The VS-level VS is sampled from vsstatus.VS and the HS-level VS from sstatus.VS.
    // A vector instruction needs both to be on, and sets both to dirty.
    //////////////////////////////////////////////////////////////////////////////////

    // Initial and Clean only when MSTATUS_VS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    vsstatus_vs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vs") {
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    vsstatus_vs_all : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vs") {
        bins off = {0};
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    hsstatus_vs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") {
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    hsstatus_vs_all : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") {
        bins off = {0};
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    cp_vsstatus_vs_set_dirty_arithmetic : cross priv_mode_vs_vu, std_vec,        vector_vector_arithmetic_instruction,   vsstatus_vs_on, hsstatus_vs_on;
    cp_vsstatus_vs_set_dirty_csr        : cross priv_mode_vs_vu, std_vec,        vsetvli_instruction,                    vsstatus_vs_on, hsstatus_vs_on;
    cp_vsstatus_vs_set_dirty_vcsr       : cross priv_mode_vs_vu, vcsrs_writable, csrops,                                 vsstatus_vs_on, hsstatus_vs_on;

    // VS off at either level
    cp_vsstatus_vs_off_arithmetic       : cross priv_mode_vs_vu, vsstatus_vs_all, hsstatus_vs_all, vector_vector_arithmetic_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 ) {
        ignore_bins both_on = binsof(vsstatus_vs_all) intersect {[1:3]} && binsof(hsstatus_vs_all) intersect {[1:3]};
    }
    cp_vsstatus_vs_off_csr              : cross priv_mode_vs_vu, vsstatus_vs_all, hsstatus_vs_all, vsetvli_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 ) {
        ignore_bins both_on = binsof(vsstatus_vs_all) intersect {[1:3]} && binsof(hsstatus_vs_all) intersect {[1:3]};
    }

endgroup
`endif

`ifdef ZVE32F_SUPPORTED
covergroup H_VF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_vf_coverpoints.svh"

    // The VS-level status is sampled from vsstatus and the HS-level status from sstatus.
    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vs") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    // Initial and Clean only when MSTATUS_FS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    vsstatus_fs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "fs") {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    vsstatus_fs_all : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "fs") {
        bins off = {0};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    hsstatus_fs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs") {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }
    hsstatus_fs_all : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "fs") {
        bins off = {0};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    cp_vectorfp_vsstatus_fs_state_affecting_register : cross priv_mode_vs_vu, std_vec, vfmv_f_s, vsstatus_fs_on, hsstatus_fs_on;
    cp_vectorfp_vsstatus_fs_state_affecting_csr      : cross priv_mode_vs_vu, std_vec, vector_vector_arithmetic_fp_instruction, vsstatus_fs_on, hsstatus_fs_on, fflags_modified_after_clear;
    cp_vectorfp_vsstatus_fs_state_nonaffecting       : cross priv_mode_vs_vu, std_vec, vector_vector_arithmetic_fp_instruction, vsstatus_fs_on, hsstatus_fs_on, vs1_zero, vs2_zero;
    // FS off at either level
    cp_vectorfp_vsstatus_fs_off                      : cross priv_mode_vs_vu, std_trap_vec, vector_vector_arithmetic_fp_instruction, vsstatus_fs_all, hsstatus_fs_all, vs1_zero, vs2_zero {
        ignore_bins both_on = binsof(vsstatus_fs_all) intersect {[1:3]} && binsof(hsstatus_fs_all) intersect {[1:3]};
    }

endgroup
`endif

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
    mcounteren_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    hcounteren_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hcounteren", "hcounteren")[ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    scounteren_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scounteren", "scounteren")[ins.current.insn[24:20]] {
        bins disabled = {0};
        bins enabled  = {1};
    }
    // The same bits held while another counter-enable register is walked
    mcounteren_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[ins.current.insn[24:20]] {
        bins one = {1};
    }
    hcounteren_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hcounteren", "hcounteren")[ins.current.insn[24:20]] {
        bins one = {1};
    }
    hcounteren_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hcounteren", "hcounteren")[ins.current.insn[24:20]] {
        bins zero = {0};
    }
    scounteren_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scounteren", "scounteren")[ins.current.insn[24:20]] {
        bins one = {1};
    }
    scounteren_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scounteren", "scounteren")[ins.current.insn[24:20]] {
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
        htimedelta: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedelta", "htimedelta") {
    `else
        htimedelta: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedeltah", "htimedeltah")[31:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htimedelta", "htimedelta")[31:0]} {
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
    `ifdef F_SUPPORTED
        H_F_cg.sample(ins);
    `endif
    `ifdef ZVE32X_SUPPORTED
        H_V_cg.sample(ins);
    `endif
    `ifdef ZVE32F_SUPPORTED
        H_VF_cg.sample(ins);
    `endif
    `ifdef ZICNTR_SUPPORTED
        H_Zicntr_cg.sample(ins);
    `endif
endfunction
