///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Coverpoints shared by the Ssdbltrp_H and Ssdbltrp_HSm covergroups.
// Written: David_Harris@hmc.edu 26 November 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    `ifdef UDB_MXLEN_64
        dte_on : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MENVCFG, "dte")[0],
                             get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "dte")[0]} {
            bins both = {2'b11};
        }
    `else
        dte_on : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MENVCFGH, "dte")[0],
                             get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFGH, "dte")[0]} {
            bins both = {2'b11};
        }
    `endif
    // vsstatus.SDT is bit 24
    vsstatus_sdt_set : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS)[24] {
        bins one = {1};
    }
