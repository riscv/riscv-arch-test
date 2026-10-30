///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Sv_satp_cg = new(); Sv_satp_cg.set_inst_name("obj_Sv_satp");
    Sv_VA_cg = new(); Sv_VA_cg.set_inst_name("obj_Sv_VA");
    Sv_sfence_cg = new(); Sv_sfence_cg.set_inst_name("obj_Sv_sfence");
    Sv_vm_permissions_cg = new(); Sv_vm_permissions_cg.set_inst_name("obj_Sv_vm_permissions");
    Sv_res_global_pte_cg = new(); Sv_res_global_pte_cg.set_inst_name("obj_Sv_res_global_pte");
    Sv_add_feature_cg = new(); Sv_add_feature_cg.set_inst_name("obj_Sv_add_feature");
`ifndef EXCLUDE_SM
    Sv_Sm_satp_cg = new(); Sv_Sm_satp_cg.set_inst_name("obj_Sv_Sm_satp");
    Sv_Sm_mstatus_mprv_cg = new(); Sv_Sm_mstatus_mprv_cg.set_inst_name("obj_Sv_Sm_mstatus_mprv");
`endif // EXCLUDE_SM
`ifdef SV_ZICBO_ANY
    Sv_Zicbo_cg = new(); Sv_Zicbo_cg.set_inst_name("obj_Sv_Zicbo");
`endif // SV_ZICBO_ANY
    Sv_Exceptions_cg = new(); Sv_Exceptions_cg.set_inst_name("obj_Sv_Exceptions");
`ifndef EXCLUDE_SM
    Sv_ExceptionsSm_cg = new(); Sv_ExceptionsSm_cg.set_inst_name("obj_Sv_ExceptionsSm");
`endif // EXCLUDE_SM
`ifdef ZAAMO_SUPPORTED
    Sv_ExceptionsZaamo_cg = new(); Sv_ExceptionsZaamo_cg.set_inst_name("obj_Sv_ExceptionsZaamo");
    `ifndef EXCLUDE_SM
        Sv_ExceptionsZaamoSm_cg = new(); Sv_ExceptionsZaamoSm_cg.set_inst_name("obj_Sv_ExceptionsZaamoSm");
    `endif // EXCLUDE_SM
`endif // ZAAMO_SUPPORTED
`ifdef ZALRSC_SUPPORTED
    Sv_ExceptionsZalrsc_cg = new(); Sv_ExceptionsZalrsc_cg.set_inst_name("obj_Sv_ExceptionsZalrsc");
    `ifndef EXCLUDE_SM
        Sv_ExceptionsZalrscSm_cg = new(); Sv_ExceptionsZalrscSm_cg.set_inst_name("obj_Sv_ExceptionsZalrscSm");
    `endif // EXCLUDE_SM
`endif // ZALRSC_SUPPORTED
