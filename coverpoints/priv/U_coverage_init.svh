///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    U_uprivinst_cg = new();    U_uprivinst_cg.set_inst_name("obj_U_uprivinst");
    U_ucsr_cg = new();         U_ucsr_cg.set_inst_name("obj_U_ucsr");
`ifdef F_SUPPORTED
    U_F_cg = new();            U_F_cg.set_inst_name("obj_U_F");
`endif
`ifdef ZVE32X_SUPPORTED
    U_V_cg = new();            U_V_cg.set_inst_name("obj_U_V");
`endif
`ifdef ZVE32F_SUPPORTED
    U_VF_cg = new();           U_VF_cg.set_inst_name("obj_U_VF");
`endif
