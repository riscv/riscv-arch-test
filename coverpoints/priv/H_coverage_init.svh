///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    H_hscsr_cg = new();     H_hscsr_cg.set_inst_name("obj_H_hscsr");
    H_vscause_cg = new();   H_vscause_cg.set_inst_name("obj_H_vscause");
    H_vscsr_cg = new();     H_vscsr_cg.set_inst_name("obj_H_vscsr");
    H_vsstatus_cg = new();  H_vsstatus_cg.set_inst_name("obj_H_vsstatus");
    H_vucsr_cg = new();     H_vucsr_cg.set_inst_name("obj_H_vucsr");
    H_inst_cg = new();      H_inst_cg.set_inst_name("obj_H_inst");
`ifdef F_SUPPORTED
    H_F_cg = new();         H_F_cg.set_inst_name("obj_H_F");
`endif
`ifdef ZVE32X_SUPPORTED
    H_V_cg = new();         H_V_cg.set_inst_name("obj_H_V");
`endif
`ifdef ZVE32F_SUPPORTED
    H_VF_cg = new();        H_VF_cg.set_inst_name("obj_H_VF");
`endif
`ifdef ZICNTR_SUPPORTED
    H_Zicntr_cg = new();    H_Zicntr_cg.set_inst_name("obj_H_Zicntr");
`endif
