///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Written: David_Harris@hmc.edu 8 November 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifndef EXCLUDE_SM
    `ifdef S_SUPPORTED
        Ssdbltrp_Sm_cg = new();    Ssdbltrp_Sm_cg.set_inst_name("obj_Ssdbltrp_Sm");
    `endif
`endif
`ifdef H_SUPPORTED
    Ssdbltrp_H_cg = new();     Ssdbltrp_H_cg.set_inst_name("obj_Ssdbltrp_H");
    `ifndef EXCLUDE_SM
        Ssdbltrp_HSm_cg = new();   Ssdbltrp_HSm_cg.set_inst_name("obj_Ssdbltrp_HSm");
    `endif
`endif
