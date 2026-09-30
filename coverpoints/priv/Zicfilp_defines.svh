///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2026 RISC-V International
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp macros shared by the Zicfilp covergroups
///////////////////////////////////////////////

// An indirect call/jump sets ELP=LP_EXPECTED (when xLPE=1) unless rs1 is x1, x5, or x7.
// rs1=x0 is excluded from the compressed form because that encoding is c.ebreak.
`ifndef ZICFILP_LP_JALR
    `define ZICFILP_LP_JALR(INSN)  (((INSN) ==? JALR) && !((INSN[19:15]) inside {5'd1, 5'd5, 5'd7}))
    `define ZICFILP_LP_CJUMP(INSN) ((((INSN) ==? C_JR) || ((INSN) ==? C_JALR)) && !((INSN[11:7]) inside {5'd0, 5'd1, 5'd5, 5'd7}))
    `ifdef ZCA_SUPPORTED
        `define ZICFILP_LP_BRANCH(INSN) (`ZICFILP_LP_JALR(INSN) || `ZICFILP_LP_CJUMP(INSN))
    `else
        `define ZICFILP_LP_BRANCH(INSN) `ZICFILP_LP_JALR(INSN)
    `endif
`endif
