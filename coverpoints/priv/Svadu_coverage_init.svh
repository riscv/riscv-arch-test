///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Svadu_cg = new(); Svadu_cg.set_inst_name("obj_Svadu");
`ifdef H_SUPPORTED
    Svadu_H_cg = new(); Svadu_H_cg.set_inst_name("obj_Svadu_H");
`endif
