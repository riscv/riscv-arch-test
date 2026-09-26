///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    `ifdef RVMODEL_SET_GUEST_EXT_INT
        InterruptsHGei_m_cg = new();  InterruptsHGei_m_cg.set_inst_name("obj_InterruptsHGei_m");
        InterruptsHGei_hs_cg = new(); InterruptsHGei_hs_cg.set_inst_name("obj_InterruptsHGei_hs");
    `endif
