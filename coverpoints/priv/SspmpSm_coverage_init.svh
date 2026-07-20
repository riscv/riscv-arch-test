///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
// SPMP (S-level Physical Memory Protection) Test Suite
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    SspmpSm_csr_cg = new();           SspmpSm_csr_cg.set_inst_name("obj_SspmpSm_csr");
    SspmpSm_perm_cg = new();          SspmpSm_perm_cg.set_inst_name("obj_SspmpSm_perm");
    SspmpSm_addr_cg = new();          SspmpSm_addr_cg.set_inst_name("obj_SspmpSm_addr");
    SspmpSm_paging_cg = new();        SspmpSm_paging_cg.set_inst_name("obj_SspmpSm_paging");
    SspmpSm_spmpen_cg = new();        SspmpSm_spmpen_cg.set_inst_name("obj_SspmpSm_spmpen");
