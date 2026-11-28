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
    Ssstrict_Sm_mcsr_cg = new();         Ssstrict_Sm_mcsr_cg.set_inst_name("obj_Ssstrict_Sm_mcsr");
    Ssstrict_Sm_instr_cg = new();        Ssstrict_Sm_instr_cg.set_inst_name("obj_Ssstrict_Sm_instr");
    Ssstrict_Sm_comp_instr_cg = new();   Ssstrict_Sm_comp_instr_cg.set_inst_name("obj_Ssstrict_Sm_comp_instr");
`endif
    Ssstrict_S_instr_cg = new();        Ssstrict_S_instr_cg.set_inst_name("obj_Ssstrict_S_instr");
    Ssstrict_S_comp_instr_cg = new();   Ssstrict_S_comp_instr_cg.set_inst_name("obj_Ssstrict_S_comp_instr");
    Ssstrict_S_scsr_cg = new();         Ssstrict_S_scsr_cg.set_inst_name("obj_Ssstrict_S_scsr");
    Ssstrict_U_instr_cg = new();        Ssstrict_U_instr_cg.set_inst_name("obj_Ssstrict_U_instr");
    Ssstrict_U_comp_instr_cg = new();   Ssstrict_U_comp_instr_cg.set_inst_name("obj_Ssstrict_U_comp_instr");
    Ssstrict_U_ucsr_cg = new();         Ssstrict_U_ucsr_cg.set_inst_name("obj_Ssstrict_U_ucsr");
