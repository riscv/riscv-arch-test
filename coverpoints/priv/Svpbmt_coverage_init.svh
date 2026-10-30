///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Svpbmt_cg = new(); Svpbmt_cg.set_inst_name("obj_Svpbmt");
`ifdef ZICBOM_SUPPORTED
    Svpbmt_Zicbom_cg = new(); Svpbmt_Zicbom_cg.set_inst_name("obj_Svpbmt_Zicbom");
`endif // ZICBOM_SUPPORTED
`ifdef ZICBOZ_SUPPORTED
    Svpbmt_Zicboz_cg = new(); Svpbmt_Zicboz_cg.set_inst_name("obj_Svpbmt_Zicboz");
`endif // ZICBOZ_SUPPORTED
