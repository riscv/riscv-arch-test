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
// TD is a trace record (ins.prev or ins.current). ZICFILP_RS1 is its decoded rs1 for jalr, c.jr and c.jalr,
// and x0 for any other instruction. c.ebreak shares the c.jalr encoding with rs1=x0 and has no rs1 operand.
`ifndef ZICFILP_LP_JALR
    `define ZICFILP_INDIRECT(TD)   ((TD.insn ==? JALR) || (TD.insn ==? C_JR) || (TD.insn ==? C_JALR))
    `define ZICFILP_RS1(TD)        ((`ZICFILP_INDIRECT(TD) && TD.has_rs1) ? ins.get_gpr_reg(TD.rs1) : x0)
    `define ZICFILP_RS1_LINK(TD)   ((`ZICFILP_RS1(TD) == x1) || (`ZICFILP_RS1(TD) == x5) || (`ZICFILP_RS1(TD) == x7))
    `define ZICFILP_LP_JALR(TD)    ((TD.insn ==? JALR) && !`ZICFILP_RS1_LINK(TD))
    `define ZICFILP_LP_CJUMP(TD)   (((TD.insn ==? C_JR) || (TD.insn ==? C_JALR)) && (`ZICFILP_RS1(TD) != x0) && !`ZICFILP_RS1_LINK(TD))
    `ifdef ZCA_SUPPORTED
        `define ZICFILP_LP_BRANCH(TD) (`ZICFILP_LP_JALR(TD) || `ZICFILP_LP_CJUMP(TD))
    `else
        `define ZICFILP_LP_BRANCH(TD) `ZICFILP_LP_JALR(TD)
    `endif
`endif
