///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    Sstc_cg = new();         Sstc_cg.set_inst_name("obj_Sstc");
`ifndef EXCLUDE_SM
    Sstc_Sm_cg = new();      Sstc_Sm_cg.set_inst_name("obj_Sstc_Sm");
`endif
`ifdef H_SUPPORTED
    Sstc_H_cg = new();       Sstc_H_cg.set_inst_name("obj_Sstc_H");
    `ifndef EXCLUDE_SM
        Sstc_HSm_cg = new(); Sstc_HSm_cg.set_inst_name("obj_Sstc_HSm");
    `endif
`endif
