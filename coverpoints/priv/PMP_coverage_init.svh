///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    PMP_Sm_cg = new();    PMP_Sm_cg.set_inst_name("obj_PMP_Sm");
`ifdef F_SUPPORTED
    PMP_F_cg = new();    PMP_F_cg.set_inst_name("obj_PMP_F");
`endif
`ifdef S_SUPPORTED
    PMP_S_cg = new();    PMP_S_cg.set_inst_name("obj_PMP_S");
`endif
`ifdef U_SUPPORTED
    PMP_U_cg = new();    PMP_U_cg.set_inst_name("obj_PMP_U");
`endif
`ifdef ZAAMO_SUPPORTED
    PMP_Zaamo_cg = new();    PMP_Zaamo_cg.set_inst_name("obj_PMP_Zaamo");
`endif
`ifdef ZALRSC_SUPPORTED
    PMP_Zalrsc_cg = new();    PMP_Zalrsc_cg.set_inst_name("obj_PMP_Zalrsc");
`endif
`ifdef ZCA_SUPPORTED
    PMP_Zca_cg = new();    PMP_Zca_cg.set_inst_name("obj_PMP_Zca");
`endif
`ifdef PMP_HAS_ZICBO
    PMP_Zicbo_cg = new();    PMP_Zicbo_cg.set_inst_name("obj_PMP_Zicbo");
`endif
`ifdef PMP_HAS_SV
    PMP_Sv_cg = new();    PMP_Sv_cg.set_inst_name("obj_PMP_Sv");
`endif
`ifdef PMP_COVER_SVZICBO
    PMP_SvZicbo_cg = new();    PMP_SvZicbo_cg.set_inst_name("obj_PMP_SvZicbo");
`endif
`ifdef SVADU_SUPPORTED
    PMP_Svadu_cg = new();    PMP_Svadu_cg.set_inst_name("obj_PMP_Svadu");
`endif
