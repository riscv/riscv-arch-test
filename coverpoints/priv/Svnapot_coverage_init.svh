///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Svnapot_cg = new(); Svnapot_cg.set_inst_name("obj_Svnapot");
`ifdef H_SUPPORTED
`ifdef UDB_MXLEN_64
    Svnapot_H_cg = new(); Svnapot_H_cg.set_inst_name("obj_Svnapot_H");
`endif
`endif
