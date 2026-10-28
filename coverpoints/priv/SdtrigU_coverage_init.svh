///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    SdtrigU_cg = new();                   SdtrigU_cg.set_inst_name("obj_SdtrigU");
    SdtrigU_access_cg = new();            SdtrigU_access_cg.set_inst_name("obj_SdtrigU_access");
    SdtrigU_icount_cg = new();            SdtrigU_icount_cg.set_inst_name("obj_SdtrigU_icount");
    SdtrigU_a_cg = new();                 SdtrigU_a_cg.set_inst_name("obj_SdtrigU_a");
    SdtrigU_cache_operations_cg = new();  SdtrigU_cache_operations_cg.set_inst_name("obj_SdtrigU_cache_operations");
    `ifdef ZVL32B_SUPPORTED
        SdtrigU_combined_accesses_cg = new(); SdtrigU_combined_accesses_cg.set_inst_name("obj_SdtrigU_combined_accesses");
    `endif
    SdtrigU_itrigger_cg = new();          SdtrigU_itrigger_cg.set_inst_name("obj_SdtrigU_itrigger");
    SdtrigU_etrigger_cg = new();          SdtrigU_etrigger_cg.set_inst_name("obj_SdtrigU_etrigger");
    SdtrigU_mcontrol6_cg = new();         SdtrigU_mcontrol6_cg.set_inst_name("obj_SdtrigU_mcontrol6");
    SdtrigU_textra_cg = new();            SdtrigU_textra_cg.set_inst_name("obj_SdtrigU_textra");
