///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David Harris David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 RISC-V International
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp VS-mode and VU-mode Coverage
//
// henvcfg.LPE enables landing pads in VS-mode and senvcfg.LPE in VU-mode. Traps into
// VS-mode save ELP in vsstatus.SPELP; an SRET executed in VS-mode restores it from there.
// The test checks the resulting software-check exceptions with its trap count.
///////////////////////////////////////////////

`define COVER_ZICFILPH

covergroup ZicfilpH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "Zicfilp_defines.svh"

    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    henvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "henvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }

    // Previous instruction was an indirect jump through a register other than x1/x5/x7, which sets
    // ELP = LP_EXPECTED when landing pads are enabled
    lp_branch_prev: coverpoint (
        `ZICFILP_LP_JALR(ins.prev.insn)                                ? 2'd1 :
        (`ZICFILP_LP_CJUMP(ins.prev.insn) && (ins.prev.insn ==? C_JR)) ? 2'd2 :
        `ZICFILP_LP_CJUMP(ins.prev.insn)                               ? 2'd3 : 2'd0) {
        bins jalr = {2'd1};
        `ifdef ZCA_SUPPORTED
            bins c_jr   = {2'd2};
            bins c_jalr = {2'd3};
        `endif
    }
    // Its target: a non-LPAD instruction, or an LPAD whose nonzero label does not match x7[31:12].
    // Either raises a software-check exception only with landing pads enabled.
    lp_target: coverpoint {(ins.current.insn ==? LPAD),
                           ((ins.current.insn[31:12] != 20'h0) &&
                            (ins.current.insn[31:12] != ins.prev.x_wdata[7][31:12]))} {
        wildcard bins not_lpad      = {2'b0?};
        bins          lpad_mismatch = {2'b11};
    }

    // henvcfg.LPE, not menvcfg.LPE, enables landing pads in VS-mode
    cp_vs_lpe: cross priv_mode_vs, henvcfg_lpe, menvcfg_lpe, lp_branch_prev, lp_target;

    // senvcfg.LPE, not henvcfg.LPE, enables landing pads in VU-mode
    cp_vu_lpe: cross priv_mode_vu, senvcfg_lpe, henvcfg_lpe, lp_branch_prev, lp_target;

    // Trap from VS or VU-mode with ELP = LP_EXPECTED (a non-LPAD target of an ELP-setting jalr)
    // or NO_LP_EXPECTED (an ebreak after anything else), into VS-mode or HS-mode
    trap_elp: coverpoint {(`ZICFILP_LP_JALR(ins.prev.insn) && !(ins.current.insn ==? LPAD)),
                          (!`ZICFILP_LP_BRANCH(ins.prev.insn) && (ins.current.insn == EBREAK))} {
        bins lp_expected    = {2'b10};
        bins no_lp_expected = {2'b01};
    }
    // hedeleg[3] and hedeleg[18] are set together, so bit 18 names the handler for both traps
    trap_to: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[SOFTWARE_CHECK] {
        bins hs = {0};
        bins vs = {1};
    }
    mode_lpe_enabled: coverpoint (ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")
                                                         : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")) {
        bins enabled = {1};
    }
    cp_trap_entry_spelp: cross priv_mode_vs_vu, mode_lpe_enabled, trap_elp, trap_to;

    // SRET, which the test places before a non-LPAD instruction. It restores ELP from vsstatus.SPELP
    // when executed in VS-mode and from sstatus.SPELP when executed in HS-mode, only if the LPE of the
    // new mode (henvcfg.LPE for VS-mode, senvcfg.LPE for VU-mode) is 1. The test gives the other SPELP
    // the opposite value, so using the wrong one changes the outcome. Each mode writes SPP and SPELP
    // through sstatus, so both crosses read them from the sstatus record; in VS-mode that is vsstatus.
    sret: coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    vs_new_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp") {
        bins vu = {0};
        bins vs = {1};
    }
    hs_new_mode: coverpoint 2 * get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") +
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp") {
        bins vu = {2};  // hstatus.SPV = 1, sstatus.SPP = 0
        bins vs = {3};  // hstatus.SPV = 1, sstatus.SPP = 1
    }
    henvcfg_lpe_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    senvcfg_lpe_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    sstatus_spelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spelp") {
        bins no_lp_expected = {0};
        bins lp_expected    = {1};
    }
    // Checked in HS-mode, where vsstatus has its own record
    vsstatus_spelp_differs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "spelp") !=
                                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spelp")) {
        bins differs = {1'b1};
    }
    cp_vs_sret_spelp: cross priv_mode_vs, sret, vs_new_mode, henvcfg_lpe_before, senvcfg_lpe_before, sstatus_spelp;
    cp_hs_sret_spelp: cross priv_mode_hs, sret, hs_new_mode, henvcfg_lpe_before, senvcfg_lpe_before, sstatus_spelp,
                            vsstatus_spelp_differs;

    // sstatus.SPELP written in VS-mode, which is vsstatus.SPELP
    sstatus_spelp_write: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_SSTATUS);
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_SSTATUS);
    }
    spelp_operand: coverpoint ins.current.rs1_val[23] {
        bins spelp = {1'b1};
    }
    cp_vs_sstatus_spelp: cross priv_mode_vs, sstatus_spelp_write, spelp_operand;

endgroup

function void zicfilph_sample(int hart, int issue, ins_t ins);
    ZicfilpH_cg.sample(ins);
endfunction
