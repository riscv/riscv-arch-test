///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Ssdbltrp H group: vsstatus.SDT across SRET from HS-mode and from VS-mode.
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
covergroup Ssdbltrp_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    sret : coverpoint ins.current.insn {
        wildcard bins sret = {SRET};
    }
    `ifdef UDB_MXLEN_64
        dte_on : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "dte")[0],
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "dte")[0]} {
            bins both = {2'b11};
        }
    `else
        dte_on : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "dte")[0],
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "dte")[0]} {
            bins both = {2'b11};
        }
    `endif
    // vsstatus.SDT is bit 24
    vsstatus_sdt_set : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vsstatus")[24] {
        bins one = {1};
    }
    // {hstatus.SPV, sstatus.SPP}
    hs_sret_to : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv")[0],
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0]} {
        bins vu = {2'b10};
        bins vs = {2'b11};
        bins hs = {2'b01};
    }
    // vsstatus.SPP, which SRET in VS-mode reads
    vs_sret_to : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "spp")[0] {
        bins vu = {0};
        bins vs = {1};
    }
    cp_hs_sret_vsstatus_sdt : cross priv_mode_hs, sret, hs_sret_to, dte_on, vsstatus_sdt_set;
    cp_vs_sret_vsstatus_sdt : cross priv_mode_vs, sret, vs_sret_to, dte_on, vsstatus_sdt_set;
endgroup
`endif

function void ssdbltrp_sample(int hart, int issue, ins_t ins);
    `ifdef H_SUPPORTED
        Ssdbltrp_H_cg.sample(ins);
    `endif
endfunction
