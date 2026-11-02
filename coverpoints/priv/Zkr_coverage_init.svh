///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Written: Julia Gong jgong@g.hmc.edu April 2026 (split into per-mode suites August 2026)
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`ifndef EXCLUDE_SM
    Zkr_Sm_cg = new();      Zkr_Sm_cg.set_inst_name("obj_Zkr_Sm");
`endif
`ifdef S_SUPPORTED
    Zkr_S_cg = new();       Zkr_S_cg.set_inst_name("obj_Zkr_S");
`endif
`ifdef U_SUPPORTED
    Zkr_U_cg = new();       Zkr_U_cg.set_inst_name("obj_Zkr_U");
`endif
