///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    SdtrigSm_trig_module_reg_cg = new();       SdtrigSm_trig_module_reg_cg.set_inst_name("obj_SdtrigSm_trig_module_reg");
    SdtrigSm_access_cg = new();                SdtrigSm_access_cg.set_inst_name("obj_SdtrigSm_access");
    SdtrigSm_icount_cg = new();                SdtrigSm_icount_cg.set_inst_name("obj_SdtrigSm_icount");
    SdtrigSm_a_cg = new();                     SdtrigSm_a_cg.set_inst_name("obj_SdtrigSm_a");
    SdtrigSm_cache_operations_cg = new();      SdtrigSm_cache_operations_cg.set_inst_name("obj_SdtrigSm_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        SdtrigSm_combined_accesses_cg = new(); SdtrigSm_combined_accesses_cg.set_inst_name("obj_SdtrigSm_combined_accesses");
    `endif
    SdtrigSm_itrigger_cg = new();              SdtrigSm_itrigger_cg.set_inst_name("obj_SdtrigSm_itrigger");
    SdtrigSm_etrigger_cg = new();              SdtrigSm_etrigger_cg.set_inst_name("obj_SdtrigSm_etrigger");
    SdtrigSm_mcontrol6_cg = new();             SdtrigSm_mcontrol6_cg.set_inst_name("obj_SdtrigSm_mcontrol6");
    SdtrigSm_textra_cg = new();                SdtrigSm_textra_cg.set_inst_name("obj_SdtrigSm_textra");
    SdtrigSm_address_matches_cg = new();       SdtrigSm_address_matches_cg.set_inst_name("obj_SdtrigSm_address_matches");
    `ifdef UDB_TCONTROL_IMPLEMENTED
        SdtrigSm_tcontrol_cg = new();          SdtrigSm_tcontrol_cg.set_inst_name("obj_SdtrigSm_tcontrol");
    `endif
