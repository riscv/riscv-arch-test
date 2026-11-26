///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifndef EXCLUDE_SM
    Sdtrig_Sm_trig_module_reg_cg = new();       Sdtrig_Sm_trig_module_reg_cg.set_inst_name("obj_Sdtrig_Sm_trig_module_reg");
    Sdtrig_Sm_access_cg = new();                Sdtrig_Sm_access_cg.set_inst_name("obj_Sdtrig_Sm_access");
    Sdtrig_Sm_icount_cg = new();                Sdtrig_Sm_icount_cg.set_inst_name("obj_Sdtrig_Sm_icount");
    Sdtrig_Sm_a_cg = new();                     Sdtrig_Sm_a_cg.set_inst_name("obj_Sdtrig_Sm_a");
    Sdtrig_Sm_cache_operations_cg = new();      Sdtrig_Sm_cache_operations_cg.set_inst_name("obj_Sdtrig_Sm_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        Sdtrig_Sm_combined_accesses_cg = new(); Sdtrig_Sm_combined_accesses_cg.set_inst_name("obj_Sdtrig_Sm_combined_accesses");
    `endif
    Sdtrig_Sm_itrigger_cg = new();              Sdtrig_Sm_itrigger_cg.set_inst_name("obj_Sdtrig_Sm_itrigger");
    Sdtrig_Sm_etrigger_cg = new();              Sdtrig_Sm_etrigger_cg.set_inst_name("obj_Sdtrig_Sm_etrigger");
    Sdtrig_Sm_mcontrol6_cg = new();             Sdtrig_Sm_mcontrol6_cg.set_inst_name("obj_Sdtrig_Sm_mcontrol6");
    Sdtrig_Sm_textra_cg = new();                Sdtrig_Sm_textra_cg.set_inst_name("obj_Sdtrig_Sm_textra");
    Sdtrig_Sm_address_matches_cg = new();       Sdtrig_Sm_address_matches_cg.set_inst_name("obj_Sdtrig_Sm_address_matches");
    `ifdef UDB_TCONTROL_IMPLEMENTED
        Sdtrig_Sm_tcontrol_cg = new();          Sdtrig_Sm_tcontrol_cg.set_inst_name("obj_Sdtrig_Sm_tcontrol");
    `endif
`endif
`ifdef S_SUPPORTED
    Sdtrig_S_cg = new();                        Sdtrig_S_cg.set_inst_name("obj_Sdtrig_S");
    Sdtrig_S_access_cg = new();                 Sdtrig_S_access_cg.set_inst_name("obj_Sdtrig_S_access");
    Sdtrig_S_trig_module_reg_cg = new();        Sdtrig_S_trig_module_reg_cg.set_inst_name("obj_Sdtrig_S_trig_module_reg");
    Sdtrig_S_icount_cg = new();                 Sdtrig_S_icount_cg.set_inst_name("obj_Sdtrig_S_icount");
    Sdtrig_S_a_cg = new();                      Sdtrig_S_a_cg.set_inst_name("obj_Sdtrig_S_a");
    Sdtrig_S_cache_operations_cg = new();       Sdtrig_S_cache_operations_cg.set_inst_name("obj_Sdtrig_S_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        Sdtrig_S_combined_accesses_cg = new();  Sdtrig_S_combined_accesses_cg.set_inst_name("obj_Sdtrig_S_combined_accesses");
    `endif
    Sdtrig_S_itrigger_cg = new();               Sdtrig_S_itrigger_cg.set_inst_name("obj_Sdtrig_S_itrigger");
    Sdtrig_S_etrigger_cg = new();               Sdtrig_S_etrigger_cg.set_inst_name("obj_Sdtrig_S_etrigger");
    Sdtrig_S_mcontrol6_cg = new();              Sdtrig_S_mcontrol6_cg.set_inst_name("obj_Sdtrig_S_mcontrol6");
    Sdtrig_S_textra_cg = new();                 Sdtrig_S_textra_cg.set_inst_name("obj_Sdtrig_S_textra");
    Sdtrig_S_address_matches_cg = new();        Sdtrig_S_address_matches_cg.set_inst_name("obj_Sdtrig_S_address_matches");
`endif
`ifdef U_SUPPORTED
    Sdtrig_U_cg = new();                        Sdtrig_U_cg.set_inst_name("obj_Sdtrig_U");
    Sdtrig_U_access_cg = new();                 Sdtrig_U_access_cg.set_inst_name("obj_Sdtrig_U_access");
    Sdtrig_U_icount_cg = new();                 Sdtrig_U_icount_cg.set_inst_name("obj_Sdtrig_U_icount");
    Sdtrig_U_a_cg = new();                      Sdtrig_U_a_cg.set_inst_name("obj_Sdtrig_U_a");
    Sdtrig_U_cache_operations_cg = new();       Sdtrig_U_cache_operations_cg.set_inst_name("obj_Sdtrig_U_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        Sdtrig_U_combined_accesses_cg = new();  Sdtrig_U_combined_accesses_cg.set_inst_name("obj_Sdtrig_U_combined_accesses");
    `endif
    Sdtrig_U_itrigger_cg = new();               Sdtrig_U_itrigger_cg.set_inst_name("obj_Sdtrig_U_itrigger");
    Sdtrig_U_etrigger_cg = new();               Sdtrig_U_etrigger_cg.set_inst_name("obj_Sdtrig_U_etrigger");
    Sdtrig_U_mcontrol6_cg = new();              Sdtrig_U_mcontrol6_cg.set_inst_name("obj_Sdtrig_U_mcontrol6");
    Sdtrig_U_textra_cg = new();                 Sdtrig_U_textra_cg.set_inst_name("obj_Sdtrig_U_textra");
`endif
`ifdef H_SUPPORTED
    Sdtrig_H_cg = new();       Sdtrig_H_cg.set_inst_name("obj_Sdtrig_H");
    `ifndef EXCLUDE_SM
        Sdtrig_HSm_cg = new(); Sdtrig_HSm_cg.set_inst_name("obj_Sdtrig_HSm");
    `endif
`endif
