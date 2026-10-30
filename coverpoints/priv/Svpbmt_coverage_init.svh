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
`ifdef H_SUPPORTED
`ifdef UDB_MXLEN_64
    Svpbmt_H_cg = new(); Svpbmt_H_cg.set_inst_name("obj_Svpbmt_H");
`endif
`endif
