///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// Smnpm applies to S mode when S is implemented
`ifdef S_SUPPORTED
  Smnpm_S_cg = new();
  Smnpm_S_cg.set_inst_name("obj_Smnpm_S");
  `ifndef EXCLUDE_SM
    Smnpm_SSm_cg = new();
    Smnpm_SSm_cg.set_inst_name("obj_Smnpm_SSm");
  `endif // EXCLUDE_SM
`else // S not supported, Smnpm applies to U mode
  Smnpm_U_cg = new();
  Smnpm_U_cg.set_inst_name("obj_Smnpm_U");
  `ifndef EXCLUDE_SM
    Smnpm_USm_cg = new();
    Smnpm_USm_cg.set_inst_name("obj_Smnpm_USm");
  `endif // EXCLUDE_SM
`endif
