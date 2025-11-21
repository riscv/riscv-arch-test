///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Collection Driver
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written: Jordan Carlin jcarlin@hmc.edu February 2024
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// Load which extensions are supported in this configuration (from $WALLY/config/<config>/coverage.svh)
`include "rvtest_config.svh"

// Load disassembler
`include "disassemble.svh"

// Load the coverage classes
`include "RISCV_coverage.svh"

module riscv_arch_test(rvviTrace rvvi);
  string disass;

  // Connect coverage class to RVVI trace interface
  coverage #(rvvi.ILEN, rvvi.XLEN, rvvi.FLEN, rvvi.VLEN, rvvi.NHART, rvvi.RETIRE) riscvISACOV;

  initial begin
    riscvISACOV = new(rvvi);
    $display("riscv_arch_test: coverage initialized");
  end

  // Invoke the riscvISACOV sample function on each clock edge for the current instruction.
  // If RVVI accepts more than one instruction or hart, iterate over all of them in the
  // correct order of retirement (TODO: multiple instructions/harts not implemented)
  always_ff @(posedge rvvi.clk) begin
    if (rvvi.valid[0][0] == 1) begin
      disass = disassemble(rvvi.insn[0][0]);
      riscvISACOV.sample(rvvi.trap[0][0], 0, 0, disass);
      `ifdef FCOV_VERBOSE
        $display("riscv_arch_test: sample taken for PC 0x%h instruction %s", rvvi.pc_rdata[0][0], disass);
      `endif
    end
  end
endmodule
