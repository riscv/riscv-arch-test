///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Ssdbltrp H and HSm groups: vsstatus.SDT across xRET and traps, and double traps from VS-mode.
// Written: David_Harris@hmc.edu 8 November 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSDBLTRP

`ifdef H_SUPPORTED
// SRET in HS-mode clears vsstatus.SDT when it returns to VU-mode, and leaves it when it returns to VS-mode or HS-mode.
// SRET in VS-mode clears vsstatus.SDT.  The test records vsstatus.SDT and sstatus.SDT in HS-mode afterwards.
// A trap into VS-mode sets vsstatus.SDT, a trap into HS-mode ignores it, setting it by a CSR write clears
// vsstatus.SIE, and henvcfg.DTE = 0 makes it read-only zero.
covergroup Ssdbltrp_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    sret : coverpoint ins.current.insn {
        wildcard bins sret = {SRET};
    }
    `include "general/RISCV_coverage_ssdbltrp.svh"
    // {hstatus.SPV, sstatus.SPP}
    hs_sret_to : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spv")[0],
                             get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0]} {
        bins vu = {2'b10};
        bins vs = {2'b11};
        bins hs = {2'b01};
    }
    // vsstatus.SPP, which SRET in VS-mode reads
    vs_sret_to : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS, "spp")[0] {
        bins vu = {0};
        bins vs = {1};
    }
    cp_hs_sret_vsstatus_sdt : cross priv_mode_hs, sret, hs_sret_to, dte_on, vsstatus_sdt_set;
    cp_vs_sret_vsstatus_sdt : cross priv_mode_vs, sret, vs_sret_to, dte_on, vsstatus_sdt_set;

    vsstatus_sdt_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[24] {
        bins zero = {0};
    }
    // A breakpoint that medeleg and hedeleg send to VS-mode
    ebreak_to_vs : coverpoint ins.current.insn {
        bins ebreak = {EBREAK} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3] &&
                                    get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[3]);
    }
    cp_vs_trap_sdt : cross priv_mode_vs_vu, ebreak_to_vs, dte_on, vsstatus_sdt_clear;

    // A breakpoint and a load access fault that medeleg sends to HS-mode and hedeleg does not send on to VS-mode
    trap_to_hs : coverpoint ins.current.insn {
        bins ebreak = {EBREAK} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3] &&
                                    !get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[3]);
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
            wildcard bins lw_access_fault = {LW} iff (ins.current.eff_addr == `RVMODEL_ACCESS_FAULT_ADDRESS_LOAD &&
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[5] &&
                                    !get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[5]);
        `endif
    }
    cp_vs_sdt_target : cross priv_mode_vs, trap_to_hs, dte_on, vsstatus_sdt_set;

    // With menvcfg.DTE = 1 and henvcfg.DTE = 0: HS-mode reads and sets vsstatus.SDT, VS-mode sets it through sstatus,
    // and VS-mode takes a breakpoint that medeleg and hedeleg send to VS-mode
    `ifdef UDB_MXLEN_64
        vs_dte_off : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MENVCFG, "dte")[0],
                                 get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "dte")[0]} {
            bins vs_off = {2'b10};
        }
    `else
        vs_dte_off : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MENVCFGH, "dte")[0],
                                 get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFGH, "dte")[0]} {
            bins vs_off = {2'b10};
        }
    `endif
    dte0_access : coverpoint ins.current.insn {
        wildcard bins hs_read = {CSRR} iff ({ins.prev.mode_virt, ins.prev.mode} == 3'b001 &&
                                            ins.current.insn[31:20] == CSR_VSSTATUS);
        wildcard bins hs_write = {CSRRS} iff ({ins.prev.mode_virt, ins.prev.mode} == 3'b001 &&
                                             ins.current.insn[31:20] == CSR_VSSTATUS && ins.current.rs1_val[24]);
        wildcard bins vs_write = {CSRRS} iff ({ins.prev.mode_virt, ins.prev.mode} == 3'b101 &&
                                             ins.current.insn[31:20] == CSR_SSTATUS && ins.current.rs1_val[24]);
        bins vs_ebreak = {EBREAK} iff ({ins.prev.mode_virt, ins.prev.mode} == 3'b101 &&
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3] &&
                                       get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[3]);
    }
    cp_henvcfg_dte0 : cross dte0_access, vs_dte_off;

    // Writes of vsstatus from HS-mode and of sstatus from VS-mode: set SDT and SIE together, set SDT with SIE = 1,
    // set SIE with SDT = 1, and clear SDT while setting SIE
    vsstatus_write : coverpoint (({ins.prev.mode_virt, ins.prev.mode} == 3'b001 && ins.current.insn[31:20] == CSR_VSSTATUS) ||
                                 ({ins.prev.mode_virt, ins.prev.mode} == 3'b101 && ins.current.insn[31:20] == CSR_SSTATUS)) {
        bins yes = {1};
    }
    // SDT is bit 24 and SIE is bit 1
    sdt_sie_write : coverpoint ins.current.insn {
        wildcard bins set_sdt_and_sie = {CSRRS} iff (ins.current.rs1_val[24] && ins.current.rs1_val[1] &&
                                                     !get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[24]);
        wildcard bins set_sdt_with_sie = {CSRRS} iff (ins.current.rs1_val[24] && !ins.current.rs1_val[1] &&
                                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[1]);
        wildcard bins set_sie_with_sdt = {CSRRS} iff (!ins.current.rs1_val[24] && ins.current.rs1_val[1] &&
                                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[24]);
        wildcard bins clear_sdt_set_sie = {CSRRW} iff (!ins.current.rs1_val[24] && ins.current.rs1_val[1] &&
                                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[24]);
    }
    cp_vs_sdt_sie : cross priv_mode_hs_vs, vsstatus_write, sdt_sie_write, dte_on;
endgroup
`endif

`ifndef EXCLUDE_SM
`ifdef H_SUPPORTED
// A trap into VS-mode with vsstatus.SDT = 1 is a double trap, taken in M-mode.  With Smdbltrp, MRET and SRET in
// M-mode clear vsstatus.SDT when they return to VU-mode.
covergroup Ssdbltrp_HSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_ssdbltrp.svh"

    // A breakpoint and a load access fault that medeleg and hedeleg send to VS-mode
    trap_to_vs : coverpoint ins.current.insn {
        bins ebreak = {EBREAK} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[3] &&
                                    get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[3]);
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
            wildcard bins lw_access_fault = {LW} iff (ins.current.eff_addr == `RVMODEL_ACCESS_FAULT_ADDRESS_LOAD &&
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MEDELEG)[5] &&
                                    get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HEDELEG, "deleg")[5]);
        `endif
    }
    cp_vs_double_trap : cross priv_mode_vs, trap_to_vs, dte_on, vsstatus_sdt_set;

    `ifdef SMDBLTRP_SUPPORTED
        // MRET (by mstatus.MPV and MPP) and SRET in M-mode (by hstatus.SPV and sstatus.SPP) to VS-mode and VU-mode.
        // The test writes SPP and SDT through sstatus, so the coverpoints read them there.
        `ifdef UDB_MXLEN_64
            m_xret_to_virt : coverpoint ins.current.insn {
                bins mret_to_vs = {MRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp")[1:0] == 2'b01);
                bins mret_to_vu = {MRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp")[1:0] == 2'b00);
                bins sret_to_vs = {SRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0]);
                bins sret_to_vu = {SRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spv")[0] &&
                                              !get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0]);
            }
        `else
            m_xret_to_virt : coverpoint ins.current.insn {
                bins mret_to_vs = {MRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUSH, "mpv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp")[1:0] == 2'b01);
                bins mret_to_vu = {MRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUSH, "mpv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp")[1:0] == 2'b00);
                bins sret_to_vs = {SRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spv")[0] &&
                                              get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0]);
                bins sret_to_vu = {SRET} iff (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spv")[0] &&
                                              !get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "spp")[0]);
            }
        `endif
        // sstatus.SDT is bit 24
        sstatus_sdt_set : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS)[24] {
            bins one = {1};
        }
        cp_m_xret_vsstatus_sdt : cross priv_mode_m, m_xret_to_virt, dte_on, vsstatus_sdt_set, sstatus_sdt_set;
    `endif
endgroup
`endif
`endif

function void ssdbltrp_sample(int hart, int issue, ins_t ins);
    `ifdef H_SUPPORTED
        Ssdbltrp_H_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Ssdbltrp_HSm_cg.sample(ins);
        `endif
    `endif
endfunction
