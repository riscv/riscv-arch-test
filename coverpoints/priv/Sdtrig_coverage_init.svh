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
    `ifdef SDTRIG_ICOUNT_ANY
    `ifdef UDB_SDTRIG_M_WRITABLE
        Sdtrig_Sm_icount_cg = new();            Sdtrig_Sm_icount_cg.set_inst_name("obj_Sdtrig_Sm_icount");
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_M_WRITABLE
    `ifdef SDTRIG_LRSC_OR_AMO
        Sdtrig_Sm_a_cg = new();                 Sdtrig_Sm_a_cg.set_inst_name("obj_Sdtrig_Sm_a");
    `endif
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_M_WRITABLE
    `ifdef SDTRIG_CBO_OR_PREFETCH
        Sdtrig_Sm_cache_operations_cg = new();  Sdtrig_Sm_cache_operations_cg.set_inst_name("obj_Sdtrig_Sm_cache_operations");
    `endif
    `endif
    `endif
    `ifdef ZVL32B_SUPPORTED
        `ifdef SDTRIG_MCONTROL6_ANY
        `ifdef UDB_SDTRIG_M_WRITABLE
            Sdtrig_Sm_combined_accesses_cg = new(); Sdtrig_Sm_combined_accesses_cg.set_inst_name("obj_Sdtrig_Sm_combined_accesses");
        `endif
        `endif
    `endif
    `ifdef SDTRIG_ITRIGGER_ANY
        Sdtrig_Sm_itrigger_cg = new();          Sdtrig_Sm_itrigger_cg.set_inst_name("obj_Sdtrig_Sm_itrigger");
    `endif
    `ifdef SDTRIG_ETRIGGER_ANY
        Sdtrig_Sm_etrigger_cg = new();          Sdtrig_Sm_etrigger_cg.set_inst_name("obj_Sdtrig_Sm_etrigger");
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
        Sdtrig_Sm_mcontrol6_cg = new();         Sdtrig_Sm_mcontrol6_cg.set_inst_name("obj_Sdtrig_Sm_mcontrol6");
    `endif
    `ifdef UDB_TDATA3_IMPLEMENTED
        Sdtrig_Sm_textra_cg = new();            Sdtrig_Sm_textra_cg.set_inst_name("obj_Sdtrig_Sm_textra");
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_MCONTROL6_EXECUTE_WRITABLE
        Sdtrig_Sm_address_matches_cg = new();   Sdtrig_Sm_address_matches_cg.set_inst_name("obj_Sdtrig_Sm_address_matches");
    `endif
    `endif
    `ifdef UDB_TCONTROL_IMPLEMENTED
        Sdtrig_Sm_tcontrol_cg = new();          Sdtrig_Sm_tcontrol_cg.set_inst_name("obj_Sdtrig_Sm_tcontrol");
    `endif
`endif
`ifdef S_SUPPORTED
    `ifdef UDB_SDTRIG_S_WRITABLE
    `ifdef SDTRIG_BREAKPOINT_ANY
        Sdtrig_S_cg = new();                    Sdtrig_S_cg.set_inst_name("obj_Sdtrig_S");
    `endif
    `endif
    Sdtrig_S_access_cg = new();                 Sdtrig_S_access_cg.set_inst_name("obj_Sdtrig_S_access");
    Sdtrig_S_trig_module_reg_cg = new();        Sdtrig_S_trig_module_reg_cg.set_inst_name("obj_Sdtrig_S_trig_module_reg");
    `ifdef SDTRIG_ICOUNT_ANY
    `ifdef UDB_SDTRIG_S_WRITABLE
        Sdtrig_S_icount_cg = new();             Sdtrig_S_icount_cg.set_inst_name("obj_Sdtrig_S_icount");
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_S_WRITABLE
    `ifdef SDTRIG_LRSC_OR_AMO
        Sdtrig_S_a_cg = new();                  Sdtrig_S_a_cg.set_inst_name("obj_Sdtrig_S_a");
    `endif
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_S_WRITABLE
    `ifdef SDTRIG_CBO_OR_PREFETCH
        Sdtrig_S_cache_operations_cg = new();   Sdtrig_S_cache_operations_cg.set_inst_name("obj_Sdtrig_S_cache_operations");
    `endif
    `endif
    `endif
    `ifdef ZVL32B_SUPPORTED
        `ifdef SDTRIG_MCONTROL6_ANY
        `ifdef UDB_SDTRIG_S_WRITABLE
            Sdtrig_S_combined_accesses_cg = new();  Sdtrig_S_combined_accesses_cg.set_inst_name("obj_Sdtrig_S_combined_accesses");
        `endif
        `endif
    `endif
    `ifdef SDTRIG_ITRIGGER_ANY
    `ifdef UDB_SDTRIG_S_WRITABLE
        Sdtrig_S_itrigger_cg = new();           Sdtrig_S_itrigger_cg.set_inst_name("obj_Sdtrig_S_itrigger");
    `endif
    `endif
    `ifdef SDTRIG_ETRIGGER_ANY
    `ifdef UDB_SDTRIG_S_WRITABLE
        Sdtrig_S_etrigger_cg = new();           Sdtrig_S_etrigger_cg.set_inst_name("obj_Sdtrig_S_etrigger");
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
        Sdtrig_S_mcontrol6_cg = new();          Sdtrig_S_mcontrol6_cg.set_inst_name("obj_Sdtrig_S_mcontrol6");
    `endif
    `ifdef SDTRIG_S_TEXTRA
        Sdtrig_S_textra_cg = new();             Sdtrig_S_textra_cg.set_inst_name("obj_Sdtrig_S_textra");
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_MCONTROL6_EXECUTE_WRITABLE
        Sdtrig_S_address_matches_cg = new();    Sdtrig_S_address_matches_cg.set_inst_name("obj_Sdtrig_S_address_matches");
    `endif
    `endif
`endif
`ifdef U_SUPPORTED
    `ifdef UDB_SDTRIG_U_WRITABLE
    `ifdef SDTRIG_BREAKPOINT_ANY
        Sdtrig_U_cg = new();                    Sdtrig_U_cg.set_inst_name("obj_Sdtrig_U");
    `endif
    `endif
    Sdtrig_U_access_cg = new();                 Sdtrig_U_access_cg.set_inst_name("obj_Sdtrig_U_access");
    `ifdef SDTRIG_ICOUNT_ANY
    `ifdef UDB_SDTRIG_U_WRITABLE
        Sdtrig_U_icount_cg = new();             Sdtrig_U_icount_cg.set_inst_name("obj_Sdtrig_U_icount");
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_U_WRITABLE
    `ifdef SDTRIG_LRSC_OR_AMO
        Sdtrig_U_a_cg = new();                  Sdtrig_U_a_cg.set_inst_name("obj_Sdtrig_U_a");
    `endif
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef UDB_SDTRIG_U_WRITABLE
    `ifdef SDTRIG_CBO_OR_PREFETCH
        Sdtrig_U_cache_operations_cg = new();   Sdtrig_U_cache_operations_cg.set_inst_name("obj_Sdtrig_U_cache_operations");
    `endif
    `endif
    `endif
    `ifdef ZVL32B_SUPPORTED
        `ifdef SDTRIG_MCONTROL6_ANY
        `ifdef UDB_SDTRIG_U_WRITABLE
            Sdtrig_U_combined_accesses_cg = new();  Sdtrig_U_combined_accesses_cg.set_inst_name("obj_Sdtrig_U_combined_accesses");
        `endif
        `endif
    `endif
    `ifdef S_SUPPORTED
    `ifdef SDTRIG_ITRIGGER_ANY
    `ifdef UDB_SDTRIG_U_WRITABLE
        Sdtrig_U_itrigger_cg = new();           Sdtrig_U_itrigger_cg.set_inst_name("obj_Sdtrig_U_itrigger");
    `endif
    `endif
    `endif
    `ifdef S_SUPPORTED
    `ifdef SDTRIG_ETRIGGER_ANY
    `ifdef UDB_SDTRIG_U_WRITABLE
        Sdtrig_U_etrigger_cg = new();           Sdtrig_U_etrigger_cg.set_inst_name("obj_Sdtrig_U_etrigger");
    `endif
    `endif
    `endif
    `ifdef SDTRIG_MCONTROL6_ANY
        Sdtrig_U_mcontrol6_cg = new();          Sdtrig_U_mcontrol6_cg.set_inst_name("obj_Sdtrig_U_mcontrol6");
    `endif
    `ifdef UDB_TDATA3_IMPLEMENTED
    `ifdef UDB_SDTRIG_U_WRITABLE
        Sdtrig_U_textra_cg = new();             Sdtrig_U_textra_cg.set_inst_name("obj_Sdtrig_U_textra");
    `endif
    `endif
`endif
`ifdef H_SUPPORTED
    Sdtrig_H_cg = new();       Sdtrig_H_cg.set_inst_name("obj_Sdtrig_H");
    `ifndef EXCLUDE_SM
        Sdtrig_HSm_cg = new(); Sdtrig_HSm_cg.set_inst_name("obj_Sdtrig_HSm");
    `endif
`endif
