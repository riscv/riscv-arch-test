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

    SPMPSm_csr_cg = new();           SPMPSm_csr_cg.set_inst_name("obj_SPMPSm_csr");
    SPMPSm_perm_cg = new();          SPMPSm_perm_cg.set_inst_name("obj_SPMPSm_perm");
    SPMPSm_addr_cg = new();          SPMPSm_addr_cg.set_inst_name("obj_SPMPSm_addr");
    SPMPSm_paging_cg = new();        SPMPSm_paging_cg.set_inst_name("obj_SPMPSm_paging");
