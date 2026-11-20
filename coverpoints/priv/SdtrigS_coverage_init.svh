///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    SdtrigS_cg = new();                   SdtrigS_cg.set_inst_name("obj_SdtrigS");
    SdtrigS_access_cg = new();            SdtrigS_access_cg.set_inst_name("obj_SdtrigS_access");
    SdtrigS_trig_module_reg_cg = new();   SdtrigS_trig_module_reg_cg.set_inst_name("obj_SdtrigS_trig_module_reg");
    SdtrigS_icount_cg = new();            SdtrigS_icount_cg.set_inst_name("obj_SdtrigS_icount");
    SdtrigS_a_cg = new();                 SdtrigS_a_cg.set_inst_name("obj_SdtrigS_a");
    SdtrigS_cache_operations_cg = new();  SdtrigS_cache_operations_cg.set_inst_name("obj_SdtrigS_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        SdtrigS_combined_accesses_cg = new(); SdtrigS_combined_accesses_cg.set_inst_name("obj_SdtrigS_combined_accesses");
    `endif
    SdtrigS_itrigger_cg = new();          SdtrigS_itrigger_cg.set_inst_name("obj_SdtrigS_itrigger");
    SdtrigS_etrigger_cg = new();          SdtrigS_etrigger_cg.set_inst_name("obj_SdtrigS_etrigger");
    SdtrigS_mcontrol6_cg = new();         SdtrigS_mcontrol6_cg.set_inst_name("obj_SdtrigS_mcontrol6");
    SdtrigS_textra_cg = new();            SdtrigS_textra_cg.set_inst_name("obj_SdtrigS_textra");
    SdtrigS_address_matches_cg = new();   SdtrigS_address_matches_cg.set_inst_name("obj_SdtrigS_address_matches");
