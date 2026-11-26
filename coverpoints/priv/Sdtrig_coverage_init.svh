///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifdef H_SUPPORTED
    Sdtrig_H_cg = new();       Sdtrig_H_cg.set_inst_name("obj_Sdtrig_H");
    `ifndef EXCLUDE_SM
        Sdtrig_HSm_cg = new(); Sdtrig_HSm_cg.set_inst_name("obj_Sdtrig_HSm");
    `endif
`endif
