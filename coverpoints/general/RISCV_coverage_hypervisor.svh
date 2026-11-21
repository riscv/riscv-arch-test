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
`ifdef UDB_SV39_VSMODE_TRANSLATION
    `ifdef UDB_SV39X4_TRANSLATION
        `define H_TWO_STAGE
    `endif
`endif
`ifdef UDB_SV32_VSMODE_TRANSLATION
    `ifdef UDB_SV32X4_TRANSLATION
        `define H_TWO_STAGE
    `endif
`endif

`ifdef H_SUPPORTED
// {hgatp.MODE, 2'b00, x4 bits}: the two guest physical address bits that an x4 G-stage mode adds above its Sv mode's
// virtual address width (33:32 for Sv32x4, 40:39 for Sv39x4, 49:48 for Sv48x4, 58:57 for Sv57x4), from a guest physical
// address shifted right by shift.  0 when hgatp is Bare, the bits are 00, or a bit above them is set.
function automatic logic [7:0] x4_gpa_bits(ins_t ins, `XLEN_BITS gpa, int shift);
    logic [3:0] mode = get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode");
    `XLEN_BITS bits;
    case (mode)
        1:       bits = gpa >> (32 - shift);
        8:       bits = gpa >> (39 - shift);
        9:       bits = gpa >> (48 - shift);
        10:      bits = gpa >> (57 - shift);
        default: bits = 0;
    endcase
    return (bits inside {[1:3]}) ? {mode, 2'b00, bits[1:0]} : 8'h0;
endfunction
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

`ifdef S_SUPPORTED
// 1 when this record takes an exception into M-mode that would go to S-mode (HS-mode with H), but medeleg cannot
// delegate it: its MEDELEG_DELEGATABLE bit is false, so that bit of medeleg is read-only 0
function automatic logic medeleg_blocked_trap(ins_t ins);
    logic [31:0] delegatable = `UDB_MEDELEG_DELEGATABLE_MASK;
    `XLEN_BITS mcause = get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCAUSE);
    return ins.current.csr_wb[CSR_MCAUSE] && mcause < 32 && !delegatable[mcause[4:0]];
endfunction
// {trap, cause[4:0]} of the trap into S-mode (HS-mode with H) that this record takes, if any; a medeleg_blocked_trap
// counts as one
function automatic logic [5:0] s_trap(ins_t ins);
    if (medeleg_blocked_trap(ins)) return {1'b1, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCAUSE)[4:0]};
    return {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE)[4:0]};
endfunction
`endif

`endif // RISCV_COVERAGE_HYPERVISOR_SVH
