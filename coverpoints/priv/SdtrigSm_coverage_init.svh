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
    SdtrigSm_mcontrol6_cg = new();             SdtrigSm_mcontrol6_cg.set_inst_name("obj_SdtrigSm_mcontrol6");
    `ifdef UDB_TCONTROL_AVAILABLE
        SdtrigSm_tcontrol_cg = new();               SdtrigSm_tcontrol_cg.set_inst_name("obj_SdtrigSm_tcontrol");
    `endif
