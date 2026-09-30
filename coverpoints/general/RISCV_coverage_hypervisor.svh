///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Hypervisor Configuration Macros
//
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`ifndef RISCV_COVERAGE_HYPERVISOR_SVH
`define RISCV_COVERAGE_HYPERVISOR_SVH

// H_TWO_STAGE: Sv39x4 and VS-stage Sv39 (RV64) or Sv32x4 and VS-stage Sv32 (RV32), as TWO_STAGE_GATE in HCommon.py
// H_REPLICA_SATP: satp and vsatp both support Sv39 (RV64) or Sv32 (RV32), as REPLICA_ATP_GATE in HCommon.py
`ifdef UDB_MXLEN_64
    `ifdef UDB_SV39_VSMODE_TRANSLATION
        `ifdef UDB_SV39X4_TRANSLATION
            `define H_TWO_STAGE
        `endif
        `ifdef SV39_SUPPORTED
            `define H_REPLICA_SATP
        `endif
    `endif
`else
    `ifdef UDB_SV32_VSMODE_TRANSLATION
        `ifdef UDB_SV32X4_TRANSLATION
            `define H_TWO_STAGE
        `endif
        `ifdef SV32_SUPPORTED
            `define H_REPLICA_SATP
        `endif
    `endif
`endif

// H_VADDR_WALK_MSB: vsepc and vstval hold the same values as sepc and stval, so they must hold every canonical
// virtual address.  Canonical addresses have bits XLEN-1:VALEN-1 equal, so bit VALEN-2 is the msb walked on its own
// (31 for Sv32, where VALEN = XLEN), as VADDR_TIERS in PrivCommon.py.
`ifdef SV57_SUPPORTED
    `define H_VADDR_WALK_MSB 55
`elsif SV48_SUPPORTED
    `define H_VADDR_WALK_MSB 46
`elsif SV39_SUPPORTED
    `define H_VADDR_WALK_MSB 37
`elsif SV32_SUPPORTED
    `define H_VADDR_WALK_MSB 31
`endif

`endif // RISCV_COVERAGE_HYPERVISOR_SVH
