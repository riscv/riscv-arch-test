///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

Ssnpm_cg = new();
Ssnpm_cg.set_inst_name("obj_Ssnpm");
`ifndef EXCLUDE_SM
Ssnpm_Sm_cg = new();
Ssnpm_Sm_cg.set_inst_name("obj_Ssnpm_Sm");
`endif
`ifdef H_SUPPORTED
Ssnpm_H_cg = new();
Ssnpm_H_cg.set_inst_name("obj_Ssnpm_H");
`endif
