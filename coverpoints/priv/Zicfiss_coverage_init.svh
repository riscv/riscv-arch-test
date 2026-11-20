///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifndef EXCLUDE_SM
    Zicfiss_Sm_cg = new();     Zicfiss_Sm_cg.set_inst_name("obj_Zicfiss_Sm");
`endif
`ifdef S_SUPPORTED
    Zicfiss_S_cg = new();     Zicfiss_S_cg.set_inst_name("obj_Zicfiss_S");
`endif
`ifdef U_SUPPORTED
    Zicfiss_U_cg = new();     Zicfiss_U_cg.set_inst_name("obj_Zicfiss_U");
`endif
`ifdef H_SUPPORTED
    Zicfiss_H_cg = new();     Zicfiss_H_cg.set_inst_name("obj_Zicfiss_H");
`endif
