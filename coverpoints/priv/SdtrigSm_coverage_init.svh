///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    SdtrigSm_sdtrig_cg = new();             SdtrigSm_sdtrig_cg.set_inst_name("obj_SdtrigSm_sdtrig");
    SdtrigSm_native_triggers_cg = new();    SdtrigSm_native_triggers_cg.set_inst_name("obj_SdtrigSm_native_triggers");
    // TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_MCONTROL6
    SdtrigSm_a_cg = new();                  SdtrigSm_a_cg.set_inst_name("obj_SdtrigSm_a");
    SdtrigSm_combined_accesses_cg = new();  SdtrigSm_combined_accesses_cg.set_inst_name("obj_SdtrigSm_combined_accesses");
    SdtrigSm_cache_operations_cg = new();   SdtrigSm_cache_operations_cg.set_inst_name("obj_SdtrigSm_cache_operations");
    SdtrigSm_address_matches_cg = new();    SdtrigSm_address_matches_cg.set_inst_name("obj_SdtrigSm_address_matches");
    // TODO(trigger_types): // `endif
    SdtrigSm_csr_cg = new();                SdtrigSm_csr_cg.set_inst_name("obj_SdtrigSm_csr");
    // TODO(trigger_types): // `ifdef UDB_TRIGGER_TYPES_MCONTROL6
    SdtrigSm_mcontrol6_cg = new();          SdtrigSm_mcontrol6_cg.set_inst_name("obj_SdtrigSm_mcontrol6");
    // TODO(trigger_types): // `endif
    // TODO(trigger_types): wrap each in // `ifdef UDB_TRIGGER_TYPES_<TYPE> / // `endif
    // (must match the covergroup guards in SdtrigSm_coverage.svh -- new() only runs if compiled)
    SdtrigSm_icount_cg = new();             SdtrigSm_icount_cg.set_inst_name("obj_SdtrigSm_icount");
    SdtrigSm_itrigger_cg = new();           SdtrigSm_itrigger_cg.set_inst_name("obj_SdtrigSm_itrigger");
    SdtrigSm_etrigger_cg = new();           SdtrigSm_etrigger_cg.set_inst_name("obj_SdtrigSm_etrigger");
    SdtrigSm_textra_cg = new();             SdtrigSm_textra_cg.set_inst_name("obj_SdtrigSm_textra");
