///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`ifndef EXCLUDE_SM
    Zicfilp_Sm_cg = new();     Zicfilp_Sm_cg.set_inst_name("obj_Zicfilp_Sm");
`endif
    Zicfilp_S_cg = new();      Zicfilp_S_cg.set_inst_name("obj_Zicfilp_S");
    Zicfilp_U_cg = new();      Zicfilp_U_cg.set_inst_name("obj_Zicfilp_U");
