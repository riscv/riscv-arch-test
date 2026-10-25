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
    Svinval_Sm_cg = new();      Svinval_Sm_cg.set_inst_name("obj_Svinval_Sm");
`endif
    Svinval_cg = new();         Svinval_cg.set_inst_name("obj_Svinval");
