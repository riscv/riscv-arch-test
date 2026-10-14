///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    S_scause_cg = new();      S_scause_cg.set_inst_name("obj_S_scause");
    S_sstatus_cg = new();     S_sstatus_cg.set_inst_name("obj_S_sstatus");
    S_sprivinst_cg = new();   S_sprivinst_cg.set_inst_name("obj_S_sprivinst");
    S_scsr_cg = new();        S_scsr_cg.set_inst_name("obj_S_scsr");
`ifdef F_SUPPORTED
    S_F_cg = new();            S_F_cg.set_inst_name("obj_S_F");
`endif
`ifdef ZVE32X_SUPPORTED
    S_V_cg = new();            S_V_cg.set_inst_name("obj_S_V");
`endif
`ifdef ZVE32F_SUPPORTED
    S_VF_cg = new();           S_VF_cg.set_inst_name("obj_S_VF");
`endif
