///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Per Instruction Sampling
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    ins_t ins;
    ins = new(hart, issue, traceDataQ);

    case (traceDataQ[hart][issue][0].inst_name)
