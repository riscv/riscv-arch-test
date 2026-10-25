///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Sm_mcause_cg = new();      Sm_mcause_cg.set_inst_name("obj_Sm_mcause");
    Sm_mstatus_cg = new();     Sm_mstatus_cg.set_inst_name("obj_Sm_mstatus");
    Sm_mprivinst_cg = new();   Sm_mprivinst_cg.set_inst_name("obj_Sm_mprivinst");
    Sm_mcsr_cg = new();        Sm_mcsr_cg.set_inst_name("obj_Sm_mcsr");
`ifdef F_SUPPORTED
    Sm_F_cg = new();            Sm_F_cg.set_inst_name("obj_Sm_F");
`endif
`ifdef ZVE32X_SUPPORTED
    Sm_V_cg = new();            Sm_V_cg.set_inst_name("obj_Sm_V");
`endif
`ifdef ZVE32F_SUPPORTED
    Sm_VF_cg = new();           Sm_VF_cg.set_inst_name("obj_Sm_VF");
`endif
`ifdef ZICNTR_SUPPORTED
    Sm_Zicntr_cg = new();    Sm_Zicntr_cg.set_inst_name("obj_Sm_Zicntr");
`endif
`ifdef H_SUPPORTED
    Sm_H_mcsr_cg = new();    Sm_H_mcsr_cg.set_inst_name("obj_Sm_H_mcsr");
    Sm_H_tvm_cg = new();     Sm_H_tvm_cg.set_inst_name("obj_Sm_H_tvm");
    Sm_H_inst_cg = new();    Sm_H_inst_cg.set_inst_name("obj_Sm_H_inst");
`endif
