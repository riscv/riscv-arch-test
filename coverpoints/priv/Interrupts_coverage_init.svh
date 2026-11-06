///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifdef S_SUPPORTED
    Interrupts_cg = new();                  Interrupts_cg.set_inst_name("obj_Interrupts");
`endif
`ifndef EXCLUDE_SM
    Interrupts_Sm_cg = new();               Interrupts_Sm_cg.set_inst_name("obj_Interrupts_Sm");
`endif
`ifdef RVTEST_SGEI_INTR_IMPL
    Interrupts_Sgei_cg = new();             Interrupts_Sgei_cg.set_inst_name("obj_Interrupts_Sgei");
    `ifndef EXCLUDE_SM
        Interrupts_SgeiSm_cg = new();       Interrupts_SgeiSm_cg.set_inst_name("obj_Interrupts_SgeiSm");
    `endif
`endif
`ifdef SHLCOFIDELEG_SUPPORTED
    Interrupts_Shlcofideleg_cg = new();     Interrupts_Shlcofideleg_cg.set_inst_name("obj_Interrupts_Shlcofideleg");
    `ifndef EXCLUDE_SM
        Interrupts_SmShlcofideleg_cg = new(); Interrupts_SmShlcofideleg_cg.set_inst_name("obj_Interrupts_SmShlcofideleg");
    `endif
`endif
