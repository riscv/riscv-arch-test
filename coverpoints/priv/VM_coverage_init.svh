///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    VM_satp_cg = new(); VM_satp_cg.set_inst_name("obj_VM_satp");
    VM_PA_VA_cg = new(); VM_PA_VA_cg.set_inst_name("obj_VM_PA_VA");
    VM_sfence_cg = new(); VM_sfence_cg.set_inst_name("obj_VM_sfence");
    VM_mstatus_mprv_cg = new(); VM_mstatus_mprv_cg.set_inst_name("obj_VM_mstatus_mprv");
    VM_vm_permissions_cg = new(); VM_vm_permissions_cg.set_inst_name("obj_VM_vm_permissions");
    VM_res_global_pte_cg = new(); VM_res_global_pte_cg.set_inst_name("obj_VM_res_global_pte");
    VM_add_feature_cg = new(); VM_add_feature_cg.set_inst_name("obj_VM_add_feature");
