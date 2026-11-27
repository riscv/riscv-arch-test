///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Shcounterenw_cg = new();         Shcounterenw_cg.set_inst_name("obj_Shcounterenw");
`ifndef EXCLUDE_SM
    Shcounterenw_Sm_cg = new();      Shcounterenw_Sm_cg.set_inst_name("obj_Shcounterenw_Sm");
`endif // EXCLUDE_SM
