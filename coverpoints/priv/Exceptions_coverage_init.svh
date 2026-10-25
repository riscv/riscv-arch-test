///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifdef F_SUPPORTED
    Exceptions_F_cg = new();   Exceptions_F_cg.set_inst_name("obj_Exceptions_F");
`endif // F_SUPPORTED
`ifdef S_SUPPORTED
    Exceptions_S_cg = new();   Exceptions_S_cg.set_inst_name("obj_Exceptions_S");
`endif // S_SUPPORTED
`ifndef EXCLUDE_SM
    Exceptions_Sm_cg = new();   Exceptions_Sm_cg.set_inst_name("obj_Exceptions_Sm");
`endif // EXCLUDE_SM
`ifdef U_SUPPORTED
    Exceptions_U_cg = new();   Exceptions_U_cg.set_inst_name("obj_Exceptions_U");
`endif // U_SUPPORTED
`ifdef ZAAMO_SUPPORTED
    Exceptions_Zaamo_cg = new();   Exceptions_Zaamo_cg.set_inst_name("obj_Exceptions_Zaamo");
`endif // ZAAMO_SUPPORTED
`ifdef ZALRSC_SUPPORTED
    Exceptions_Zalrsc_cg = new();   Exceptions_Zalrsc_cg.set_inst_name("obj_Exceptions_Zalrsc");
`endif // ZALRSC_SUPPORTED
`ifdef ZCA_SUPPORTED
    Exceptions_Zc_cg = new();   Exceptions_Zc_cg.set_inst_name("obj_Exceptions_Zc");
`endif // ZCA_SUPPORTED
`ifdef EXCEPTIONS_ZICBO_ANY
  `ifdef S_SUPPORTED
      Exceptions_ZicboS_cg = new();   Exceptions_ZicboS_cg.set_inst_name("obj_Exceptions_ZicboS");
  `endif // S_SUPPORTED
  `ifndef EXCLUDE_SM
      Exceptions_ZicboSm_cg = new();   Exceptions_ZicboSm_cg.set_inst_name("obj_Exceptions_ZicboSm");
  `endif // EXCLUDE_SM
  `ifdef U_SUPPORTED
      Exceptions_ZicboU_cg = new();   Exceptions_ZicboU_cg.set_inst_name("obj_Exceptions_ZicboU");
  `endif // U_SUPPORTED
`endif // EXCEPTIONS_ZICBO_ANY
